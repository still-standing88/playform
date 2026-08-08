from __future__ import annotations

import re
from typing import Callable, Optional

from media_core.ffmpeg import FFmpeg
from media_core.ffmpeg.errors import FFmpegError

from media_core.m4b_tools import probe as probe_module
from media_core.m4b_tools.segment import Segment

_MAX_TIME = 100000000000000.0

_SILENCE_START_RE = re.compile(r" silence_start: (?P<start>-?[0-9]+(?:\.[0-9]*)?)")
_SILENCE_END_RE = re.compile(r" silence_end: (?P<end>-?[0-9]+(?:\.[0-9]*)?)")


def find_chapters(
    input_path,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    ffprobe_executable: str = "ffprobe",
) -> list[Segment]:
    """Read a file's embedded chapters, filtered to the given time window."""
    resolved_start = start_time if start_time is not None else 0.0
    resolved_end = end_time if end_time is not None else _MAX_TIME

    chapters = probe_module.get_chapters(input_path, ffprobe_executable)
    return [c for c in chapters if c.start_time >= resolved_start and c.end_time <= resolved_end]


class _SilenceLineParser:
    """Turns ffmpeg `silencedetect` stderr lines into non-silence (start, end) spans."""

    def __init__(self, start_time: float, end_time: float, trim_silence: bool = False):
        self.start_time = start_time
        self.end_time = end_time
        self.trim_silence = trim_silence
        self.segment_starts: list[float] = []
        self.segment_ends: list[float] = []

    def parse_line(self, line: str):
        if self.trim_silence:
            match = _SILENCE_START_RE.search(line)
            if match:
                timestamp = self.start_time + float(match.group("start"))
                if self.start_time < timestamp < self.end_time:
                    self.segment_ends.append(timestamp)
                    if not self.segment_starts:
                        self.segment_starts.append(self.start_time)

        match = _SILENCE_END_RE.search(line)
        if match:
            timestamp = self.start_time + float(match.group("end"))
            if timestamp < self.end_time:
                if not self.trim_silence:
                    if not self.segment_starts:
                        self.segment_starts.append(self.start_time)
                    if len(self.segment_starts) > len(self.segment_ends):
                        self.segment_ends.append(timestamp)
                self.segment_starts.append(timestamp)

    def get_segments(self) -> list[tuple]:
        if len(self.segment_starts) > len(self.segment_ends):
            if self.segment_starts[-1] < self.end_time:
                self.segment_ends.append(self.end_time)
            else:
                self.segment_starts.pop()
        return list(zip(self.segment_starts, self.segment_ends))


def find_silence(
    input_path,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    silence_duration: float = 3.0,
    silence_threshold: int = -35,
    trim_silence: bool = False,
    ffmpeg_executable: str = "ffmpeg",
    ffprobe_executable: str = "ffprobe",
    on_log_line: Optional[Callable[[str], None]] = None,
) -> list[Segment]:
    """Find non-silence spans in a file via ffmpeg's `silencedetect` filter.

    When `end_time` isn't given, the file's duration is resolved once up front via
    `probe.get_file_duration` rather than sniffing it back out of ffmpeg's own stderr,
    so there's a single source of truth for "how long is this file" across m4b_tools.
    """
    on_log_line = on_log_line or (lambda line: None)

    resolved_start = start_time or 0.0
    resolved_end = end_time
    if resolved_end is None:
        try:
            resolved_end = probe_module.get_file_duration(input_path, ffprobe_executable)
        except RuntimeError:
            resolved_end = _MAX_TIME

    input_options = {}
    if start_time:
        input_options["ss"] = start_time
    if end_time:
        input_options["t"] = end_time - resolved_start

    ffmpeg = FFmpeg(executable=ffmpeg_executable)
    ffmpeg.input(str(input_path), input_options)
    ffmpeg.option("filter_complex", f"[0]silencedetect=d={silence_duration}:n={silence_threshold}dB[s0]")
    ffmpeg.output("-", **{"map": "[s0]", "f": "null"})

    lines: list[str] = []

    @ffmpeg.on("stderr")
    def _on_stderr(line: str):
        lines.append(line)
        on_log_line(line)

    try:
        ffmpeg.execute()
    except FFmpegError:
        pass

    parser = _SilenceLineParser(resolved_start, resolved_end, trim_silence)
    for line in lines:
        parser.parse_line(line)

    segments = []
    for index, (segment_start, segment_end) in enumerate(parser.get_segments()):
        segments.append(Segment(
            start_time=segment_start,
            end_time=segment_end,
            id=index,
            backing_file=str(input_path),
            file_start_time=segment_start,
            file_end_time=segment_end,
        ))
    return segments

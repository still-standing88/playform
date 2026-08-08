from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from media_core.ffmpeg import FFmpeg
from media_core.ffmpeg.errors import FFmpegError

from media_core.m4b_tools.segment import Segment


@dataclass
class MediaProbe:
    """Result of a single combined `ffprobe -show_format -show_streams -show_chapters` call."""

    format: dict
    streams: list
    chapters: list
    tags: dict
    audio_stream: Optional[dict]

    @property
    def duration(self) -> Optional[float]:
        raw = self.format.get("duration") or (self.audio_stream or {}).get("duration")
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None


def _run_ffprobe(ffprobe_executable: str, path, *show_flags: str) -> dict:
    ffprobe = FFmpeg(executable=ffprobe_executable)
    ffprobe.option("v", "quiet")
    ffprobe.option("print_format", "json")
    for flag in show_flags:
        ffprobe.option(flag)
    ffprobe.input(str(path))

    try:
        output = ffprobe.execute()
    except (FFmpegError, OSError):
        return {}

    if not output:
        return {}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {}


def run_probe(path, ffprobe_executable: str = "ffprobe") -> Optional[MediaProbe]:
    """Probe a media file's format, streams, tags, and chapters in one ffprobe call."""
    data = _run_ffprobe(ffprobe_executable, path, "show_format", "show_streams", "show_chapters")
    if not data:
        return None

    streams = data.get("streams", [])
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = data.get("format", {})
    return MediaProbe(
        format=fmt,
        streams=streams,
        chapters=data.get("chapters", []),
        tags=fmt.get("tags", {}),
        audio_stream=audio_stream,
    )


_DECODE_TIME_RE = re.compile(r"time=(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\.(?P<ms>\d{2})")


def get_file_duration(
    path,
    ffprobe_executable: str = "ffprobe",
    ffmpeg_executable: str = "ffmpeg",
    decode_duration: bool = False,
) -> float:
    """Determine a file's duration, in seconds.

    Trusts the container's metadata by default (fast). Pass `decode_duration=True` to
    fully decode the file and read the final timestamp instead - slower, but immune to
    files with wrong or missing duration metadata.
    """
    if decode_duration:
        duration = _decode_duration(path, ffmpeg_executable)
        if duration is not None:
            return duration

    probe = run_probe(path, ffprobe_executable)
    if not probe or probe.audio_stream is None:
        raise RuntimeError(f"Could not get audio stream for '{path}'.")

    duration = probe.duration
    if duration is None:
        raise RuntimeError(f"Cannot parse duration listed in '{path}'.")
    return duration


def _decode_duration(path, ffmpeg_executable: str) -> Optional[float]:
    ffmpeg = FFmpeg(executable=ffmpeg_executable).option("y")
    ffmpeg.input(str(path)).output("-", f="null")

    last_match = None

    @ffmpeg.on("stderr")
    def _on_stderr(line: str):
        nonlocal last_match
        match = _DECODE_TIME_RE.search(line)
        if match:
            last_match = match

    try:
        ffmpeg.execute()
    except FFmpegError:
        pass

    if last_match is None:
        return None

    groups = last_match.groupdict()
    return (
        int(groups["hour"]) * 3600
        + int(groups["min"]) * 60
        + int(groups["sec"])
        + int(groups["ms"]) / 100
    )


def get_chapters(path, ffprobe_executable: str = "ffprobe") -> list[Segment]:
    """Read a file's embedded chapters as a list of `Segment`s."""
    probe = run_probe(path, ffprobe_executable)
    if probe is None:
        return []

    segments = []
    for chapter in probe.chapters:
        start = float(chapter["start_time"])
        end = float(chapter["end_time"])
        segments.append(Segment(
            start_time=start,
            end_time=end,
            id=chapter.get("id"),
            title=chapter.get("tags", {}).get("title"),
            backing_file=str(path),
            file_start_time=start,
            file_end_time=end,
        ))
    return segments


def probe_sample_rate(ffprobe_executable: str, path, default: int = 44100) -> int:
    probe = run_probe(path, ffprobe_executable)
    if probe and probe.audio_stream and probe.audio_stream.get("sample_rate"):
        try:
            return int(probe.audio_stream["sample_rate"])
        except (TypeError, ValueError):
            pass
    return default

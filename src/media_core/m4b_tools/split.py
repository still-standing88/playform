from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from media_core.ffmpeg import FFmpeg
from media_core.ffmpeg.errors import FFmpegError
from media_core.ffmpeg.format_capabilities import build_ffmpeg_output_options, get_format

from media_core.m4b_tools import cover as cover_module
from media_core.m4b_tools import probe as probe_module
from media_core.m4b_tools.finders import find_chapters, find_silence
from media_core.m4b_tools.naming import DEFAULT_CHAPTER_TEMPLATE, format_chapter_filename, format_time, sanitize_filename
from media_core.m4b_tools.runner import M4bToolsRunner


def build_chapter_variables(segment, index: int, probe: Optional[probe_module.MediaProbe],
                             source_path, output_format_id: str) -> dict:
    """Naming-template variables for one split-out chapter file.

    Same variable set `m4b-tools`' splitter offered (`{book_title}`, `{chapter_num}`, ...),
    kept as the one place that builds them so both the chapters- and silence-based split
    modes format output paths identically.
    """
    tags = (probe.tags if probe else {}) or {}
    author = tags.get("author") or tags.get("artist") or tags.get("album_artist") or ""
    narrator = tags.get("narrator") or tags.get("composer") or ""
    book_title = tags.get("title") or tags.get("album") or Path(source_path).stem
    genre = tags.get("genre", "")
    year = (tags.get("date") or "")[:4]
    duration = segment.end_time - segment.start_time

    return {
        "chapter_num": index,
        "chapter_title": sanitize_filename(segment.title or str(index)),
        "book_title": sanitize_filename(book_title),
        "author": sanitize_filename(author) if author else "",
        "narrator": sanitize_filename(narrator) if narrator else "",
        "genre": sanitize_filename(genre) if genre else "",
        "year": year,
        "ext": get_format(output_format_id).extension,
        "original_filename": Path(source_path).stem,
        "duration": f"{duration:.0f}s",
        "duration_formatted": format_time(duration),
    }


class SplitRunner(M4bToolsRunner):
    """Splits one file into per-segment files, either by embedded chapters or detected silence.

    Mirrors `media_core.ffmpeg.conversion_job.ConversionRunner`'s callback shape
    (`on_overall_progress(index, total, name)`, `on_file_completed(name, success, message)`,
    `on_log_line(line)`) and its threading model, so a Qt wrapper can drive this exactly
    like it drives a batch-conversion job.
    """

    def __init__(
        self,
        input_path,
        output_dir,
        mode: str = "chapters",
        output_format: str = "mp3",
        template: str = DEFAULT_CHAPTER_TEMPLATE,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        minimum_segment_time: float = 1.0,
        silence_duration: float = 3.0,
        silence_threshold: int = -35,
        trim_silence: bool = False,
        padding: float = 0.0,
        include_cover: bool = True,
        codec_option_values: Optional[dict] = None,
        ffmpeg_executable: str = "ffmpeg",
        ffprobe_executable: str = "ffprobe",
        on_overall_progress: Optional[Callable[[int, int, str], None]] = None,
        on_file_completed: Optional[Callable[[str, bool, str], None]] = None,
        on_log_line: Optional[Callable[[str], None]] = None,
    ):
        super().__init__()
        self.input_path = Path(input_path)
        self.output_dir = Path(output_dir)
        self.mode = mode
        self.output_format = output_format
        self.template = template
        self.start_time = start_time
        self.end_time = end_time
        self.minimum_segment_time = minimum_segment_time
        self.silence_duration = silence_duration
        self.silence_threshold = silence_threshold
        self.trim_silence = trim_silence
        self.padding = padding
        self.include_cover = include_cover
        self.codec_option_values = codec_option_values or {}
        self.ffmpeg_executable = ffmpeg_executable
        self.ffprobe_executable = ffprobe_executable

        self._on_overall_progress = on_overall_progress or (lambda *a: None)
        self._on_file_completed = on_file_completed or (lambda *a: None)
        self._on_log_line = on_log_line or (lambda line: None)

    def run(self) -> tuple:
        """Split `self.input_path`. Returns (successful_segment_count, total_segment_count)."""
        if self.mode == "silence":
            segments = find_silence(
                self.input_path, self.start_time, self.end_time,
                self.silence_duration, self.silence_threshold, self.trim_silence,
                self.ffmpeg_executable, self.ffprobe_executable, self._on_log_line,
            )
        else:
            segments = find_chapters(self.input_path, self.start_time, self.end_time, self.ffprobe_executable)

        segments = [s for s in segments if s.end_time - s.start_time >= self.minimum_segment_time]
        if not segments:
            self._on_log_line("Error: No segments found.")
            return 0, 0

        probe = probe_module.run_probe(self.input_path, self.ffprobe_executable)

        cover_path = None
        if self.include_cover:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            candidate = self.output_dir / "cover.png"
            if cover_module.extract_cover(self.input_path, candidate, self.ffmpeg_executable):
                cover_path = candidate

        total = len(segments)
        successful = 0

        for index, segment in enumerate(segments, start=1):
            if not self._checkpoint():
                break

            self._on_overall_progress(index - 1, total, segment.title or str(index))
            variables = build_chapter_variables(segment, index, probe, self.input_path, self.output_format)
            output_path = self.output_dir / format_chapter_filename(self.template, variables)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                self._split_one(segment, index, total, output_path, probe, cover_path)
                self._on_file_completed(str(output_path), True, "OK")
                successful += 1
            except FFmpegError as error:
                self._on_file_completed(str(output_path), False, error.message)
            except OSError as error:
                self._on_file_completed(str(output_path), False, str(error))

        self._on_overall_progress(total, total, "")
        return successful, total

    def _split_one(self, segment, index: int, total: int, output_path: Path, probe, cover_path: Optional[Path]):
        duration = segment.end_time - segment.start_time
        tags = (probe.tags if probe else {}) or {}

        ffmpeg = FFmpeg(executable=self.ffmpeg_executable).option("y")
        ffmpeg.input(str(self.input_path), {"ss": segment.start_time, "t": duration})

        output_options = build_ffmpeg_output_options(
            self.output_format, codec_option_values=self.codec_option_values,
        )
        output_options["vn"] = None
        output_options["map_chapters"] = "-1"
        output_options["metadata"] = self._build_metadata_flags(segment, index, total, tags)

        if self.padding > 0.0:
            output_options["af"] = f"apad=pad_dur={self.padding}"

        if cover_path:
            ffmpeg.input(str(cover_path))
            output_options["map"] = ["0:a", "1:0"]
        else:
            output_options["map"] = "0:a"

        ffmpeg.output(str(output_path), **output_options)

        @ffmpeg.on("stderr")
        def _on_stderr(line: str):
            self._on_log_line(line)

        ffmpeg.execute()

    @staticmethod
    def _build_metadata_flags(segment, index: int, total: int, tags: dict) -> list:
        flags = []
        book_title = tags.get("title") or tags.get("album")
        if book_title:
            flags.append(f"album={book_title}")
        author = tags.get("author") or tags.get("artist") or tags.get("album_artist")
        if author:
            flags.append(f"artist={author}")
            flags.append(f"album_artist={author}")
        narrator = tags.get("narrator") or tags.get("composer")
        if narrator:
            flags.append(f"composer={narrator}")
        if tags.get("genre"):
            flags.append(f"genre={tags['genre']}")
        if tags.get("date"):
            flags.append(f"date={tags['date']}")
        if segment.title:
            flags.append(f"title={segment.title}")
        flags.append(f"track={index}/{total}")
        return flags


def split_multiple_files(input_paths, output_dir, **runner_kwargs) -> tuple:
    """Run `SplitRunner` over several source files. Returns (files_fully_split, total_files)."""
    on_log_line = runner_kwargs.get("on_log_line") or (lambda line: None)
    input_paths = list(input_paths)
    fully_split = 0
    for input_path in input_paths:
        runner = SplitRunner(input_path, output_dir, **runner_kwargs)
        successful, total = runner.run()
        if total > 0 and successful == total:
            fully_split += 1
        elif total == 0:
            on_log_line(f"No segments found in {input_path}")
    return fully_split, len(input_paths)

from __future__ import annotations

from typing import Callable, Optional

from media_core.m4b_tools.audiobook import Audiobook


def _shift(segments, duration: float):
    for segment in segments:
        segment.start_time += duration
        segment.end_time += duration
        if segment.file_start_time is not None:
            segment.file_start_time += duration
        if segment.file_end_time is not None:
            segment.file_end_time += duration


def _drop_overshooting(segments, start_time, end_time, file_start_time, file_end_time):
    """Remove segments that ended up entirely outside the original [start_time, end_time] window."""
    for segment in segments.copy():
        if segment.start_time > end_time or segment.end_time <= 0 or segment.end_time < start_time:
            segments.remove(segment)
            continue
        if None not in (segment.file_start_time, segment.file_end_time, file_start_time, file_end_time):
            if (
                segment.file_start_time > file_end_time
                or segment.file_end_time <= 0
                or segment.file_end_time < file_start_time
            ):
                segments.remove(segment)


def slide_segments(segments: list, duration: float) -> list:
    """Shift every segment in `segments` by `duration` seconds without moving the overall
    start/end of the list - segments that slide entirely off either end are dropped, and
    the first/last segment's outer edge snaps back to the original bounds.
    """
    if not segments or duration == 0:
        return segments

    start_time = segments[0].start_time
    end_time = segments[-1].end_time
    file_start_time = segments[0].file_start_time
    file_end_time = segments[-1].file_end_time

    _shift(segments, float(duration))

    original_length = len(segments)
    _drop_overshooting(segments, start_time, end_time, file_start_time, file_end_time)
    if len(segments) != original_length:
        for index, segment in enumerate(segments):
            segment.id = index

    if segments:
        segments[-1].end_time = end_time
        segments[0].start_time = start_time
        segments[-1].file_end_time = file_end_time
        segments[0].file_start_time = file_start_time

    return segments


def run_slide(
    input_path,
    duration: float = 0.0,
    trim_start: Optional[float] = None,
    bitrate: str = "128k",
    ffmpeg_executable: str = "ffmpeg",
    ffprobe_executable: str = "ffprobe",
    on_log_line: Optional[Callable[[str], None]] = None,
) -> bool:
    """Shift a file's chapters by `duration` seconds (optionally trimming `trim_start`
    seconds off the beginning first) and rewrite the file in place.
    """
    on_log_line = on_log_line or (lambda line: None)
    slide_duration = duration - (trim_start or 0.0)

    book = Audiobook(bitrate=bitrate, ffmpeg_executable=ffmpeg_executable,
                      ffprobe_executable=ffprobe_executable, on_log_line=on_log_line)
    book.add_chapters_from_chaptered_file(input_path)
    if not book.chapters:
        on_log_line("Error: No chapters found!")
        return False

    end_time = book.chapters[-1].end_time
    file_end_time = book.chapters[-1].file_end_time

    if trim_start:
        for chapter in book.chapters.copy():
            if chapter.end_time < trim_start:
                book.chapters.remove(chapter)
            else:
                break
        if not book.chapters:
            on_log_line("Error: No chapters were left after trim.")
            return False
        book.chapters[0].start_time = 0.0
        book.chapters[0].file_start_time = 0.0
        book.chapters[-1].end_time = end_time - trim_start
        book.chapters[-1].file_end_time = file_end_time - trim_start

    book.chapters = slide_segments(book.chapters, slide_duration)
    if not book.chapters:
        on_log_line("Error: No chapters were left after slide.")
        return False

    return book.bind(input_path)

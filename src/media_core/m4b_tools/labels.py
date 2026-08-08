from __future__ import annotations

import re
from typing import Callable, Optional

from media_core.m4b_tools import probe as probe_module
from media_core.m4b_tools.audiobook import Audiobook
from media_core.m4b_tools.segment import Segment

_LABEL_LINE_RE = re.compile(r"^(?P<start_time>\d+\.?\d*)\s+(?P<end_time>\d+\.?\d*)\s+(?P<title>.*)\s*$")


def segments_from_audacity_labels(lines) -> list[Segment]:
    """Parse Audacity label-track lines into Segments.

    Audacity label end times are ignored - audiobook chapters must be contiguous and
    non-overlapping, so each segment's end is taken from the *next* label's start time.
    """
    segments: list[Segment] = []
    previous: Optional[dict] = None

    for line in lines:
        match = _LABEL_LINE_RE.search(line)
        if not match:
            continue
        if previous:
            segments.append(Segment(
                start_time=previous["start_time"],
                end_time=float(match["start_time"]),
                title=previous["title"],
            ))
        previous = {
            "start_time": float(match["start_time"]),
            "end_time": float(match["end_time"]),
            "title": match["title"],
        }

    if previous:
        segments.append(Segment(
            start_time=previous["start_time"],
            end_time=previous["end_time"],
            title=previous["title"],
        ))
    return segments


def audacity_labels_from_segments(segments) -> list[str]:
    return [f"{segment.start_time}\t{segment.start_time}\t{segment.title}" for segment in segments]


def read_label_file(path) -> list[Segment]:
    with open(path, encoding="utf-8") as handle:
        return segments_from_audacity_labels(handle.readlines())


def write_label_file(path, segments) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for label in audacity_labels_from_segments(segments):
            handle.write(f"{label}\n")


def apply_segments_to_book(
    segments,
    book_path,
    ffmpeg_executable: str = "ffmpeg",
    ffprobe_executable: str = "ffprobe",
    on_log_line: Optional[Callable[[str], None]] = None,
) -> bool:
    """Rewrite a book's chapters from an externally-sourced segment list (e.g. Audacity labels).

    Segments are clipped to the book's actual duration; a segment that starts entirely
    past the end is dropped rather than producing a zero-length trailing chapter.
    """
    new_book = Audiobook(
        ffmpeg_executable=ffmpeg_executable,
        ffprobe_executable=ffprobe_executable,
        on_log_line=on_log_line or (lambda line: None),
    )
    new_book.add_chapters_from_chaptered_file(book_path)  # seeds title/author/date only
    book_duration = probe_module.get_file_duration(book_path, ffprobe_executable)

    new_chapters = []
    for chapter in segments:
        end_time = chapter.end_time
        if end_time > book_duration > chapter.start_time:
            end_time = book_duration
        if end_time <= book_duration:
            new_chapters.append(Segment(
                start_time=chapter.start_time,
                end_time=end_time,
                title=chapter.title,
                backing_file=str(book_path),
                file_start_time=chapter.start_time,
                file_end_time=end_time,
            ))

    new_book.chapters = new_chapters
    return new_book.bind(book_path)

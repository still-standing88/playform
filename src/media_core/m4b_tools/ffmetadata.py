from __future__ import annotations

from typing import Optional

from media_core.m4b_tools.segment import Segment

_HEADER = ";FFMETADATA1"
_DEFAULT_GLOBAL_FIELDS = {
    "major_brand": "M4A",
    "minor_version": "512",
    "compatible_brands": "M4A isomiso2",
}


def build_ffmetadata(global_fields: dict, chapters: list[Segment], include_defaults: bool = True) -> str:
    """Build the ;FFMETADATA1 text ffmpeg's `-i metadata.txt -map_metadata 1` accepts.

    `global_fields` entries with an empty/None value are skipped, so callers can pass a
    dict with unset fields left as None rather than filtering it themselves.
    """
    lines = [_HEADER]
    if include_defaults:
        for key, value in _DEFAULT_GLOBAL_FIELDS.items():
            lines.append(f"{key}={value}")
    for key, value in global_fields.items():
        if value:
            lines.append(f"{key}={value}")

    for chapter in chapters:
        lines.append("[CHAPTER]")
        lines.append("TIMEBASE=1/1000")
        lines.append(f"START={int(chapter.start_time * 1000)}")
        lines.append(f"END={int(chapter.end_time * 1000)}")
        if chapter.title:
            lines.append(f"title={chapter.title}")

    return "\n".join(lines) + "\n"


def parse_ffmetadata(text: str) -> tuple[dict, list[Segment]]:
    """Parse ;FFMETADATA1 text into (global_fields, chapters).

    Chapters missing START/END are dropped - they can't be turned into a usable Segment.
    """
    global_fields: dict = {}
    chapters: list[Segment] = []
    current: Optional[dict] = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        if line == "[CHAPTER]":
            if current is not None:
                chapter = _chapter_from_fields(current)
                if chapter is not None:
                    chapters.append(chapter)
            current = {}
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        (current if current is not None else global_fields)[key] = value

    if current is not None:
        chapter = _chapter_from_fields(current)
        if chapter is not None:
            chapters.append(chapter)

    return global_fields, chapters


def _chapter_from_fields(fields: dict) -> Optional[Segment]:
    start_raw = fields.get("START")
    end_raw = fields.get("END")
    if start_raw is None or end_raw is None:
        return None

    timebase = fields.get("TIMEBASE", "1/1000")
    try:
        num, den = timebase.split("/")
        scale = int(num) / int(den)
    except (ValueError, ZeroDivisionError):
        scale = 1 / 1000

    try:
        return Segment(
            start_time=int(start_raw) * scale,
            end_time=int(end_raw) * scale,
            title=fields.get("title"),
        )
    except (TypeError, ValueError):
        return None

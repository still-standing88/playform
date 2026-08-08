from __future__ import annotations

import re

DEFAULT_CHAPTER_TEMPLATE = "{book_title}/{chapter_num:02d} - {chapter_title}.{ext}"

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')
_REPEATED_UNDERSCORES = re.compile(r"_+")
_NATURAL_SORT_SPLIT = re.compile(r"(\d+)")


def natural_sort_key(name: str) -> list:
    """Sort key that orders embedded numbers numerically (`track2` before `track10`)."""
    return [int(part) if part.isdigit() else part.lower() for part in _NATURAL_SORT_SPLIT.split(name)]


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """Strip characters that are invalid in Windows/POSIX filenames."""
    name = _INVALID_FILENAME_CHARS.sub("_", name)
    name = _REPEATED_UNDERSCORES.sub("_", name)
    name = name.strip(" .")
    if not name:
        name = "untitled"
    return name[:max_length]


def format_time(seconds: float) -> str:
    """Format a duration in seconds as a short human-readable string (e.g. `1h 2m 3s`)."""
    seconds = max(0, seconds)
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        minutes, secs = divmod(int(seconds), 60)
        return f"{minutes}m {secs}s"
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}h {minutes}m {secs}s"


def format_chapter_filename(template: str, variables: dict) -> str:
    """Format a chapter output path from a naming template.

    Falls back to `DEFAULT_CHAPTER_TEMPLATE` if the template references an unknown
    variable, so a typo'd template degrades gracefully instead of aborting a batch split.
    """
    try:
        return template.format(**variables)
    except (KeyError, IndexError, ValueError):
        return DEFAULT_CHAPTER_TEMPLATE.format(**variables)

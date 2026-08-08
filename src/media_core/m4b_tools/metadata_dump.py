from __future__ import annotations

import csv
import sys
from pathlib import Path

from media_core.m4b_tools import probe as probe_module

METADATA_FIELDNAMES = [
    "file", "chapter_num", "chapter_title", "chapter_start", "chapter_end", "chapter_duration",
    "title", "author", "album", "album_artist", "narrator", "genre", "year",
    "codec", "bitrate", "sample_rate", "channels",
]


def dump_metadata_rows(path, ffprobe_executable: str = "ffprobe") -> list:
    """Build one CSV-ready row per chapter, or a single whole-file row if there are none."""
    probe = probe_module.run_probe(path, ffprobe_executable)
    if probe is None:
        return []

    tags = probe.tags or {}
    audio = probe.audio_stream or {}
    common = {
        "file": Path(path).name,
        "title": tags.get("title", ""),
        "author": tags.get("author") or tags.get("artist", ""),
        "album": tags.get("album", ""),
        "album_artist": tags.get("album_artist", ""),
        "narrator": tags.get("narrator") or tags.get("composer", ""),
        "genre": tags.get("genre", ""),
        "year": (tags.get("date") or "")[:4],
        "codec": audio.get("codec_name", ""),
        "bitrate": audio.get("bit_rate", ""),
        "sample_rate": audio.get("sample_rate", ""),
        "channels": audio.get("channels", ""),
    }

    if not probe.chapters:
        duration = probe.duration or 0.0
        return [{
            **common,
            "chapter_num": 1,
            "chapter_title": tags.get("title", "Chapter 1"),
            "chapter_start": 0.0,
            "chapter_end": duration,
            "chapter_duration": duration,
        }]

    rows = []
    for index, chapter in enumerate(probe.chapters, start=1):
        start = float(chapter.get("start_time", 0))
        end = float(chapter.get("end_time", 0))
        rows.append({
            **common,
            "chapter_num": index,
            "chapter_title": chapter.get("tags", {}).get("title", f"Chapter {index}"),
            "chapter_start": start,
            "chapter_end": end,
            "chapter_duration": end - start,
        })
    return rows


def write_metadata_csv(rows: list, output_file=None) -> None:
    """Write rows built by `dump_metadata_rows` as CSV, to a file path, an open stream, or stdout."""
    if output_file is None:
        _write_csv(rows, sys.stdout)
        return
    if hasattr(output_file, "write"):
        _write_csv(rows, output_file)
        return
    with open(output_file, "w", encoding="utf-8", newline="") as handle:
        _write_csv(rows, handle)


def _write_csv(rows: list, stream) -> None:
    writer = csv.DictWriter(stream, fieldnames=METADATA_FIELDNAMES)
    writer.writeheader()
    writer.writerows(rows)

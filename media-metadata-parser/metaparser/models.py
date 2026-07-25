"""Phase-4 raw-storage models.

Per plan.md: "Store per-file output as raw blobs first... Build the
alias/normalization table after you've scanned a real sample and seen what
key names actually show up — not before." RawFileMetadata is exactly that
raw-blob container — bext_raw/ixml_raw/info_raw/ucs_from_filename kept
separate and shaped as they came out of their respective interpreters,
nothing unified or renamed here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RawFileMetadata:
    file_path: str
    file_format: str
    """One of: 'wav', 'aiff', 'rf64', or a mutagen/exiftool-recognized format
    name (e.g. 'MP3', 'FLAC', 'MP4') for files that went through the tags/
    path instead of the chunk-walker path."""

    bext_raw: dict | None = None
    ixml_raw: dict | None = None
    info_raw: dict | None = None
    """RIFF LIST/INFO fourCC fields, friendly-named where known."""
    cue_points: list[dict] = field(default_factory=list)
    adtl_labels: dict[int, dict] = field(default_factory=dict)
    axml_raw: str | None = None

    ucs_from_filename: dict | None = None
    """Result of ucs.filename_parser.parse_filename, as a plain dict (see
    to_plain_dict there) — kept separate from ixml_raw even when both carry
    category info, since disagreement between them is itself a signal."""

    tags_raw: dict | None = None
    """Output of tags.audio_tags.extract / tags.video_tags.extract for
    formats without a chunk-walker path, or as a supplementary source
    (plain title/artist ID3-in-RIFF tags) for WAV/AIFF."""

    ucs_ixml_cross_check: dict | None = None

    errors: list[str] = field(default_factory=list)
    """Human-readable notes about anything that failed opportunistically
    during extraction (a chunk that wouldn't parse, etc) — never raised,
    always logged here so a scan can report "N files had partial extraction"
    instead of silently losing that information."""

    @property
    def filename(self) -> str:
        return Path(self.file_path).name

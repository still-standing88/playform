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
    matroska_raw: dict | None = None
    """Full EBML element tree for Matroska/WebM files, as produced by
    metaparser.interpreters.matroska.parse — nested dict, friendly-named
    where known, stopped before the first Cluster (media data)."""
    realmedia_raw: dict | None = None
    """RealMedia (.rm/.rmvb) object tree, as produced by
    metaparser.interpreters.realmedia.parse — CONT/MDPR decoded, every other
    object type kept raw under its object_id."""
    flv_raw: dict | None = None
    """FLV (.flv/.f4v) tag summary, as produced by
    metaparser.interpreters.flash_video.parse — decoded script-data
    (onMetaData) properties plus audio/video tag counts."""
    mpeg_raw: dict | None = None
    """MPEG-1/2 audio/video frame header fields (.mpg/.mpeg/.m2v), as
    produced by metaparser.interpreters.mpeg.parse — technical stream
    parameters only, this format carries no descriptive tags."""
    m2ts_raw: dict | None = None
    """MPEG-2 Transport Stream program/stream map (.ts/.m2ts/.mts), as
    produced by metaparser.interpreters.m2ts.parse — discovered PAT/PMT
    structure plus PCR-derived duration."""
    dv_raw: dict | None = None
    """DV (raw Digital Video) format profile + VAUX/AAUX metadata (.dv), as
    produced by metaparser.interpreters.dv.parse."""
    amr_raw: dict | None = None
    """AMR (.amr) variant/frame-count/duration, as produced by
    metaparser.interpreters.amr.parse — AMR defines no metadata mechanism
    beyond this, confirmed by there being no ExifTool module for it."""
    udta_raw: dict | None = None
    """Legacy pre-iTunes QuickTime 'udta' text atoms for MP4-family video
    files (.mov/.mp4/.m4v/.3gp/...), as produced by
    metaparser.interpreters.quicktime_udta.parse — supplementary to
    tags_raw's mutagen-based ilst reading, empty for files that only use
    the modern ilst path (which mutagen already covers)."""
    caf_raw: dict | None = None
    """CAF (.caf) chunk data, as produced by metaparser.interpreters.caf.parse
    — 'desc' (audio description) and 'info' (free-form key/value text
    metadata, dynamically walked) decoded, other chunks kept raw by fourCC."""
    dts_raw: dict | None = None
    """DTS (.dts) core frame header fields, as produced by
    metaparser.interpreters.dts.parse — technical stream parameters only
    (this project holds no ExifTool reference or bundled spec for DTS, so
    decoding is deliberately scoped to the fields it's confident about)."""
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

"""AMR interpreter, built on metaparser.chunks.amr_walker.

There is nothing here beyond technical stream parameters — AMR genuinely
defines no metadata/tag mechanism, confirmed by there being no ExifTool
module for it at all (unlike every other format in this project, where
ExifTool's coverage was at least a cross-check). This module exists mainly
so AMR files show up in the index with *something* (variant, frame count,
duration) rather than nothing, consistent with the project's "most audio
files" goal — not because there's a rich tag surface being dynamically
walked here.
"""

from __future__ import annotations

from media_core.metaparser.chunks import amr_walker


def parse(data: bytes) -> dict:
    variant, frame_count = amr_walker.walk(data)
    return {
        "variant": "AMR-WB" if variant == "wb" else "AMR-NB",
        "frame_count": frame_count,
        "duration_secs": frame_count * amr_walker.FRAME_DURATION_SECS,
    }

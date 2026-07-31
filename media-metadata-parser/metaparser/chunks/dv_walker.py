"""DV (raw Digital Video) sync locator — .dv.

DV has no chunk/element framing at all: a DV frame is a fixed grid of
80-byte DIF blocks (1 Header + 2 Subcode + 3 VAUX + ... + Audio + Video
blocks, repeated per DIF sequence), and there's no length-prefixed container
around any of it — a raw .dv file is just this block grid start-to-end. This
module's only job is finding where that grid actually starts in the file
(some encoders pad or offset it), via the DIF Header block's own byte
signature. Once `start` is known, metaparser.interpreters.dv reads
fixed-offset fields directly out of the buffer — those offsets are exact,
disclosed transliterations of archive/exiftool's DV.pm (see ../../CREDITS.md),
since the DV bitstream layout can't be independently re-derived from general
knowledge with the confidence this project holds itself to elsewhere.

Only the common-case sync pattern is implemented (the Header DIF block's
literal byte signature at a 12000-byte search window's start) — ExifTool's
DV.pm also has a secondary fallback regex for less common header placements
that this module doesn't attempt to replicate, since it can't be verified
without a real sample file to test against. A file that only matches the
fallback case will report as not-a-DV-file here rather than risk a wrong
offset.
"""

from __future__ import annotations

SEARCH_WINDOW = 12000
HEADER_SIGNATURE_PREFIX = b"\x1f\x07\x00"
_MIN_GRID_SIZE = 80 * 6  # must have a full Header + Subcode + VAUX run available


def find_dif_start(data: bytes) -> int | None:
    """Returns the byte offset of the DIF Header block, or None if the
    common-case signature isn't found (in the first SEARCH_WINDOW bytes) or
    there isn't enough data past it for a minimal DIF grid."""
    window = data[:SEARCH_WINDOW]
    idx = 0
    while True:
        idx = window.find(HEADER_SIGNATURE_PREFIX, idx)
        if idx == -1:
            return None
        if idx + 3 < len(window) and window[idx + 3] in (0x3F, 0xBF):
            if idx + _MIN_GRID_SIZE <= len(data):
                return idx
            return None
        idx += 1

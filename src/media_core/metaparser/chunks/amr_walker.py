"""AMR (Adaptive Multi-Rate speech codec) frame walker — .amr.

AMR has no metadata mechanism at all — a file is just a 6- or 9-byte magic
header identifying the variant, followed directly by a raw sequence of
speech frames with no container, no chunk framing, nothing resembling a tag.
The only things extractable are technical: which variant (narrowband vs
wideband), how many frames, and — since every frame is a fixed 20ms of
audio regardless of bitrate — a duration estimate from the frame count.

Frame sizes are keyed by a 4-bit "frame type" index in each frame's 1-byte
header, per RFC 4867 (IETF's AMR RTP payload spec, a public standard — no
ExifTool module exists for this format at all, so there's nothing to
cross-check against there; see ../../CREDITS.md). Reproduced from general
knowledge of the standard, not verified against a real sample file. Frame
type indices outside the ones actually used for real speech/comfort-noise
frames (SID) are marked unknown rather than guessed at — walking stops
there rather than risk misaligning every frame after a wrong size guess.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

MAGIC_NB = b"#!AMR\n"
MAGIC_WB = b"#!AMR-WB\n"

# frame_type_index -> total frame size in bytes, INCLUDING the 1-byte frame
# header (RFC 4867 Table 1a for narrowband, Table 1b-equivalent for
# wideband). Index 8(NB)/9(WB) is SID (comfort noise); NB index 15 / WB
# index 9 is NO_DATA (header only, no speech payload). Indices not listed
# are reserved/future-use in the RFC and are never emitted by real encoders
# for actual speech — treated as "unknown, stop walking" rather than guessed.
_NB_FRAME_SIZES = {0: 13, 1: 14, 2: 16, 3: 18, 4: 20, 5: 21, 6: 27, 7: 32, 8: 6, 15: 1}
_WB_FRAME_SIZES = {0: 18, 1: 24, 2: 33, 3: 37, 4: 41, 5: 47, 6: 51, 7: 59, 8: 61, 9: 6, 10: 1}

FRAME_DURATION_SECS = 0.02  # every AMR frame (either variant) is 20ms


class AmrParseError(Exception):
    pass


def detect_variant(data: bytes) -> str | None:
    """Returns 'nb', 'wb', or None if neither magic matches. WB's magic is
    checked first since it's a superset prefix-adjacent string of NB's."""
    if data.startswith(MAGIC_WB):
        return "wb"
    if data.startswith(MAGIC_NB):
        return "nb"
    return None


def walk(data: bytes) -> tuple[str, int]:
    """Returns (variant, frame_count). Walks frame-by-frame using the
    RFC 4867 size table, stopping (without raising) at the first reserved/
    unrecognized frame type index, truncated frame, or end of data —
    whichever comes first. frame_count reflects only the frames walked
    before stopping, so it's always a safe lower bound, never an overcount.
    """
    variant = detect_variant(data)
    if variant is None:
        raise AmrParseError("no AMR magic header found (neither '#!AMR\\n' nor '#!AMR-WB\\n')")

    sizes = _NB_FRAME_SIZES if variant == "nb" else _WB_FRAME_SIZES
    pos = len(MAGIC_WB if variant == "wb" else MAGIC_NB)
    end = len(data)
    frame_count = 0

    while pos < end:
        frame_type = (data[pos] >> 3) & 0x0F
        frame_size = sizes.get(frame_type)
        if frame_size is None:
            logger.info(
                "AMR frame type index %d at offset %d isn't a recognized speech/SID/no-data "
                "size — stopping frame walk here (%d frames counted so far)",
                frame_type,
                pos,
                frame_count,
            )
            break
        if pos + frame_size > end:
            logger.info(
                "AMR frame at offset %d declares %d bytes but only %d remain — stopping walk",
                pos,
                frame_size,
                end - pos,
            )
            break
        pos += frame_size
        frame_count += 1

    return variant, frame_count

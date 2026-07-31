"""ISO Base Media File Format (ISO-BMFF) box walker — the container MP4,
QuickTime .mov, and 3GP are all built on (ISO/IEC 14496-12).

Box shape: 4-byte size (big-endian uint32) + 4-byte type (ASCII fourCC) +
payload. size==1 means the real size is a 64-bit value in the 8 bytes
immediately following the fourCC (for boxes too large for 32 bits); size==0
means "this box runs to the end of whatever byte range it's in" (legal at
the outermost level, per spec).

A file is a flat top-level sequence of boxes (typically 'ftyp', 'moov',
'mdat', ...) — like riff_walker/ebml_walker, this module only walks one
flat level at a time; a caller recurses into a container box's own payload
by calling walk() again on it (metaparser.interpreters.quicktime_udta does
this for moov -> udta). Same contract as every other walker here: log and
truncate on anything malformed, never raise past the initial sanity check.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_BOX_HEADER_SIZE = 8  # size(4) + type(4)
_EXTENDED_SIZE_FIELD = 8  # additional 8 bytes when size == 1


@dataclass(frozen=True)
class RawBox:
    box_type: str
    offset: int
    """Byte offset of the box payload, past its header (8 or 16 bytes)."""
    raw: bytes
    size_declared: int
    """Total box size as declared (including its own header) — ISO-BMFF's
    own convention, like RealMedia's object size and unlike RIFF's."""


class Mp4ParseError(Exception):
    pass


def _is_plausible_fourcc(raw: bytes) -> bool:
    return all(0x20 <= b <= 0x7E for b in raw)


def is_iso_bmff(data: bytes) -> bool:
    """ISO-BMFF has no fixed magic byte sequence (the first box can
    legitimately be 'ftyp', 'moov', 'free', 'skip', 'wide', or others,
    depending on encoder/era) — the closest thing to a signature is that the
    first 8 bytes must parse as a plausible box header: a printable-ASCII
    fourCC, and a declared size that isn't obviously nonsense. "Obviously
    nonsense" specifically includes claiming to be bigger than the entire
    buffer — without that check, arbitrary 4-byte magic strings from other
    formats (e.g. RIFF's own "RIFF" interpreted as a big-endian size) can
    read as a huge-but-technically-nonzero size and false-positive.
    """
    if len(data) < _BOX_HEADER_SIZE:
        return False
    declared_size = struct.unpack_from(">I", data, 0)[0]
    box_type = data[4:8]
    if not _is_plausible_fourcc(box_type):
        return False
    if declared_size in (0, 1):
        return True  # "runs to end" / extended-size — can't sanity-check further without more parsing
    return _BOX_HEADER_SIZE <= declared_size <= len(data)


def walk(data: bytes) -> list[RawBox]:
    boxes: list[RawBox] = []
    pos = 0
    end = len(data)

    while pos < end:
        if pos + _BOX_HEADER_SIZE > end:
            logger.warning(
                "truncated ISO-BMFF box header at offset %d (%d bytes left) — stopping walk",
                pos,
                end - pos,
            )
            break

        declared_size = struct.unpack_from(">I", data, pos)[0]
        box_type_raw = data[pos + 4 : pos + 8]
        # latin-1, not ascii+replace: classic QuickTime fourCCs use the
        # non-ASCII byte 0xA9 ('\xa9nam', '\xa9ART', '\xa9day', ...) —
        # ascii+replace would collapse every one of those to the same
        # U+FFFD-prefixed key, silently colliding distinct atoms in a
        # caller's result dict. latin-1 maps every byte 1:1 and can't fail,
        # so 0xA9 decodes to the actual '©' character, matching how Apple's
        # own QTFF docs write these fourCCs.
        box_type = box_type_raw.decode("latin-1")

        header_size = _BOX_HEADER_SIZE
        if declared_size == 1:
            if pos + _BOX_HEADER_SIZE + _EXTENDED_SIZE_FIELD > end:
                logger.warning(
                    "box %r at offset %d declares a 64-bit extended size but the field itself "
                    "is truncated — stopping walk",
                    box_type,
                    pos,
                )
                break
            declared_size = struct.unpack_from(">Q", data, pos + _BOX_HEADER_SIZE)[0]
            header_size += _EXTENDED_SIZE_FIELD

        if declared_size == 0:
            payload_start = pos + header_size
            boxes.append(
                RawBox(box_type=box_type, offset=payload_start, raw=data[payload_start:end], size_declared=0)
            )
            break  # size-0 box runs to the end of this byte range by definition

        if declared_size < header_size:
            logger.warning(
                "box %r at offset %d declares size %d, smaller than its own %d-byte header — "
                "stopping walk (can't trust further offsets)",
                box_type,
                pos,
                declared_size,
                header_size,
            )
            break

        payload_start = pos + header_size
        payload_end = pos + declared_size

        if payload_end > end:
            logger.warning(
                "box %r at offset %d declares total size %d but only %d bytes remain — truncating",
                box_type,
                pos,
                declared_size,
                end - pos,
            )
            boxes.append(
                RawBox(box_type=box_type, offset=payload_start, raw=data[payload_start:end], size_declared=declared_size)
            )
            break

        boxes.append(
            RawBox(
                box_type=box_type,
                offset=payload_start,
                raw=data[payload_start:payload_end],
                size_declared=declared_size,
            )
        )
        pos = payload_end

    return boxes


def find_path(data: bytes, *path: str) -> bytes | None:
    """Convenience: walks nested container boxes by type name, e.g.
    find_path(file_bytes, 'moov', 'udta') returns that box's raw payload, or
    None if any step of the path isn't present. Doesn't care whether an
    intermediate box is "supposed to" be a container — it just tries to walk
    its payload as boxes and see if the next path element shows up.
    """
    current = data
    for box_type in path:
        boxes = walk(current)
        match = next((b for b in boxes if b.box_type == box_type), None)
        if match is None:
            return None
        current = match.raw
    return current

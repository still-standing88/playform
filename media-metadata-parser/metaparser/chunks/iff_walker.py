"""IFF/AIFF chunk walker.

Structurally identical to RIFF (4-byte ID + 4-byte size + payload + optional
pad byte) except everything is big-endian, per the original EA IFF 85 spec
that AIFF/AIFC inherit. Same contract as riff_walker: no interpretation,
tolerant of lying size fields and truncation.
"""

from __future__ import annotations

import logging
import struct

from metaparser.chunks.riff_walker import CHUNK_HEADER_SIZE, RawChunk

logger = logging.getLogger(__name__)

FORM_HEADER_SIZE = 12  # "FORM" + size(4) + form type (4)


class IffParseError(Exception):
    pass


def is_iff(data: bytes) -> bool:
    return len(data) >= FORM_HEADER_SIZE and data[0:4] == b"FORM"


def form_type(data: bytes) -> str | None:
    """Returns the 4-char form type, typically 'AIFF' or 'AIFC'."""
    if not is_iff(data):
        return None
    return data[8:12].decode("ascii", errors="replace")


def walk(data: bytes) -> list[RawChunk]:
    if not is_iff(data):
        raise IffParseError("not an IFF file (missing 'FORM' magic)")

    declared_form_size = struct.unpack_from(">I", data, 4)[0]
    # As with RIFF, the size field covers everything after itself (form type
    # + chunks), measured from offset 8, not from the end of the 12-byte
    # FORM+size+form-type header.
    actual_payload_size = len(data) - 8
    if declared_form_size not in (actual_payload_size, actual_payload_size + 1):
        logger.warning(
            "FORM size field says %d bytes but file has %d bytes of payload — "
            "walking what's there",
            declared_form_size,
            actual_payload_size,
        )

    chunks: list[RawChunk] = []
    pos = FORM_HEADER_SIZE
    end = len(data)

    while pos < end:
        if pos + CHUNK_HEADER_SIZE > end:
            logger.warning(
                "truncated chunk header at offset %d (only %d bytes left) — stopping walk",
                pos,
                end - pos,
            )
            break

        chunk_id = data[pos : pos + 4].decode("ascii", errors="replace")
        declared_size = struct.unpack_from(">I", data, pos + 4)[0]
        payload_start = pos + CHUNK_HEADER_SIZE
        payload_end = payload_start + declared_size

        if payload_end > end:
            logger.warning(
                "chunk %r at offset %d declares size %d but only %d bytes remain — truncating",
                chunk_id,
                pos,
                declared_size,
                end - payload_start,
            )
            raw = data[payload_start:end]
            chunks.append(
                RawChunk(chunk_id=chunk_id, offset=payload_start, raw=raw, size_declared=declared_size)
            )
            break

        raw = data[payload_start:payload_end]
        chunks.append(
            RawChunk(chunk_id=chunk_id, offset=payload_start, raw=raw, size_declared=declared_size)
        )

        pos = payload_end
        if declared_size % 2 == 1 and pos < end:
            pos += 1

    return chunks

"""RIFF/WAV chunk walker.

RIFF is little-endian: 4-byte ASCII ID, 4-byte uint32 size, payload, then an
optional single pad byte if size is odd. This module does zero interpretation —
it just yields (chunk_id, offset, raw_bytes) tuples. Every payload interpreter
in metaparser.interpreters depends on this being correct, so it favors logging
and skipping over raising on anything malformed.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass

logger = logging.getLogger(__name__)

RIFF_HEADER_SIZE = 12  # "RIFF" + size(4) + form type (4)
CHUNK_HEADER_SIZE = 8  # id(4) + size(4)


@dataclass(frozen=True)
class RawChunk:
    chunk_id: str
    offset: int
    """Byte offset of the chunk payload (i.e. just past the 8-byte header)."""
    raw: bytes
    size_declared: int
    """Size as declared in the header, kept even if it disagreed with what was
    actually readable (truncated file) — callers can tell the two apart via
    len(raw) != size_declared."""


class RiffParseError(Exception):
    pass


def is_riff(data: bytes) -> bool:
    return len(data) >= RIFF_HEADER_SIZE and data[0:4] == b"RIFF"


def form_type(data: bytes) -> str | None:
    """Returns the 4-char form type (e.g. 'WAVE'), or None if not RIFF."""
    if not is_riff(data):
        return None
    return data[8:12].decode("ascii", errors="replace")


def walk(data: bytes) -> list[RawChunk]:
    """Walk top-level RIFF chunks. Does not recurse into LIST sub-chunks —
    that's the LIST/INFO interpreter's job, since it needs to know the LIST
    'type' fourCC (INFO, adtl, ...) to decide how to walk its own contents.
    """
    if not is_riff(data):
        raise RiffParseError("not a RIFF file (missing 'RIFF' magic)")

    declared_riff_size = struct.unpack_from("<I", data, 4)[0]
    # The size field covers everything after itself — the 4-byte form type
    # plus all chunks — so it's measured from offset 8, not from the end of
    # the 12-byte RIFF+size+form-type header.
    actual_payload_size = len(data) - 8
    if declared_riff_size not in (actual_payload_size, actual_payload_size + 1):
        logger.warning(
            "RIFF size field says %d bytes but file has %d bytes of payload "
            "(size field lied, or file is truncated) — walking what's there",
            declared_riff_size,
            actual_payload_size,
        )

    chunks: list[RawChunk] = []
    pos = RIFF_HEADER_SIZE
    end = len(data)

    while pos < end:
        if pos + CHUNK_HEADER_SIZE > end:
            logger.warning(
                "truncated chunk header at offset %d (only %d bytes left) — stopping walk",
                pos,
                end - pos,
            )
            break

        chunk_id_raw = data[pos : pos + 4]
        try:
            chunk_id = chunk_id_raw.decode("ascii")
        except UnicodeDecodeError:
            chunk_id = chunk_id_raw.decode("latin-1")
            logger.warning(
                "non-ASCII chunk id %r at offset %d — keeping as latin-1, likely a corrupt walk",
                chunk_id_raw,
                pos,
            )

        declared_size = struct.unpack_from("<I", data, pos + 4)[0]
        payload_start = pos + CHUNK_HEADER_SIZE
        payload_end = payload_start + declared_size

        if declared_size == 0xFFFFFFFF:
            # RF64/BW64 sentinel — the real size lives in the ds64 chunk.
            # Caller (rf64.py) is responsible for re-walking with the resolved
            # size; here we just hand back what we can see and stop, since we
            # have no idea how long the payload actually is.
            logger.info(
                "chunk %r at offset %d has RF64 sentinel size (0xFFFFFFFF) — "
                "caller must resolve via ds64 table",
                chunk_id,
                pos,
            )
            chunks.append(
                RawChunk(chunk_id=chunk_id, offset=payload_start, raw=b"", size_declared=declared_size)
            )
            break

        if payload_end > end:
            logger.warning(
                "chunk %r at offset %d declares size %d but only %d bytes remain — "
                "truncating to what's available",
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
        if declared_size % 2 == 1:
            # Pad byte required by spec, but some encoders forget it on the
            # final chunk — only consume it if it's actually there.
            if pos < end:
                pos += 1
            else:
                logger.info(
                    "chunk %r at offset %d is odd-sized (%d) with no trailing pad byte "
                    "(file ends exactly on the payload) — not an error, just noting it",
                    chunk_id,
                    payload_start,
                    declared_size,
                )

    return chunks


def walk_sub_chunks(data: bytes) -> list[RawChunk]:
    """Walk a flat run of ID+size+payload chunks with no RIFF/form header —
    used for LIST sub-chunks and other nested chunk lists that share RIFF's
    little-endian ID+size shape but aren't themselves a full RIFF file.
    """
    chunks: list[RawChunk] = []
    pos = 0
    end = len(data)

    while pos < end:
        if pos + CHUNK_HEADER_SIZE > end:
            logger.warning(
                "truncated sub-chunk header at offset %d (only %d bytes left)",
                pos,
                end - pos,
            )
            break

        chunk_id = data[pos : pos + 4].decode("ascii", errors="replace")
        declared_size = struct.unpack_from("<I", data, pos + 4)[0]
        payload_start = pos + CHUNK_HEADER_SIZE
        payload_end = payload_start + declared_size

        if payload_end > end:
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

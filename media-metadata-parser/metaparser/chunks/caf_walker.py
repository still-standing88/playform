"""CAF (Core Audio Format) chunk walker — .caf.

Apple's own container format, publicly documented at
https://developer.apple.com/library/archive/documentation/MusicAudio/Reference/CAFSpec/
(no ExifTool module exists for this format — nothing to cross-check against
there, so this is built directly from Apple's spec; see ../../CREDITS.md).

Shape: an 8-byte file header ('caff' magic + 2-byte version + 2-byte flags),
then a flat sequence of chunks: 4-byte ASCII type + 8-byte **signed** int64
size (a size of -1 means "runs to the end of the file" — CAF's own
documented convention for a streamed/unknown-length chunk, distinct from
RealMedia's or EBML's own version of the same idea) + payload.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass

logger = logging.getLogger(__name__)

FILE_HEADER_SIZE = 8  # 'caff'(4) + version(2) + flags(2)
CHUNK_HEADER_SIZE = 12  # type(4) + size(8)
MAGIC = b"caff"


@dataclass(frozen=True)
class RawChunk:
    chunk_type: str
    offset: int
    """Byte offset of the chunk payload, past its 12-byte header."""
    raw: bytes
    size_declared: int


class CafParseError(Exception):
    pass


def is_caf(data: bytes) -> bool:
    return len(data) >= FILE_HEADER_SIZE and data[0:4] == MAGIC


def walk(data: bytes) -> list[RawChunk]:
    if not is_caf(data):
        raise CafParseError("not a CAF file (missing 'caff' magic)")

    chunks: list[RawChunk] = []
    pos = FILE_HEADER_SIZE
    end = len(data)

    while pos < end:
        if pos + CHUNK_HEADER_SIZE > end:
            logger.warning(
                "truncated CAF chunk header at offset %d (%d bytes left) — stopping walk",
                pos,
                end - pos,
            )
            break

        chunk_type = data[pos : pos + 4].decode("latin-1")
        declared_size = struct.unpack_from(">q", data, pos + 4)[0]  # signed
        payload_start = pos + CHUNK_HEADER_SIZE

        if declared_size == -1:
            chunks.append(
                RawChunk(chunk_type=chunk_type, offset=payload_start, raw=data[payload_start:end], size_declared=-1)
            )
            break  # runs to end of file by definition

        if declared_size < 0:
            logger.warning(
                "CAF chunk %r at offset %d declares an invalid negative size %d — stopping walk",
                chunk_type,
                pos,
                declared_size,
            )
            break

        payload_end = payload_start + declared_size
        if payload_end > end:
            logger.warning(
                "CAF chunk %r at offset %d declares size %d but only %d bytes remain — truncating",
                chunk_type,
                pos,
                declared_size,
                end - payload_start,
            )
            chunks.append(
                RawChunk(chunk_type=chunk_type, offset=payload_start, raw=data[payload_start:end], size_declared=declared_size)
            )
            break

        chunks.append(
            RawChunk(
                chunk_type=chunk_type,
                offset=payload_start,
                raw=data[payload_start:payload_end],
                size_declared=declared_size,
            )
        )
        pos = payload_end

    return chunks

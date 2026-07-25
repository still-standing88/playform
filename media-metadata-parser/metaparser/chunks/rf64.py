"""RF64/BW64 support (EBU Tech 3306 / ITU-R BS.2088).

A RIFF variant for files that exceed the 32-bit (~4GB) size limit. The outer
form ID becomes 'RF64' (or 'BW64' under the newer ITU spec) with the 32-bit
size field at offset 4 forced to 0xFFFFFFFF, and a 'ds64' chunk is inserted
immediately after the form header (before 'fmt ') carrying the real 64-bit
sizes plus a lookup table for any other chunk that also overflowed 32 bits.

Unlikely to show up in an SFX library (files that size are rare there), but
per plan.md's own note: it should be recognized and not silently corrupt a
scan, not necessarily fully supported.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass

from metaparser.chunks.riff_walker import CHUNK_HEADER_SIZE, RIFF_HEADER_SIZE, RawChunk

logger = logging.getLogger(__name__)

RF64_SENTINEL_SIZE = 0xFFFFFFFF
DS64_MIN_SIZE = 28  # riffSize(8) + dataSize(8) + sampleCount(8) + tableLength(4)


@dataclass(frozen=True)
class Ds64Table:
    riff_size: int
    data_size: int
    sample_count: int
    chunk_sizes: dict[str, int]
    """Overflow sizes for chunks other than 'data', keyed by chunk id. Per
    spec a chunk id can repeat in the table only if it repeats in the file,
    which we don't expect here — last one wins if it somehow does."""


class Rf64ParseError(Exception):
    pass


def is_rf64(data: bytes) -> bool:
    return len(data) >= RIFF_HEADER_SIZE and data[0:4] in (b"RF64", b"BW64")


def parse_ds64(raw: bytes) -> Ds64Table:
    if len(raw) < DS64_MIN_SIZE:
        raise Rf64ParseError(f"ds64 chunk too short: {len(raw)} bytes, need >= {DS64_MIN_SIZE}")

    riff_size = int.from_bytes(raw[0:4], "little") | (int.from_bytes(raw[4:8], "little") << 32)
    data_size = int.from_bytes(raw[8:12], "little") | (int.from_bytes(raw[12:16], "little") << 32)
    sample_count = int.from_bytes(raw[16:20], "little") | (int.from_bytes(raw[20:24], "little") << 32)
    table_length = struct.unpack_from("<I", raw, 24)[0]

    chunk_sizes: dict[str, int] = {}
    table_start = 28
    entry_size = 12  # id(4) + sizeLow(4) + sizeHigh(4)
    for i in range(table_length):
        entry_off = table_start + i * entry_size
        if entry_off + entry_size > len(raw):
            logger.warning(
                "ds64 table declares %d entries but only %d fit in %d bytes — stopping at entry %d",
                table_length,
                (len(raw) - table_start) // entry_size,
                len(raw),
                i,
            )
            break
        chunk_id = raw[entry_off : entry_off + 4].decode("ascii", errors="replace")
        size = int.from_bytes(raw[entry_off + 4 : entry_off + 8], "little") | (
            int.from_bytes(raw[entry_off + 8 : entry_off + 12], "little") << 32
        )
        chunk_sizes[chunk_id] = size

    return Ds64Table(riff_size=riff_size, data_size=data_size, sample_count=sample_count, chunk_sizes=chunk_sizes)


def walk(data: bytes) -> list[RawChunk]:
    """Walk an RF64/BW64 file's top-level chunks, resolving any 0xFFFFFFFF
    sentinel sizes (expected on 'data', possible on others) via the ds64
    table. Assumes 'ds64' is the first chunk after the form header, per spec.
    """
    if not is_rf64(data):
        raise Rf64ParseError("not an RF64/BW64 file (missing 'RF64'/'BW64' magic)")

    end = len(data)
    pos = RIFF_HEADER_SIZE
    if pos + CHUNK_HEADER_SIZE > end or data[pos : pos + 4] != b"ds64":
        raise Rf64ParseError("RF64/BW64 file missing mandatory leading 'ds64' chunk")

    ds64_size = struct.unpack_from("<I", data, pos + 4)[0]
    ds64_payload_start = pos + CHUNK_HEADER_SIZE
    ds64_payload_end = ds64_payload_start + ds64_size
    ds64_raw = data[ds64_payload_start : min(ds64_payload_end, end)]
    table = parse_ds64(ds64_raw)

    pos = ds64_payload_end
    if ds64_size % 2 == 1:
        pos += 1

    chunks: list[RawChunk] = []
    while pos < end:
        if pos + CHUNK_HEADER_SIZE > end:
            logger.warning("truncated chunk header at offset %d — stopping RF64 walk", pos)
            break

        chunk_id = data[pos : pos + 4].decode("ascii", errors="replace")
        declared_size = struct.unpack_from("<I", data, pos + 4)[0]

        if declared_size == RF64_SENTINEL_SIZE:
            resolved = table.chunk_sizes.get(chunk_id)
            if chunk_id == "data" and resolved is None:
                resolved = table.data_size
            if resolved is None:
                logger.warning(
                    "chunk %r at offset %d has sentinel size but no ds64 table entry — "
                    "cannot determine real size, stopping walk",
                    chunk_id,
                    pos,
                )
                break
            declared_size = resolved

        payload_start = pos + CHUNK_HEADER_SIZE
        payload_end = payload_start + declared_size

        if payload_end > end:
            logger.warning(
                "chunk %r at offset %d resolves to size %d but only %d bytes remain — truncating",
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


__all__ = ["Ds64Table", "Rf64ParseError", "is_rf64", "parse_ds64", "walk"]

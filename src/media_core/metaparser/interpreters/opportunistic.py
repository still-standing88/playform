"""Best-effort interpreters for the long tail of chunks: 'cue ', 'labl'/'note'
(inside a LIST 'adtl'), and 'axml' (the ADM/XML chunk from EBU Tech 3285
Supplement 5). Per plan.md, these are low priority to fully parse but high
priority to not crash on — every function here is meant to be called from a
try/except at the call site (or wraps its own internals in one) so a
malformed instance of any of these never takes down the rest of a file's
extraction.
"""

from __future__ import annotations

import logging
import struct

from media_core.metaparser.chunks.riff_walker import walk_sub_chunks
from media_core.metaparser.interpreters._text import decode_lenient

logger = logging.getLogger(__name__)

CUE_POINT_SIZE = 24


class OpportunisticParseError(Exception):
    pass


def parse_cue(raw: bytes) -> list[dict]:
    """'cue ' chunk: cue point count (uint32) + N x 24-byte cue point records.
    Returns [] on any structural problem rather than raising — a busted cue
    chunk shouldn't block the rest of the file's metadata.
    """
    if len(raw) < 4:
        logger.warning("cue chunk too short to hold a count (%d bytes) — skipping", len(raw))
        return []

    try:
        count = struct.unpack_from("<I", raw, 0)[0]
    except struct.error as exc:
        logger.warning("cue chunk count field unreadable: %s — skipping", exc)
        return []

    available = (len(raw) - 4) // CUE_POINT_SIZE
    if count > available:
        logger.warning(
            "cue chunk declares %d points but only %d fit in the payload — reading %d",
            count,
            available,
            available,
        )
        count = available

    points = []
    for i in range(count):
        off = 4 + i * CUE_POINT_SIZE
        try:
            name, position, fcc_chunk, chunk_start, block_start, sample_offset = struct.unpack_from(
                "<II4sIII", raw, off
            )
        except struct.error as exc:
            logger.warning("cue point %d unreadable: %s — stopping", i, exc)
            break
        points.append(
            {
                "name_id": name,
                "position": position,
                "fcc_chunk": fcc_chunk.decode("ascii", errors="replace"),
                "chunk_start": chunk_start,
                "block_start": block_start,
                "sample_offset": sample_offset,
            }
        )
    return points


def parse_adtl(raw: bytes) -> dict[int, dict]:
    """LIST 'adtl' payload: sub-chunks 'labl'/'note' (both: 4-byte name id +
    null-terminated text) associating text with a cue point by name_id, plus
    'ltxt' which we don't decode fully (labeled-text region metadata) but
    still register the name_id for. Returns {name_id: {kind, text}}.
    """
    if len(raw) < 4:
        logger.warning("adtl payload too short to contain a list type — skipping")
        return {}

    list_type = raw[0:4].decode("ascii", errors="replace")
    if list_type != "adtl":
        logger.info("expected adtl list type, got %r — parsing sub-chunks anyway", list_type)

    result: dict[int, dict] = {}
    for chunk in walk_sub_chunks(raw[4:]):
        if chunk.chunk_id not in ("labl", "note", "ltxt"):
            continue
        if len(chunk.raw) < 4:
            logger.warning("%r sub-chunk too short to hold a name id — skipping", chunk.chunk_id)
            continue
        name_id = struct.unpack_from("<I", chunk.raw, 0)[0]
        if chunk.chunk_id in ("labl", "note"):
            text = decode_lenient(chunk.raw[4:].split(b"\x00", 1)[0]).strip()
            result[name_id] = {"kind": chunk.chunk_id, "text": text}
        else:
            # ltxt carries a text region (purpose, country, language, dialect
            # fields before the text) — not decoding the fixed fields, just
            # keeping the trailing text so it's not silently dropped.
            text = decode_lenient(chunk.raw[20:].split(b"\x00", 1)[0]).strip()
            result[name_id] = {"kind": "ltxt", "text": text}

    return result


def parse_axml(raw: bytes) -> str | None:
    """'axml' chunk: an ADM XML payload (EBU Tech 3285 Supplement 5), carried
    by some newer BWF files. Not fully modeled here — just returned as
    decoded text so it's available for storage/inspection without the
    extractor choking on it. A dedicated ADM parser is future scope if a
    real sample corpus shows it's common enough in the SFX libraries this
    targets to be worth building.
    """
    try:
        return raw.decode("utf-8", errors="replace").strip() or None
    except Exception as exc:  # decoding utf-8 with errors='replace' shouldn't raise, but stay defensive
        logger.warning("axml chunk could not even be decoded as text: %s", exc)
        return None

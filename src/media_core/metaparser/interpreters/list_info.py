"""RIFF LIST chunk interpreter, specifically the 'INFO' list type.

A LIST chunk's payload starts with a 4-byte "list type" fourCC, followed by
a flat run of sub-chunks in the same id+size+payload shape as top-level RIFF
chunks. For list type 'INFO', those sub-chunks are well-known fourCCs like
INAM (title), IART (artist), ICMT (comment) — but the RIFF spec allows
vendor-defined fourCCs too. Known codes get mapped to a friendly name for
convenience; anything unrecognized is kept verbatim under its raw fourCC key
rather than being dropped, per plan.md: "nothing gets silently dropped just
because it's not in your table."
"""

from __future__ import annotations

import logging

from media_core.metaparser.chunks.riff_walker import walk_sub_chunks
from media_core.metaparser.interpreters._text import decode_lenient

logger = logging.getLogger(__name__)

# RIFF INFO fourCC -> friendly name. Source: the standard RIFF INFO chunk
# registry (Microsoft/IBM Multimedia Programming Interface spec).
KNOWN_INFO_CODES = {
    "IARL": "archival_location",
    "IART": "artist",
    "ICMS": "commissioned",
    "ICMT": "comment",
    "ICOP": "copyright",
    "ICRD": "creation_date",
    "ICRP": "cropped",
    "IDIM": "dimensions",
    "IDPI": "dots_per_inch",
    "IENG": "engineer",
    "IGNR": "genre",
    "IKEY": "keywords",
    "ILGT": "lightness",
    "IMED": "medium",
    "INAM": "title",
    "IPLT": "num_colors",
    "IPRD": "product",
    "ISBJ": "subject",
    "ISFT": "software",
    "ISHP": "sharpness",
    "ISRC": "source",
    "ISRF": "source_form",
    "ITCH": "technician",
    "ITRK": "track_number",
}


class ListInfoParseError(Exception):
    pass


def is_info_list(list_payload: bytes) -> bool:
    return len(list_payload) >= 4 and list_payload[0:4] == b"INFO"


def parse_info(list_payload: bytes) -> dict[str, str]:
    """Parse a LIST chunk's payload as an INFO list. Caller is responsible
    for having checked `is_info_list` first (or for accepting whatever
    fourCCs show up if it's actually some other list type — this function
    doesn't care, it just walks sub-chunks after the leading 4-byte type id).
    """
    if len(list_payload) < 4:
        raise ListInfoParseError(f"LIST payload too short to contain a list type: {len(list_payload)} bytes")

    list_type = list_payload[0:4].decode("ascii", errors="replace")
    if list_type != "INFO":
        logger.info("LIST payload has type %r, not INFO — parsing sub-chunks anyway", list_type)

    sub_chunks = walk_sub_chunks(list_payload[4:])

    result: dict[str, str] = {}
    for chunk in sub_chunks:
        text = decode_lenient(chunk.raw.split(b"\x00", 1)[0]).strip()
        friendly = KNOWN_INFO_CODES.get(chunk.chunk_id)
        key = friendly if friendly is not None else chunk.chunk_id
        if friendly is None:
            logger.debug("unrecognized INFO fourCC %r — keeping raw key", chunk.chunk_id)
        if key in result:
            logger.warning("duplicate INFO key %r (fourCC %r) — keeping first occurrence", key, chunk.chunk_id)
            continue
        result[key] = text

    return result

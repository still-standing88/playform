"""RealMedia (.rm/.rmvb) interpreter, built on metaparser.chunks.realmedia_walker.

Only two object types carry genuinely descriptive text per the RMFF spec:

- 'CONT' (title/author/copyright/comment) — a fixed positional structure
  (four uint16-length-prefixed strings, in that order). Hardcoded by
  necessity, the same way bext.py's EBU Tech 3285 struct is: it's positional
  binary, not a tag list, so there's nothing to walk generically here.
- 'MDPR' (per-stream properties) — fixed numeric fields followed by two
  uint8-length-prefixed strings (stream_name, mime_type). Also positional.

Every other object type (PROP, DATA, INDX, and anything vendor-specific) is
walked generically and kept under its raw 4-char object_id with its payload
bytes untouched — there's no fixed whitelist of what object types are
"allowed" to appear, matching this project's rule that nothing gets silently
dropped just because it wasn't specifically decoded (see list_info.py).
"""

from __future__ import annotations

import logging
import struct

from media_core.metaparser.chunks import realmedia_walker
from media_core.metaparser.interpreters._text import decode_lenient

logger = logging.getLogger(__name__)

_MDPR_FIXED_FIELDS_SIZE = 30  # 8 fields: 1 uint16 + 7 uint32


class RealMediaInterpretError(Exception):
    pass


def _read_pstring(data: bytes, pos: int, length_size: int) -> tuple[str, int] | None:
    """Reads one length-prefixed string (length_size bytes, big-endian,
    followed by that many bytes of text). Returns (text, bytes_consumed), or
    None if truncated."""
    if pos + length_size > len(data):
        return None
    length = int.from_bytes(data[pos : pos + length_size], "big")
    start = pos + length_size
    if start + length > len(data):
        return None
    return decode_lenient(data[start : start + length]), length_size + length


def parse_cont(payload: bytes) -> dict[str, str]:
    """CONT object: title/author/copyright/comment, each a uint16-length-
    prefixed string, in that fixed order. Stops gracefully (keeping whatever
    fields were readable) on truncation rather than raising — matches the
    "process errors gracefully" rule every interpreter in this package
    follows."""
    fields: dict[str, str] = {}
    pos = 0
    for name in ("title", "author", "copyright", "comment"):
        result = _read_pstring(payload, pos, 2)
        if result is None:
            logger.info("CONT object truncated before field %r — keeping what was read", name)
            break
        text, consumed = result
        if text:
            fields[name] = text
        pos += consumed
    return fields


def parse_mdpr(payload: bytes) -> dict:
    """MDPR (per-stream properties): fixed numeric header fields plus
    stream_name/mime_type (uint8-length-prefixed, unlike CONT's uint16).
    type_specific_data (codec-dependent, follows mime_type) is deliberately
    not decoded here — its shape depends on the codec and isn't something
    this module guesses at."""
    if len(payload) < _MDPR_FIXED_FIELDS_SIZE:
        raise RealMediaInterpretError(f"MDPR payload too short: {len(payload)} bytes")

    (
        stream_number,
        max_bit_rate,
        avg_bit_rate,
        max_packet_size,
        avg_packet_size,
        start_time,
        preroll,
        duration,
    ) = struct.unpack_from(">HIIIIIII", payload, 0)

    fields: dict = {
        "stream_number": stream_number,
        "max_bit_rate": max_bit_rate,
        "avg_bit_rate": avg_bit_rate,
        "max_packet_size": max_packet_size,
        "avg_packet_size": avg_packet_size,
        "start_time": start_time,
        "preroll": preroll,
        "duration": duration,
    }

    pos = _MDPR_FIXED_FIELDS_SIZE
    name_result = _read_pstring(payload, pos, 1)
    if name_result is not None:
        fields["stream_name"], consumed = name_result
        pos += consumed
        mime_result = _read_pstring(payload, pos, 1)
        if mime_result is not None:
            fields["mime_type"], _ = mime_result

    return fields


def parse(data: bytes) -> dict:
    """Walks a whole RealMedia file's top-level objects into
    {object_id: decoded_payload}. CONT/MDPR get their positional fields
    decoded (MDPR entries collect into a list, since a file has one per
    stream); everything else is kept as raw bytes under its 4-char
    object_id, dynamically — no fixed whitelist of what object types may
    appear. A single malformed object is logged and skipped, never fatal to
    the rest of the file.
    """
    objects = realmedia_walker.walk(data)
    result: dict = {}
    mdpr_streams: list[dict] = []

    for obj in objects:
        try:
            if obj.object_id == "CONT":
                result["CONT"] = parse_cont(obj.raw)
            elif obj.object_id == "MDPR":
                mdpr_streams.append(parse_mdpr(obj.raw))
            else:
                result.setdefault(obj.object_id, obj.raw)
        except Exception as exc:
            logger.warning("RealMedia object %r failed to parse: %s", obj.object_id, exc)

    if mdpr_streams:
        result["MDPR"] = mdpr_streams

    return result

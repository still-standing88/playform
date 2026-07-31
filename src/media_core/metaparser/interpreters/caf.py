"""CAF (Core Audio Format) interpreter, built on metaparser.chunks.caf_walker.

'desc' (Audio Description) is a fixed 32-byte positional struct per Apple's
CAF spec — hardcoded by necessity, the same way bext.py's EBU struct is,
since there's no way to walk field names out of bytes that never had any.

'info' (Information) is CAF's own free-form metadata chunk: a count followed
by that many NUL-terminated UTF-8 key/value string pairs, with **no fixed
key list** — Apple's spec documents common keys (title, artist, album,
comments, composer, copyright, genre, tempo, key signature, ...) but any
string is valid, so this is walked generically like iXML/AMF0, not matched
against a whitelist. Every other chunk type ('kuki' magic cookie, 'pakt'
packet table, 'data', 'free', ...) is kept raw under its own fourCC — same
"nothing gets silently dropped" rule the rest of this project follows.
"""

from __future__ import annotations

import logging
import struct

from media_core.metaparser.chunks import caf_walker

logger = logging.getLogger(__name__)

_DESC_SIZE = 32


class CafInterpretError(Exception):
    pass


def parse_desc(payload: bytes) -> dict:
    if len(payload) < _DESC_SIZE:
        raise CafInterpretError(f"desc chunk too short: {len(payload)} bytes (need {_DESC_SIZE})")

    sample_rate = struct.unpack_from(">d", payload, 0)[0]
    format_id = payload[8:12].decode("ascii", errors="replace").strip()
    (format_flags, bytes_per_packet, frames_per_packet, channels_per_frame, bits_per_channel) = struct.unpack_from(
        ">IIIII", payload, 12
    )

    return {
        "sample_rate": sample_rate,
        "format_id": format_id,
        "format_flags": format_flags,
        "bytes_per_packet": bytes_per_packet,
        "frames_per_packet": frames_per_packet,
        "channels_per_frame": channels_per_frame,
        "bits_per_channel": bits_per_channel,
    }


def parse_info(payload: bytes) -> dict[str, str]:
    """Walks the NUL-terminated key/value string pairs. Stops (keeping
    whatever pairs were already read) at the first truncated/unterminated
    string rather than raising — one malformed entry shouldn't lose the
    rest of a file's info chunk."""
    if len(payload) < 4:
        return {}

    num_entries = struct.unpack_from(">I", payload, 0)[0]
    pos = 4
    result: dict[str, str] = {}

    for _ in range(num_entries):
        key_end = payload.find(b"\x00", pos)
        if key_end == -1:
            logger.info("CAF info chunk: unterminated key string at offset %d — stopping", pos)
            break
        key = payload[pos:key_end].decode("utf-8", errors="replace")
        pos = key_end + 1

        value_end = payload.find(b"\x00", pos)
        if value_end == -1:
            logger.info("CAF info chunk: unterminated value string for key %r — stopping", key)
            break
        value = payload[pos:value_end].decode("utf-8", errors="replace")
        pos = value_end + 1

        result[key] = value

    return result


def parse(data: bytes) -> dict:
    result: dict = {}
    for chunk in caf_walker.walk(data):
        try:
            if chunk.chunk_type == "desc":
                result["desc"] = parse_desc(chunk.raw)
            elif chunk.chunk_type == "info":
                result["info"] = parse_info(chunk.raw)
            else:
                result.setdefault(chunk.chunk_type, chunk.raw)
        except CafInterpretError as exc:
            logger.warning("CAF chunk %r failed to parse: %s", chunk.chunk_type, exc)

    return result

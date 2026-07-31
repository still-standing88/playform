"""AMF0 (Action Message Format 0) decoder — the key/value encoding Flash
uses for its "script data" tags (onMetaData and friends). Public spec
reference: Adobe's "AMF0 File Format Specification" (also cited by
archive/exiftool's Flash.pm — see ../../CREDITS.md).

This is the clearest case in this package for "dynamic, not a fixed field
list": an AMF0 object or ECMA array is an arbitrary, open-ended set of
key/value pairs chosen by whatever encoder wrote the file — there's no fixed
schema to hardcode against, so this decoder is a pure type-marker dispatch
that returns whatever structure was actually encoded, however deep or shaped
it turns out to be. Truncated or unrecognized data stops decoding at that
point rather than raising — callers get back whatever decoded cleanly.
"""

from __future__ import annotations

import struct

from metaparser.interpreters._text import decode_lenient

MARKER_NUMBER = 0x00
MARKER_BOOLEAN = 0x01
MARKER_STRING = 0x02
MARKER_OBJECT = 0x03
MARKER_NULL = 0x05
MARKER_UNDEFINED = 0x06
MARKER_ECMA_ARRAY = 0x08
MARKER_OBJECT_END = 0x09
MARKER_STRICT_ARRAY = 0x0A
MARKER_DATE = 0x0B
MARKER_LONG_STRING = 0x0C

_OBJECT_END_MARKER = b"\x00\x00\x09"


class Amf0DecodeError(Exception):
    pass


def _decode_string(data: bytes, pos: int, length_size: int = 2) -> tuple[str, int]:
    if pos + length_size > len(data):
        raise Amf0DecodeError(f"truncated AMF0 string length at offset {pos}")
    length = int.from_bytes(data[pos : pos + length_size], "big")
    start = pos + length_size
    if start + length > len(data):
        raise Amf0DecodeError(f"truncated AMF0 string data at offset {start} (declared length {length})")
    return decode_lenient(data[start : start + length]), start + length


def _decode_object_properties(data: bytes, pos: int) -> tuple[dict, int]:
    """Reads key/value pairs (string key, AMF0 value) until the 3-byte
    end-of-object marker. Shared by MARKER_OBJECT and MARKER_ECMA_ARRAY,
    since both are shaped identically on the wire past their own leading
    marker/count."""
    obj: dict = {}
    while True:
        if data[pos : pos + 3] == _OBJECT_END_MARKER:
            return obj, pos + 3
        key, pos = _decode_string(data, pos)
        value, pos = _decode_value(data, pos)
        obj[key] = value


def _decode_value(data: bytes, pos: int) -> tuple[object, int]:
    if pos >= len(data):
        raise Amf0DecodeError(f"truncated AMF0 value at offset {pos}")
    marker = data[pos]
    pos += 1

    if marker == MARKER_NUMBER:
        if pos + 8 > len(data):
            raise Amf0DecodeError(f"truncated AMF0 number at offset {pos}")
        return struct.unpack_from(">d", data, pos)[0], pos + 8

    if marker == MARKER_BOOLEAN:
        if pos + 1 > len(data):
            raise Amf0DecodeError(f"truncated AMF0 boolean at offset {pos}")
        return bool(data[pos]), pos + 1

    if marker == MARKER_STRING:
        return _decode_string(data, pos)

    if marker == MARKER_LONG_STRING:
        return _decode_string(data, pos, length_size=4)

    if marker == MARKER_OBJECT:
        return _decode_object_properties(data, pos)

    if marker == MARKER_ECMA_ARRAY:
        if pos + 4 > len(data):
            raise Amf0DecodeError(f"truncated AMF0 ECMA array count at offset {pos}")
        # The associative-array element count is a hint some encoders get
        # wrong — read until the actual end-of-object marker instead of
        # trusting it, same "don't trust declared sizes over what's there"
        # discipline the chunk walkers use.
        pos += 4
        return _decode_object_properties(data, pos)

    if marker == MARKER_STRICT_ARRAY:
        if pos + 4 > len(data):
            raise Amf0DecodeError(f"truncated AMF0 strict array count at offset {pos}")
        count = struct.unpack_from(">I", data, pos)[0]
        pos += 4
        items = []
        for _ in range(count):
            value, pos = _decode_value(data, pos)
            items.append(value)
        return items, pos

    if marker == MARKER_DATE:
        if pos + 10 > len(data):
            raise Amf0DecodeError(f"truncated AMF0 date at offset {pos}")
        millis_since_epoch = struct.unpack_from(">d", data, pos)[0]
        # The trailing 2-byte timezone field is legacy and always 0 per spec
        # — consumed but not surfaced separately.
        return millis_since_epoch, pos + 10

    if marker in (MARKER_NULL, MARKER_UNDEFINED):
        return None, pos

    raise Amf0DecodeError(f"unsupported or unrecognized AMF0 type marker 0x{marker:02X} at offset {pos - 1}")


def decode_all(data: bytes) -> list:
    """Decodes a flat sequence of AMF0 values from a script-data tag payload
    (conventionally two values: a string name like 'onMetaData', then one
    object/ECMA-array of properties, though this doesn't assume that shape).
    Stops and returns whatever decoded successfully so far if a later value
    is malformed or truncated — one bad trailing value shouldn't lose
    everything already decoded.
    """
    values = []
    pos = 0
    while pos < len(data):
        try:
            value, pos = _decode_value(data, pos)
        except Amf0DecodeError:
            break
        values.append(value)
    return values

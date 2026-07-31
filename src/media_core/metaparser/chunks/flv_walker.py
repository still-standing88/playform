"""FLV (Flash Video) tag-stream walker — .flv/.f4v.

Structurally different from every other container this package walks: not
chunk/element-nested, but a flat sequence of (type, size, timestamp, data)
tags following a 9-byte file header, each followed by a 4-byte "previous tag
size" trailer the spec uses for backward seeking (skipped over here, never
trusted over a tag's own declared data_size). Public spec reference: Adobe's
"Video File Format Specification" (also cited by archive/exiftool's
Flash.pm — see ../../CREDITS.md).

No interpretation of tag contents happens here — that's flash_video.py's
job, particularly for the AMF0-encoded "script data" tag (type 18) that
carries onMetaData. Same contract as every other walker in this package:
log-and-skip on anything malformed or truncated, never raise past the
initial magic check.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass

logger = logging.getLogger(__name__)

FILE_HEADER_SIZE = 9
TAG_HEADER_SIZE = 11
FILE_MAGIC = b"FLV"

TAG_TYPE_AUDIO = 8
TAG_TYPE_VIDEO = 9
TAG_TYPE_SCRIPT_DATA = 18


@dataclass(frozen=True)
class RawTag:
    tag_type: int
    timestamp_ms: int
    offset: int
    """Byte offset of the tag payload, past the 11-byte tag header."""
    raw: bytes
    size_declared: int


class FlvParseError(Exception):
    pass


def is_flv(data: bytes) -> bool:
    return len(data) >= FILE_HEADER_SIZE and data[0:3] == FILE_MAGIC


def walk(data: bytes) -> list[RawTag]:
    if not is_flv(data):
        raise FlvParseError("not an FLV file (missing 'FLV' magic)")

    data_offset = struct.unpack_from(">I", data, 5)[0]
    if not (FILE_HEADER_SIZE <= data_offset <= len(data)):
        logger.warning(
            "FLV header declares data_offset=%d, outside a sane range for a %d-byte file — "
            "falling back to the standard 9-byte header size",
            data_offset,
            len(data),
        )
        data_offset = FILE_HEADER_SIZE

    tags: list[RawTag] = []
    pos = data_offset + 4  # skip the header + the always-zero PreviousTagSize0
    end = len(data)

    while pos < end:
        if pos + TAG_HEADER_SIZE > end:
            logger.warning(
                "truncated FLV tag header at offset %d (%d bytes left) — stopping walk",
                pos,
                end - pos,
            )
            break

        tag_type = data[pos]
        data_size = int.from_bytes(data[pos + 1 : pos + 4], "big")
        timestamp_lower = int.from_bytes(data[pos + 4 : pos + 7], "big")
        timestamp_ext = data[pos + 7]
        timestamp_ms = (timestamp_ext << 24) | timestamp_lower

        payload_start = pos + TAG_HEADER_SIZE
        payload_end = payload_start + data_size

        if payload_end > end:
            logger.warning(
                "FLV tag type %d at offset %d declares data_size=%d but only %d bytes remain — truncating",
                tag_type,
                pos,
                data_size,
                end - payload_start,
            )
            tags.append(
                RawTag(
                    tag_type=tag_type,
                    timestamp_ms=timestamp_ms,
                    offset=payload_start,
                    raw=data[payload_start:end],
                    size_declared=data_size,
                )
            )
            break

        tags.append(
            RawTag(
                tag_type=tag_type,
                timestamp_ms=timestamp_ms,
                offset=payload_start,
                raw=data[payload_start:payload_end],
                size_declared=data_size,
            )
        )
        pos = payload_end + 4  # skip the trailing PreviousTagSize field

    return tags

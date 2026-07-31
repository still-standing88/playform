"""RealMedia (.rm/.rmvb) object walker — the RMFF (RealMedia File Format)
container.

Structurally similar to RIFF (id + size + payload) but with two differences
that make it not reusable as-is: each object's size field covers the object's
own header too (not just its payload, as RIFF's does), and the header carries
an extra 2-byte object_version before any version-specific payload. Public
spec reference: the RMFF description at
https://common.helixcommunity.org/nonav/2003/HCS_SDK_r5/htmfiles/rmff.htm
(the same reference archive/exiftool's Real.pm module cites — see
../../CREDITS.md for how that source was used).

Same contract as every other walker in this package: no interpretation of
payload contents, log-and-skip on anything malformed or truncated, never
raise past the initial magic check.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass

logger = logging.getLogger(__name__)

OBJECT_HEADER_SIZE = 10  # id(4) + size(4) + version(2)
FILE_MAGIC = b".RMF"


@dataclass(frozen=True)
class RawObject:
    object_id: str
    object_version: int
    offset: int
    """Byte offset of the object payload, past the 10-byte header."""
    raw: bytes
    size_declared: int
    """Total object size as declared in the header, INCLUDING the 10-byte
    header itself — RMFF's own convention, unlike RIFF/IFF/EBML."""


class RealMediaParseError(Exception):
    pass


def is_realmedia(data: bytes) -> bool:
    return len(data) >= OBJECT_HEADER_SIZE and data[0:4] == FILE_MAGIC


def walk(data: bytes) -> list[RawObject]:
    if not is_realmedia(data):
        raise RealMediaParseError("not a RealMedia file (missing '.RMF' magic)")

    objects: list[RawObject] = []
    pos = 0
    end = len(data)

    while pos < end:
        if pos + OBJECT_HEADER_SIZE > end:
            logger.warning(
                "truncated RealMedia object header at offset %d (%d bytes left) — stopping walk",
                pos,
                end - pos,
            )
            break

        object_id = data[pos : pos + 4].decode("ascii", errors="replace")
        declared_size, object_version = struct.unpack_from(">IH", data, pos + 4)

        if declared_size < OBJECT_HEADER_SIZE:
            logger.warning(
                "RealMedia object %r at offset %d declares size %d, smaller than its own "
                "10-byte header — stopping walk (can't trust further offsets)",
                object_id,
                pos,
                declared_size,
            )
            break

        payload_start = pos + OBJECT_HEADER_SIZE
        payload_end = pos + declared_size

        if payload_end > end:
            logger.warning(
                "RealMedia object %r at offset %d declares total size %d but only %d bytes "
                "remain — truncating",
                object_id,
                pos,
                declared_size,
                end - pos,
            )
            objects.append(
                RawObject(
                    object_id=object_id,
                    object_version=object_version,
                    offset=payload_start,
                    raw=data[payload_start:end],
                    size_declared=declared_size,
                )
            )
            break

        objects.append(
            RawObject(
                object_id=object_id,
                object_version=object_version,
                offset=payload_start,
                raw=data[payload_start:payload_end],
                size_declared=declared_size,
            )
        )
        pos = payload_end

    return objects

"""EBML (Extensible Binary Meta Language) element walker — the container
format Matroska (MKV/MKA) and WebM are built on.

Unlike RIFF/IFF, EBML has no fixed-width header: both the element ID and the
size are self-describing variable-length integers (the number of leading
zero-bits in the first byte encodes how many bytes follow). This walker does
zero interpretation of what an element *means* — same contract as
riff_walker/iff_walker: yield (element_id, offset, raw_bytes) tuples, log and
truncate on anything malformed, never raise past the initial magic check.

A file is just a flat top-level sequence of EBML elements (typically one
'EBML' header element followed by one 'Segment' element that contains
everything else) — there's no separate RIFF-style outer size header to
validate against. Nesting is the caller's job: walk() operates on whatever
flat byte range it's given, so an interpreter recurses into a master
element's own `raw` payload by calling walk() again on it, exactly like
riff_walker.walk_sub_chunks is reused for LIST sub-chunks.

Element IDs are kept as their full wire-format integer, marker bit included
(e.g. the EBML header element is 0x1A45DFA3) — the standard convention used
by every EBML/Matroska implementation, per the public specification at
https://www.matroska.org/technical/specs/index.html (referenced directly,
not from any single tool's source).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

EBML_HEADER_ID = 0x1A45DFA3


@dataclass(frozen=True)
class RawElement:
    element_id: int
    offset: int
    """Byte offset of the element payload, relative to the start of `data`
    passed to walk() — not necessarily the whole file, since walk() is also
    used to recurse into a master element's own payload."""
    raw: bytes
    size_declared: int
    size_unknown: bool
    """True if the size vint's data bits were all 1 (EBML's "unknown size"
    marker, legal for the outermost Segment in live-streamed captures). When
    True, `raw` runs to the end of whatever byte range was given to walk(),
    not to a spec-verified boundary — there's no way to know the real one
    without scanning for the next valid sibling ID, which this walker
    deliberately doesn't attempt (never let one weird file hang a scan)."""


class EbmlParseError(Exception):
    pass


def _read_vint(data: bytes, pos: int, keep_marker: bool) -> tuple[int, int] | None:
    """Reads one EBML variable-length integer starting at `pos`. Returns
    (value, byte_length) or None if truncated/invalid. Element IDs keep their
    marker bit (keep_marker=True); sizes have it stripped per spec.
    """
    if pos >= len(data):
        return None
    first = data[pos]
    if first == 0:
        # Reserved/invalid leading byte (would imply a vint longer than the
        # 8 bytes EBML supports) — not a valid vint start.
        return None

    length = 1
    mask = 0x80
    while not (first & mask):
        mask >>= 1
        length += 1
        if length > 8:
            return None

    if pos + length > len(data):
        return None

    raw_int = int.from_bytes(data[pos : pos + length], "big")
    if keep_marker:
        return raw_int, length

    marker_bit = mask << ((length - 1) * 8)
    return raw_int & ~marker_bit, length


def _is_unknown_size(value: int, length: int) -> bool:
    """EBML's "unknown size" sentinel: every data bit of the size vint set to 1."""
    return value == (1 << (7 * length)) - 1


def is_ebml(data: bytes) -> bool:
    parsed = _read_vint(data, 0, keep_marker=True)
    return parsed is not None and parsed[0] == EBML_HEADER_ID


def walk(data: bytes) -> list[RawElement]:
    """Walk a flat sequence of sibling EBML elements. Used both for the
    top-level file and, recursively, for any master element's own payload —
    see module docstring.
    """
    elements: list[RawElement] = []
    pos = 0
    end = len(data)

    while pos < end:
        id_parsed = _read_vint(data, pos, keep_marker=True)
        if id_parsed is None:
            logger.warning(
                "truncated or invalid EBML element ID at offset %d (%d bytes left) — stopping walk",
                pos,
                end - pos,
            )
            break
        element_id, id_len = id_parsed

        size_pos = pos + id_len
        size_parsed = _read_vint(data, size_pos, keep_marker=False)
        if size_parsed is None:
            logger.warning(
                "truncated or invalid EBML size vint at offset %d for element 0x%X — stopping walk",
                size_pos,
                element_id,
            )
            break
        declared_size, size_len = size_parsed

        payload_start = size_pos + size_len
        unknown = _is_unknown_size(declared_size, size_len)

        if unknown:
            logger.info(
                "element 0x%X at offset %d has unknown size (EBML live-stream sentinel) — "
                "consuming to end of this byte range and stopping walk",
                element_id,
                pos,
            )
            elements.append(
                RawElement(
                    element_id=element_id,
                    offset=payload_start,
                    raw=data[payload_start:end],
                    size_declared=declared_size,
                    size_unknown=True,
                )
            )
            break

        payload_end = payload_start + declared_size
        if payload_end > end:
            logger.warning(
                "element 0x%X at offset %d declares size %d but only %d bytes remain — truncating",
                element_id,
                pos,
                declared_size,
                end - payload_start,
            )
            elements.append(
                RawElement(
                    element_id=element_id,
                    offset=payload_start,
                    raw=data[payload_start:end],
                    size_declared=declared_size,
                    size_unknown=False,
                )
            )
            break

        elements.append(
            RawElement(
                element_id=element_id,
                offset=payload_start,
                raw=data[payload_start:payload_end],
                size_declared=declared_size,
                size_unknown=False,
            )
        )
        pos = payload_end

    return elements

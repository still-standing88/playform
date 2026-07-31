"""Legacy QuickTime 'udta' (user data) interpreter, built on
metaparser.chunks.mp4_walker.

mutagen's MP4 reader only understands the modern iTunes-style metadata path
(moov/udta/meta/ilst, atoms like '\\xa9nam' holding a nested 'data' box) —
confirmed via video_tags.py's own docstring against a real ffmpeg-generated
.mov file: pre-iTunes QuickTime files can carry the *same* user-data fourCCs
directly under 'udta' using the older QTFF "text item" atom shape (a plain
uint16 text-length + uint16 language-code prefix, then the text itself, no
'data' box wrapper) — and mutagen's ilst-only reader doesn't parse that
older shape at all, so such files come back from mutagen with no tags even
though the data is genuinely present in the file. This module exists to
close that specific gap, run as a supplementary source alongside mutagen's
own MP4 reading, not a replacement for it.

Every 'udta' child is walked dynamically — no fixed whitelist of which
fourCCs are "allowed": whatever decodes as a plausible legacy text atom is
decoded, everything else (including newer 'meta' sub-boxes mutagen already
handles) is kept raw under its own fourCC rather than dropped, same rule
every other interpreter in this package follows.
"""

from __future__ import annotations

import struct

from metaparser.chunks import mp4_walker
from metaparser.interpreters._text import decode_lenient


def _try_decode_legacy_text_atom(raw: bytes) -> str | None:
    """Attempts the classic QTFF user-data text atom shape: uint16 BE text
    length, uint16 BE Macintosh language code, then that many bytes of text.
    Returns None (not a raise) if the bytes don't fit that shape — callers
    fall back to keeping the box raw.
    """
    if len(raw) < 4:
        return None
    text_length = struct.unpack_from(">H", raw, 0)[0]
    if text_length == 0 or 4 + text_length > len(raw):
        return None
    return decode_lenient(raw[4 : 4 + text_length]).strip()


def parse_udta(udta_payload: bytes) -> dict:
    result: dict = {}
    for box in mp4_walker.walk(udta_payload):
        text = _try_decode_legacy_text_atom(box.raw)
        value = text if text else box.raw
        if box.box_type in result:
            existing = result[box.box_type]
            if isinstance(existing, list):
                existing.append(value)
            else:
                result[box.box_type] = [existing, value]
        else:
            result[box.box_type] = value
    return result


def parse(data: bytes) -> dict:
    """Returns whatever moov/udta held, decoded where it matched the legacy
    text-atom shape, raw otherwise. Empty dict if the file has no
    moov/udta path at all (common for files that only use the modern
    ilst path, which mutagen already covers)."""
    udta_payload = mp4_walker.find_path(data, "moov", "udta")
    if udta_payload is None:
        return {}
    return parse_udta(udta_payload)

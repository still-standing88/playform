"""DTS Coherent Acoustics core-stream sync locator — .dts.

Raw .dts files are just a sequence of frames with no container at all —
similar in spirit to raw MPEG-PS/ES, but a different codec's own bit
layout. This module only finds the first valid frame sync word; bitfield
decode of what follows it is metaparser.interpreters.dts's job.

Confidence note (see ../../CREDITS.md for the fuller version): DTS's core
frame header comes from ETSI TS 102 114, a standard this project doesn't
hold a copy of, and no ExifTool module exists for this format to cross-check
against either — unlike literally every other format in this project. The
sync word itself (0x7FFE8001, the standard 16-bit-word big-endian raw core
sync) is about as universally and consistently documented as a DTS fact
gets, so this project's confidence in it is high; that confidence doesn't
automatically extend to every bitfield past it, which is why the interpreter
scopes what it decodes deliberately narrowly.
"""

from __future__ import annotations

SYNC_WORD = b"\x7f\xfe\x80\x01"


class DtsParseError(Exception):
    pass


def find_sync(data: bytes) -> int | None:
    idx = data.find(SYNC_WORD)
    return idx if idx != -1 else None


def is_dts(data: bytes) -> bool:
    return find_sync(data) is not None

"""MPEG-1/2 audio and video frame-sync scanner — .mpg/.mpeg/.m2v.

Unlike every other walker in this package, raw MPEG-PS/ES has no chunk or
element framing to walk generically — technical metadata lives entirely in
the bitfields of the first valid audio frame header and/or video sequence
header found in the stream, wherever they happen to start. This module's job
is purely to *find* those two structures via frame-sync validation (per
ISO/IEC 11172-3 and 13818-2); metaparser.interpreters.mpeg decodes what's in
them. ISO charges for the official spec, so — same as archive/exiftool's
MPEG.pm, whose own header notes this — this is built against the same
widely-used unofficial references (mp3-tech.org, getid3.org); see
../../CREDITS.md.
"""

from __future__ import annotations

import struct

VIDEO_SEQUENCE_HEADER_START_CODE = b"\x00\x00\x01\xb3"


def find_video_sequence_header(data: bytes) -> bytes | None:
    """Returns the 8 bytes immediately following the first MPEG video
    sequence header start code (0x000001B3), or None if not found or
    truncated. Those 8 bytes hold width/height/aspect-ratio/frame-rate/
    bitrate as packed bitfields, decoded by metaparser.interpreters.mpeg.
    """
    idx = data.find(VIDEO_SEQUENCE_HEADER_START_CODE)
    if idx == -1:
        return None
    start = idx + len(VIDEO_SEQUENCE_HEADER_START_CODE)
    if start + 8 > len(data):
        return None
    return data[start : start + 8]


def _is_valid_audio_frame_sync(word: int) -> bool:
    # An 11-bit sync (0xFFE) alone is a weak signal on its own (roughly
    # 1-in-2048 odds on random bytes), so also reject the bit combinations
    # the spec marks reserved/invalid — same validation ExifTool's
    # ParseMPEGAudio applies before trusting a match.
    if (word & 0xFFE00000) != 0xFFE00000:
        return False
    if (word & 0x00180000) == 0x00080000:  # version '01' is reserved
        return False
    if (word & 0x00060000) == 0x00000000:  # layer '00' is reserved
        return False
    if (word & 0x0000F000) == 0x0000F000:  # bitrate index 1111 is invalid
        return False
    if (word & 0x00000C00) == 0x00000C00:  # sample rate '11' is reserved
        return False
    if (word & 0x00000003) == 0x00000002:  # emphasis '10' is reserved
        return False
    return True


def find_audio_frame_sync(data: bytes) -> tuple[int, int] | None:
    """Scans for the first valid MPEG audio frame header, returning
    (header_word, offset). offset is where the 4-byte header word starts, so
    a caller can look past it (e.g. for a Xing/LAME VBR header). Returns
    None if no valid sync was found anywhere in `data`.
    """
    pos = 0
    limit = len(data) - 4
    while pos <= limit:
        candidate = data.find(b"\xff", pos, limit + 1)
        if candidate == -1:
            return None
        word = struct.unpack_from(">I", data, candidate)[0]
        if _is_valid_audio_frame_sync(word):
            return word, candidate
        pos = candidate + 1
    return None

"""DTS Coherent Acoustics core frame-header interpreter, built on
metaparser.chunks.dts_walker.

Scope is deliberately narrower than this project's other bitfield decoders
(MPEG audio/video, M2TS): only the fields up to and including LFF/HFLAG are
decoded — the fields that would follow an optional 16-bit CRC (FILTS,
VERNUM, CHIST, PCMR, SUMF, SUMS, DIALNORM) are not, and the 5-bit bitrate
index is reported raw rather than mapped to kbps. Confidence in the exact
bit positions and values that far into the header, and in reproducing a
~30-entry rate table correctly from memory, isn't high enough for this
project to present as fact (see dts_walker.py's docstring and
../../CREDITS.md — no ExifTool module or bundled spec exists to cross-check
against, unlike every other format here). What IS decoded — frame type,
block count, frame byte size, channel arrangement, sample rate — is exactly
what this project's indexing/search use case needs (duration estimate,
channel count, sample rate); the skipped fields wouldn't add indexing value
even if decoded with full confidence.
"""

from __future__ import annotations

from metaparser.chunks import dts_walker

_SYNC_BITS = 32

# Channel arrangement (AMODE, 6 bits). Codes 0-9 are the commonly-documented
# base configurations; codes 10-15 add extended surround/subwoofer channels
# with layouts this project isn't confident enough to name precisely, so
# they're reported by raw code instead of guessed at.
_CHANNEL_ARRANGEMENTS = {
    0: "A (mono)",
    1: "A+B (dual mono)",
    2: "L+R (stereo)",
    3: "(L+R)+(L-R) (sum-difference stereo)",
    4: "LT+RT (matrixed surround stereo)",
    5: "C+L+R",
    6: "L+R+S",
    7: "C+L+R+S",
    8: "L+R+SL+SR",
    9: "C+L+R+SL+SR",
}

# Sample rate (SFREQ, 4 bits). Indices not listed are reserved/invalid.
_SAMPLE_RATES = {
    1: 8000, 2: 16000, 3: 32000,
    6: 11025, 7: 22050, 8: 44100,
    11: 12000, 12: 24000, 13: 48000,
}


class DtsInterpretError(Exception):
    pass


class _BitReader:
    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    def read(self, n: int) -> int:
        if self._pos + n > len(self._data) * 8:
            raise DtsInterpretError(f"DTS header truncated: need {n} more bits at bit offset {self._pos}")
        value = 0
        for _ in range(n):
            byte_index = self._pos // 8
            bit_index = 7 - (self._pos % 8)
            value = (value << 1) | ((self._data[byte_index] >> bit_index) & 1)
            self._pos += 1
        return value


def parse_header(data: bytes) -> dict:
    """Decodes a DTS core frame header; `data` must start at the sync word
    (dts_walker.find_sync gives the offset to slice from). Raises
    DtsInterpretError only if truncated before the fields this module
    decodes; every field is returned even when its raw code isn't in this
    module's intentionally partial lookup tables.
    """
    reader = _BitReader(data)
    reader.read(_SYNC_BITS)  # sync word, already validated by the caller

    frame_type = reader.read(1)
    reader.read(5)  # SHORT (deficit sample count) — not surfaced, rarely useful
    crc_present = bool(reader.read(1))
    nblks = reader.read(7)
    fsize = reader.read(14)
    amode = reader.read(6)
    sfreq = reader.read(4)
    rate_index = reader.read(5)
    reader.read(1)  # FixedBit/MIX — not surfaced
    dynamic_range_present = bool(reader.read(1))
    timestamp_present = bool(reader.read(1))
    auxiliary_data_present = bool(reader.read(1))
    hdcd = bool(reader.read(1))
    reader.read(3)  # EXT_AUDIO_ID — not surfaced
    reader.read(1)  # EXT_AUDIO — not surfaced
    extended_sync_present = bool(reader.read(1))
    low_frequency_effects = reader.read(2)
    reader.read(1)  # HFLAG — not surfaced

    blocks = nblks + 1
    frame_size_bytes = fsize + 1
    sample_rate = _SAMPLE_RATES.get(sfreq)

    fields: dict = {
        "frame_type": "normal" if frame_type else "termination",
        "crc_present": crc_present,
        "blocks_per_channel": blocks,
        "frame_size_bytes": frame_size_bytes,
        "channel_arrangement": _CHANNEL_ARRANGEMENTS.get(amode, f"extended multichannel (code {amode})"),
        "sample_rate": sample_rate,
        "bit_rate_index": rate_index,  # deliberately not mapped to kbps — see module docstring
        "dynamic_range_present": dynamic_range_present,
        "timestamp_present": timestamp_present,
        "auxiliary_data_present": auxiliary_data_present,
        "hdcd": hdcd,
        "extended_sync_present": extended_sync_present,
        "low_frequency_effects": low_frequency_effects,
    }

    if sample_rate:
        fields["duration_secs_this_frame"] = (blocks * 32) / sample_rate

    return fields


def parse(data: bytes) -> dict:
    offset = dts_walker.find_sync(data)
    if offset is None:
        raise DtsInterpretError("no DTS sync word found")
    return parse_header(data[offset:])

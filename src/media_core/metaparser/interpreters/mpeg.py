"""MPEG-1/2 audio and video frame-header interpreter, built on
metaparser.chunks.mpeg_walker.

Raw MPEG-PS/ES carries no descriptive tags at all — everything here is
technical stream parameters (bitrate, sample rate, resolution, aspect ratio,
frame rate) packed as bitfields in the first audio frame header and/or video
sequence header found in the stream. The lookup tables below (bitrate index
tables, sample-rate tables, aspect-ratio enum, frame-rate enum) are genuine
ISO/IEC 11172-3 (MPEG-1) and 13818-2 (MPEG-2) spec constants — every MPEG
decoder needs the identical values, they aren't a convenience layer over
arbitrary tag IDs the way a fourCC-name table is. Cross-checked against
archive/exiftool's MPEG.pm (same unofficial references it cites, since ISO
charges for the official spec) — see ../../CREDITS.md. Not ported: MPEG.pm's
exotic non-LAME encoder-signature heuristics (RCA mp3PRO, Thomson mp3PRO,
Gogo) — narrow legacy-encoder identification with little value here.
"""

from __future__ import annotations

import struct

from media_core.metaparser.chunks import mpeg_walker


def _extract_bits(word: int, first_bit: int, last_bit: int) -> int:
    """Extracts bits [first_bit, last_bit] (inclusive, 0-indexed from the
    MSB) out of a 32-bit word."""
    width = last_bit - first_bit + 1
    shift = 31 - last_bit
    mask = (1 << width) - 1
    return (word >> shift) & mask


_VERSION_LABELS = {0: 2.5, 2: 2, 3: 1}
_LAYER_LABELS = {1: 3, 2: 2, 3: 1}

# Bitrate index -> bps, one table per (version, layer) combination — ISO
# 11172-3 Table 3-B.2/3.
_BITRATE_V1_L1 = {0: "free", 1: 32000, 2: 64000, 3: 96000, 4: 128000, 5: 160000, 6: 192000,
                  7: 224000, 8: 256000, 9: 288000, 10: 320000, 11: 352000, 12: 384000,
                  13: 416000, 14: 448000}
_BITRATE_V1_L2 = {0: "free", 1: 32000, 2: 48000, 3: 56000, 4: 64000, 5: 80000, 6: 96000,
                  7: 112000, 8: 128000, 9: 160000, 10: 192000, 11: 224000, 12: 256000,
                  13: 320000, 14: 384000}
_BITRATE_V1_L3 = {0: "free", 1: 32000, 2: 40000, 3: 48000, 4: 56000, 5: 64000, 6: 80000,
                  7: 96000, 8: 112000, 9: 128000, 10: 160000, 11: 192000, 12: 224000,
                  13: 256000, 14: 320000}
_BITRATE_V2_L1 = {0: "free", 1: 32000, 2: 48000, 3: 56000, 4: 64000, 5: 80000, 6: 96000,
                  7: 112000, 8: 128000, 9: 144000, 10: 160000, 11: 176000, 12: 192000,
                  13: 224000, 14: 256000}
_BITRATE_V2_L23 = {0: "free", 1: 8000, 2: 16000, 3: 24000, 4: 32000, 5: 40000, 6: 48000,
                   7: 56000, 8: 64000, 9: 80000, 10: 96000, 11: 112000, 12: 128000,
                   13: 144000, 14: 160000}

_SAMPLE_RATE_TABLES = {
    3: {0: 44100, 1: 48000, 2: 32000},  # version 1
    2: {0: 22050, 1: 24000, 2: 16000},  # version 2
    0: {0: 11025, 1: 12000, 2: 8000},  # version 2.5
}

_CHANNEL_MODE = {0: "Stereo", 1: "Joint Stereo", 2: "Dual Channel", 3: "Single Channel"}
_MODE_EXTENSION = {0: "Bands 4-31", 1: "Bands 8-31", 2: "Bands 12-31", 3: "Bands 16-31"}
_EMPHASIS = {0: "None", 1: "50/15 ms", 2: "reserved", 3: "CCIT J.17"}

_ASPECT_RATIO = {
    1: "1:1", 2: "0.6735", 3: "16:9, 625 line, PAL", 4: "0.7615", 5: "0.8055",
    6: "16:9, 525 line, NTSC", 7: "0.8935", 8: "4:3, 625 line, PAL, CCIR601",
    9: "0.9815", 10: "1.0255", 11: "1.0695", 12: "4:3, 525 line, NTSC, CCIR601",
    13: "1.1575", 14: "1.2015",
}
_FRAME_RATE = {1: 23.976, 2: 24, 3: 25, 4: 29.97, 5: 30, 6: 50, 7: 59.94, 8: 60}

_LAME_METHOD = {1: "CBR", 2: "ABR", 3: "VBR (old/rh)", 4: "VBR (new/mtrh)",
                5: "VBR (old/rh)", 6: "VBR", 8: "CBR (2-pass)", 9: "ABR (2-pass)"}
_LAME_STEREO_MODE = {0: "Mono", 1: "Stereo", 2: "Dual Channels", 3: "Joint Stereo",
                      4: "Forced Joint Stereo", 6: "Auto", 7: "Intensity Stereo"}


def parse_audio_header(word: int) -> dict:
    """Decodes a validated 32-bit MPEG audio frame header word (see
    mpeg_walker.find_audio_frame_sync) into its technical fields."""
    version_raw = _extract_bits(word, 11, 12)
    layer_raw = _extract_bits(word, 13, 14)
    bitrate_index = _extract_bits(word, 16, 19)
    sample_rate_index = _extract_bits(word, 20, 21)
    channel_mode_raw = _extract_bits(word, 24, 25)

    fields: dict = {
        "mpeg_audio_version": _VERSION_LABELS.get(version_raw),
        "audio_layer": _LAYER_LABELS.get(layer_raw),
        "channel_mode": _CHANNEL_MODE.get(channel_mode_raw),
        "copyright_flag": bool(_extract_bits(word, 28, 28)),
        "original_media": bool(_extract_bits(word, 29, 29)),
        "emphasis": _EMPHASIS.get(_extract_bits(word, 30, 31)),
    }

    if version_raw == 3:
        bitrate_table = {3: _BITRATE_V1_L1, 2: _BITRATE_V1_L2, 1: _BITRATE_V1_L3}.get(layer_raw)
    elif layer_raw == 3:
        bitrate_table = _BITRATE_V2_L1
    elif layer_raw in (1, 2):
        bitrate_table = _BITRATE_V2_L23
    else:
        bitrate_table = None
    if bitrate_table is not None:
        fields["audio_bitrate"] = bitrate_table.get(bitrate_index)

    sample_rate_table = _SAMPLE_RATE_TABLES.get(version_raw)
    if sample_rate_table is not None:
        fields["sample_rate"] = sample_rate_table.get(sample_rate_index)

    if layer_raw == 1:  # Layer III
        fields["ms_stereo"] = bool(_extract_bits(word, 26, 26))
        fields["intensity_stereo"] = bool(_extract_bits(word, 27, 27))
    elif layer_raw in (2, 3):  # Layer I or II
        fields["mode_extension"] = _MODE_EXTENSION.get(_extract_bits(word, 26, 27))

    fields["_mpeg_version_raw"] = version_raw
    fields["_layer_raw"] = layer_raw
    fields["_channel_mode_raw"] = channel_mode_raw
    return fields


def parse_video_header(eight_bytes: bytes) -> dict:
    """Decodes the 8 bytes immediately following an MPEG video sequence
    header start code (0x000001B3) into its technical fields."""
    w1, w2 = struct.unpack(">II", eight_bytes)

    bitrate_raw = _extract_bits(w2, 0, 17)  # bits 32-49 of the combined pair

    return {
        "image_width": _extract_bits(w1, 0, 11) or None,
        "image_height": _extract_bits(w1, 12, 23) or None,
        "aspect_ratio": _ASPECT_RATIO.get(_extract_bits(w1, 24, 27)),
        "frame_rate": _FRAME_RATE.get(_extract_bits(w1, 28, 31)),
        "video_bitrate": "Variable" if bitrate_raw == 0x3FFFF else bitrate_raw * 400,
    }


def parse_lame_header(data: bytes) -> dict:
    """Decodes the fields this project surfaces from a LAME 3.90+ extended
    VBR header (byte-offset positional, per the de facto LAME tag layout)."""
    fields: dict = {}
    if len(data) > 9:
        fields["lame_method"] = _LAME_METHOD.get(data[9] & 0x0F)
    if len(data) > 20:
        fields["lame_bitrate"] = data[20] * 1000
    if len(data) > 24:
        fields["lame_stereo_mode"] = _LAME_STEREO_MODE.get((data[24] & 0x1C) >> 2)
    return fields


def find_and_parse_xing(data: bytes, frame_end: int, version_raw: int, channel_mode_raw: int) -> dict | None:
    """Looks for a Xing/Info VBR header at the fixed offset past an audio
    frame header (offset depends on version + mono/stereo, per the de facto
    Xing tag convention), decodes whichever optional fields its flags byte
    says are present, and — if a LAME encoder signature immediately follows
    — decodes the LAME extended header too. Returns None if no Xing/Info tag
    is present; never raises on a truncated/malformed one, just returns
    whatever was read before truncation was hit.
    """
    is_mono = channel_mode_raw == 3
    offset = frame_end + (17 if is_mono else 32) if version_raw == 3 else (9 if is_mono else 17)

    if offset + 8 > len(data):
        return None
    tag = data[offset : offset + 4]
    if tag not in (b"Xing", b"Info"):
        return None
    is_vbr = tag == b"Xing"

    flags = struct.unpack_from(">I", data, offset + 4)[0]
    pos = offset + 8
    fields: dict = {}

    if flags & 0x01:  # VBRFrames
        if pos + 4 > len(data):
            return fields
        if is_vbr:
            fields["vbr_frames"] = struct.unpack_from(">I", data, pos)[0]
        pos += 4
    if flags & 0x02:  # VBRBytes
        if pos + 4 > len(data):
            return fields
        if is_vbr:
            fields["vbr_bytes"] = struct.unpack_from(">I", data, pos)[0]
        pos += 4
    if flags & 0x04:  # VBR TOC (100-byte seek table) — present but not decoded, low value here
        pos += 100
    if flags & 0x08:  # VBRScale
        if pos + 4 > len(data):
            return fields
        scale = struct.unpack_from(">I", data, pos)[0]
        if is_vbr:
            fields["vbr_scale"] = scale
        pos += 4

    if pos + 9 <= len(data):
        encoder_tag = data[pos : pos + 9]
        if encoder_tag[:4] in (b"LAME", b"GOGO"):
            fields["encoder"] = encoder_tag.decode("ascii", errors="replace")
            if encoder_tag >= b"LAME3.90":
                fields.update(parse_lame_header(data[pos:]))

    return fields


def parse(data: bytes) -> dict:
    """Runs the full MPEG audio+video discovery/decode over a buffer:
    finds the first valid audio frame header and/or video sequence header
    (either, both, or neither may be present depending on file content),
    decodes each, and looks for a Xing/LAME VBR header following the audio
    frame. Never raises — a stream with no recognizable MPEG audio or video
    sync just yields an empty result.
    """
    result: dict = {}

    audio_match = mpeg_walker.find_audio_frame_sync(data)
    if audio_match is not None:
        word, offset = audio_match
        audio_fields = parse_audio_header(word)
        xing = find_and_parse_xing(
            data, offset + 4, audio_fields["_mpeg_version_raw"], audio_fields["_channel_mode_raw"]
        )
        audio_fields = {k: v for k, v in audio_fields.items() if not k.startswith("_")}
        result["audio"] = audio_fields
        if xing:
            result["xing"] = xing

    video_header = mpeg_walker.find_video_sequence_header(data)
    if video_header is not None:
        result["video"] = parse_video_header(video_header)

    return result

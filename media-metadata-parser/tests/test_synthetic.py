"""Synthetic round-trip tests.

No real SFX files exist in this repo yet — real-world validation against a
sample library (cross-checked with exiftool per plan.md) is the next phase,
once that data is available. Until then, this builds minimal WAV/AIFF/RF64
byte strings by hand, with known bext/iXML/LIST/cue/adtl payloads, and
verifies every interpreter reads back exactly what was written. This is
deliberately narrower than real-world testing — it proves the parsers are
byte-exact against the spec, not that they handle every vendor's quirks.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from metaparser import extractor, models
from metaparser.chunks import (
    amr_walker,
    caf_walker,
    dts_walker,
    dv_walker,
    ebml_walker,
    flv_walker,
    iff_walker,
    mp4_walker,
    mpeg_walker,
    realmedia_walker,
    rf64,
    riff_walker,
    ts_walker,
)
from metaparser.interpreters import (
    amf0,
    amr,
    bext,
    caf,
    dts,
    dv,
    flash_video,
    ixml,
    list_info,
    m2ts,
    matroska,
    mpeg,
    opportunistic,
    quicktime_udta,
    realmedia,
)
from metaparser.ucs import categories, filename_parser

from db import indexer, schema, search


# ---------------------------------------------------------------------------
# Byte-building helpers (little-endian RIFF-shaped by default)
# ---------------------------------------------------------------------------


def _chunk(chunk_id: bytes, payload: bytes, big_endian: bool = False) -> bytes:
    endian = ">" if big_endian else "<"
    data = chunk_id + struct.pack(f"{endian}I", len(payload)) + payload
    if len(payload) % 2 == 1:
        data += b"\x00"
    return data


def _riff(form_type: bytes, chunks: bytes) -> bytes:
    payload = form_type + chunks
    return b"RIFF" + struct.pack("<I", len(payload)) + payload


def _form(form_type: bytes, chunks: bytes) -> bytes:
    payload = form_type + chunks
    return b"FORM" + struct.pack(">I", len(payload)) + payload


def build_bext_payload(
    description="Test description",
    originator="TestOrig",
    originator_reference="REF123",
    origination_date="2026-01-01",
    origination_time="12-00-00",
    time_reference=123456789,
    version=2,
    loudness_value=-23.0,
    loudness_range=7.0,
    max_true_peak=-1.0,
    max_momentary=-20.0,
    max_short_term=-22.0,
    coding_history="A=PCM,F=48000,W=24,M=stereo\r\n",
) -> bytes:
    buf = bytearray(602)

    def set_ascii(offset, size, text):
        b = text.encode("ascii")[:size]
        buf[offset : offset + len(b)] = b

    set_ascii(0, 256, description)
    set_ascii(256, 32, originator)
    set_ascii(288, 32, originator_reference)
    set_ascii(320, 10, origination_date)
    set_ascii(330, 8, origination_time)
    struct.pack_into("<I", buf, 338, time_reference & 0xFFFFFFFF)
    struct.pack_into("<I", buf, 342, (time_reference >> 32) & 0xFFFFFFFF)
    struct.pack_into("<H", buf, 346, version)
    struct.pack_into(
        "<5h",
        buf,
        412,
        round(loudness_value * 100),
        round(loudness_range * 100),
        round(max_true_peak * 100),
        round(max_momentary * 100),
        round(max_short_term * 100),
    )
    return bytes(buf) + coding_history.encode("ascii")


SAMPLE_IXML = b"""<BWFXML>
<IXML_VERSION>1.61</IXML_VERSION>
<PROJECT>TestProject</PROJECT>
<SCENE>1A</SCENE>
<TAKE>3</TAKE>
<ASWG>
<CATEGORY>BLAST</CATEGORY>
<SUB_CATEGORY>Explosion Large</SUB_CATEGORY>
<CATID>BLASTExplosion-Large</CATID>
<FX_NAME>Big Boom</FX_NAME>
<CREATOR_ID>JD</CREATOR_ID>
<SOURCE_ID>MyLib</SOURCE_ID>
</ASWG>
</BWFXML>"""


def build_info_payload() -> bytes:
    sub_chunks = (
        _chunk(b"INAM", b"Big Boom Title")
        + _chunk(b"IART", b"Some Artist")
        + _chunk(b"ICMT", b"A test comment")
        + _chunk(b"XVND", b"vendor specific value")  # unrecognized fourCC on purpose
    )
    return b"INFO" + sub_chunks


def build_minimal_wav(extra_chunks: bytes = b"") -> bytes:
    fmt_payload = struct.pack("<HHIIHH", 1, 2, 48000, 48000 * 2 * 2, 4, 16)  # PCM, stereo, 16-bit, 48k
    data_payload = b"\x00\x00" * 100
    chunks = _chunk(b"fmt ", fmt_payload) + extra_chunks + _chunk(b"data", data_payload)
    return _riff(b"WAVE", chunks)


# ---------------------------------------------------------------------------
# EBML/Matroska byte-building helpers
# ---------------------------------------------------------------------------


def _ebml_id_bytes(element_id: int) -> bytes:
    length = max(1, (element_id.bit_length() + 7) // 8)
    return element_id.to_bytes(length, "big")


def _ebml_size_bytes(size: int) -> bytes:
    length = 1
    while size > (1 << (7 * length)) - 2:  # reserve the all-1s pattern for "unknown size"
        length += 1
    marker = 0x80 >> (length - 1)
    value = size | (marker << ((length - 1) * 8))
    return value.to_bytes(length, "big")


def _ebml_element(element_id: int, payload: bytes) -> bytes:
    return _ebml_id_bytes(element_id) + _ebml_size_bytes(len(payload)) + payload


def build_matroska_bytes(doc_type: bytes = b"matroska") -> bytes:
    ebml_header_payload = _ebml_element(0x4286, (1).to_bytes(1, "big")) + _ebml_element(0x4282, doc_type)

    info_payload = (
        _ebml_element(0x7BA9, "Test Title".encode("utf-8"))
        + _ebml_element(0x4D80, b"libmatroska")
        + _ebml_element(0x4489, struct.pack(">f", 12.5))
    )

    audio_payload = _ebml_element(0xB5, struct.pack(">f", 48000.0)) + _ebml_element(0x9F, (2).to_bytes(1, "big"))
    track_entry_payload = (
        _ebml_element(0x83, (2).to_bytes(1, "big"))  # TrackType: audio
        + _ebml_element(0x86, b"A_AAC")
        + _ebml_element(0x22B59C, b"eng")
        + _ebml_element(0xE1, audio_payload)
    )
    tracks_payload = _ebml_element(0xAE, track_entry_payload)

    simple_tag_payload = _ebml_element(0x45A3, b"ARTIST") + _ebml_element(0x4487, "Test Artist".encode("utf-8"))
    tag_payload = _ebml_element(0x67C8, simple_tag_payload)
    tags_payload = _ebml_element(0x7373, tag_payload)

    cluster_payload = b"\x00" * 10  # dummy media data — must never be walked into

    segment_payload = (
        _ebml_element(0x1549A966, info_payload)
        + _ebml_element(0x1654AE6B, tracks_payload)
        + _ebml_element(0x1254C367, tags_payload)
        + _ebml_element(0x1F43B675, cluster_payload)
    )

    return _ebml_element(ebml_walker.EBML_HEADER_ID, ebml_header_payload) + _ebml_element(0x18538067, segment_payload)


# ---------------------------------------------------------------------------
# RealMedia byte-building helpers
# ---------------------------------------------------------------------------


def _rm_object(object_id: bytes, version: int, payload: bytes) -> bytes:
    total_size = realmedia_walker.OBJECT_HEADER_SIZE + len(payload)
    return object_id + struct.pack(">IH", total_size, version) + payload


def _rm_pstring(text: str, length_size: int) -> bytes:
    data = text.encode("utf-8")
    return len(data).to_bytes(length_size, "big") + data


def build_cont_payload(title="Test Title", author="Test Author", copyright_="Test Copyright", comment="Test Comment") -> bytes:
    return _rm_pstring(title, 2) + _rm_pstring(author, 2) + _rm_pstring(copyright_, 2) + _rm_pstring(comment, 2)


def build_mdpr_payload(stream_name="audio stream", mime_type="audio/x-pn-realaudio") -> bytes:
    fixed = struct.pack(">HIIIIIII", 0, 64000, 64000, 1024, 1024, 0, 0, 5000)
    return fixed + _rm_pstring(stream_name, 1) + _rm_pstring(mime_type, 1)


def build_realmedia_bytes() -> bytes:
    file_header_payload = struct.pack(">II", 0, 6)  # file_version, num_headers
    return (
        _rm_object(b".RMF", 0, file_header_payload)
        + _rm_object(b"CONT", 0, build_cont_payload())
        + _rm_object(b"MDPR", 0, build_mdpr_payload())
        + _rm_object(b"DATA", 0, b"\x01\x02\x03\x04")  # unrecognized-by-name payload, must stay raw
    )


# ---------------------------------------------------------------------------
# AMF0 byte-building helpers
# ---------------------------------------------------------------------------


def _amf0_number(value: float) -> bytes:
    return bytes([amf0.MARKER_NUMBER]) + struct.pack(">d", value)


def _amf0_boolean(value: bool) -> bytes:
    return bytes([amf0.MARKER_BOOLEAN, 1 if value else 0])


def _amf0_string(value: str) -> bytes:
    data = value.encode("utf-8")
    return bytes([amf0.MARKER_STRING]) + len(data).to_bytes(2, "big") + data


def _amf0_object(pairs: dict) -> bytes:
    body = b""
    for key, encoded_value in pairs.items():
        key_bytes = key.encode("utf-8")
        body += len(key_bytes).to_bytes(2, "big") + key_bytes + encoded_value
    return bytes([amf0.MARKER_OBJECT]) + body + b"\x00\x00\x09"


def _amf0_ecma_array(pairs: dict) -> bytes:
    body = struct.pack(">I", len(pairs))
    for key, encoded_value in pairs.items():
        key_bytes = key.encode("utf-8")
        body += len(key_bytes).to_bytes(2, "big") + key_bytes + encoded_value
    return bytes([amf0.MARKER_ECMA_ARRAY]) + body + b"\x00\x00\x09"


# ---------------------------------------------------------------------------
# FLV byte-building helpers
# ---------------------------------------------------------------------------


def _flv_tag(tag_type: int, payload: bytes, timestamp_ms: int = 0) -> bytes:
    data_size = len(payload)
    timestamp_lower = (timestamp_ms & 0xFFFFFF).to_bytes(3, "big")
    timestamp_ext = ((timestamp_ms >> 24) & 0xFF).to_bytes(1, "big")
    header = bytes([tag_type]) + data_size.to_bytes(3, "big") + timestamp_lower + timestamp_ext + b"\x00\x00\x00"
    tag = header + payload
    return tag + len(tag).to_bytes(4, "big")  # trailing PreviousTagSize


def build_flv_bytes() -> bytes:
    header = b"FLV" + bytes([1, 0x05]) + struct.pack(">I", 9)  # version=1, flags=audio+video, data_offset=9
    prev_tag_size0 = struct.pack(">I", 0)

    script_payload = _amf0_string("onMetaData") + _amf0_ecma_array(
        {
            "duration": _amf0_number(30.0),
            "width": _amf0_number(1280),
            "height": _amf0_number(720),
        }
    )

    tags = (
        _flv_tag(flv_walker.TAG_TYPE_SCRIPT_DATA, script_payload)
        + _flv_tag(flv_walker.TAG_TYPE_AUDIO, b"\xaf\x01" + b"\x00" * 4)
        + _flv_tag(flv_walker.TAG_TYPE_VIDEO, b"\x17\x01\x00\x00\x00" + b"\x00" * 4)
    )

    return header + prev_tag_size0 + tags


# ---------------------------------------------------------------------------
# MPEG-PS/ES byte-building helpers
# ---------------------------------------------------------------------------


def _mpeg_audio_word(
    version_raw: int,
    layer_raw: int,
    bitrate_index: int,
    sample_rate_index: int,
    channel_mode_raw: int,
    ms_stereo: int = 0,
    intensity_stereo: int = 0,
    mode_extension: int = 0,
    copyright_flag: int = 0,
    original: int = 1,
    emphasis: int = 0,
) -> int:
    word = 0x7FF << 21  # 11-bit frame sync
    word |= version_raw << 19
    word |= layer_raw << 17
    word |= 1 << 16  # protection bit (no CRC) — irrelevant to decode
    word |= bitrate_index << 12
    word |= sample_rate_index << 10
    word |= channel_mode_raw << 6
    if layer_raw == 1:  # Layer III
        word |= ms_stereo << 5
        word |= intensity_stereo << 4
    else:
        word |= mode_extension << 4
    word |= copyright_flag << 3
    word |= original << 2
    word |= emphasis
    return word


def _mpeg_video_header_bytes(width: int, height: int, aspect_raw: int, frame_rate_raw: int, bitrate_raw: int) -> bytes:
    w1 = (width << 20) | (height << 8) | (aspect_raw << 4) | frame_rate_raw
    w2 = bitrate_raw << 14
    return struct.pack(">II", w1, w2)


# ---------------------------------------------------------------------------
# MPEG-TS / M2TS byte-building helpers
# ---------------------------------------------------------------------------


def _psi_section(table_id: int, body_without_crc: bytes) -> bytes:
    body = body_without_crc + b"\x00\x00\x00\x00"  # dummy CRC32, not validated by our decoder
    section_length = len(body)
    header = bytes([table_id]) + struct.pack(">H", 0x8000 | 0x3000 | section_length)
    return header + body


def _pat_section(programs: dict[int, int]) -> bytes:
    body = struct.pack(">H", 1) + bytes([0xC1, 0, 0])  # transport_stream_id, misc, sec#, last_sec#
    for program_number, pmt_pid in programs.items():
        body += struct.pack(">H", program_number)
        body += struct.pack(">H", 0xE000 | (pmt_pid & 0x1FFF))
    return _psi_section(0x00, body)


def _pmt_section(program_number: int, pcr_pid: int, streams: list[tuple[int, int, bytes]]) -> bytes:
    body = struct.pack(">H", program_number) + bytes([0xC1, 0, 0])
    body += struct.pack(">H", 0xE000 | (pcr_pid & 0x1FFF))
    body += struct.pack(">H", 0xF000)  # program_info_length = 0
    for stream_type, elementary_pid, es_info in streams:
        body += bytes([stream_type])
        body += struct.pack(">H", 0xE000 | (elementary_pid & 0x1FFF))
        body += struct.pack(">H", 0xF000 | (len(es_info) & 0x0FFF))
        body += es_info
    return _psi_section(0x02, body)


def _ac3_descriptor(bitrate_code: int, surround: int, channels: int) -> bytes:
    return bytes([0x81, 3, 0x00, (bitrate_code << 2) | surround, channels << 1])


def _pcr_adaptation_field(pcr_base: int, pcr_ext_raw: int = 0x7E00) -> bytes:
    body = bytes([0x10]) + struct.pack(">I", pcr_base) + struct.pack(">H", pcr_ext_raw)
    return bytes([len(body)]) + body


def _ts_packet(pid: int, payload_unit_start: bool, payload: bytes = b"", adaptation: bytes = b"") -> bytes:
    prefix = 0x47000000
    if payload_unit_start:
        prefix |= 0x00400000
    prefix |= (pid & 0x1FFF) << 8
    if adaptation:
        prefix |= 0x00000020
    if payload:
        prefix |= 0x00000010
    header = struct.pack(">I", prefix)
    body = adaptation + payload
    pad_len = 188 - 4 - len(body)
    assert pad_len >= 0, "synthetic TS packet body too long"
    return header + body + b"\xff" * pad_len


def build_ts_bytes() -> bytes:
    pat = _pat_section({1: 0x100})
    pmt = _pmt_section(1, 0x101, [(0x81, 0x101, _ac3_descriptor(6, 2, 2))])

    packets = [
        _ts_packet(0, True, payload=b"\x00" + pat),
        _ts_packet(0x100, True, payload=b"\x00" + pmt),
        _ts_packet(0x101, False, adaptation=_pcr_adaptation_field(0)),
        _ts_packet(0x101, False, adaptation=_pcr_adaptation_field(45000)),
    ]
    return b"".join(packets)


# ---------------------------------------------------------------------------
# DV byte-building helpers
# ---------------------------------------------------------------------------


def build_dv_bytes() -> bytes:
    size = 80 * 6 + 80 * 16 * 3 + 3 + 8
    buf = bytearray(size)

    buf[0:4] = b"\x1f\x07\x00\x3f"  # DIF Header block sync (byte3=0x3f also encodes DSF=0, top bit clear)
    buf[4] = 0x00  # APT=0

    buf[80 * 5 + 48 + 3] = 0x00  # VideoSType=0x0 -> profile 0 (IEC 61834/SMPTE-314M NTSC)

    # All three VAUX packs must land in the same DIF block with nothing
    # unrecognized between them: `time` is reset by *any* pack that isn't
    # 0x61/0x62/0x63 (see dv._parse_vaux's "must be consecutive" comment,
    # transliterated from DV.pm), so scattering them across blocks whose
    # remaining slots are zero-filled would wipe out an already-found time
    # the moment the scan reached those zero packs.
    vaux1 = 80  # DIF block index 1
    buf[vaux1] = 0x50
    p_vc = vaux1 + 0 * 5 + 3
    buf[p_vc] = 0x61
    buf[p_vc + 2] = 0x02  # (t & 0x07) == 0x02 -> 16:9
    buf[p_vc + 3] = 0x10  # interlace bit
    p_date = vaux1 + 1 * 5 + 3
    buf[p_date] = 0x62
    buf[p_date + 2] = 0x15  # day (BCD "15")
    buf[p_date + 3] = 0x03  # month (BCD "03")
    buf[p_date + 4] = 0x26  # year (BCD "26" -> 2026)
    p_time = vaux1 + 2 * 5 + 3
    buf[p_time] = 0x63
    buf[p_time + 2] = 0x30  # seconds (BCD "30")
    buf[p_time + 3] = 0x15  # minutes (BCD "15")
    buf[p_time + 4] = 0x12  # hours (BCD "12")

    aaux_pos = 80 * 6 + 80 * 16 * 3 + 3
    buf[aaux_pos] = 0x50  # audio source pack
    buf[aaux_pos + 3] = 0x00  # stype=0 -> 2 channels
    buf[aaux_pos + 4] = 0x00  # freq=0 (48000), quant=0 (16-bit)

    return bytes(buf)


# ---------------------------------------------------------------------------
# AMR byte-building helpers
# ---------------------------------------------------------------------------


def _amr_frame(frame_type: int, variant: str = "nb") -> bytes:
    sizes = amr_walker._NB_FRAME_SIZES if variant == "nb" else amr_walker._WB_FRAME_SIZES
    size = sizes[frame_type]
    header = bytes([(frame_type << 3) | 0x04])  # bit2 = frame-quality-good flag, arbitrary here
    return header + b"\x00" * (size - 1)


def build_amr_bytes(variant: str = "nb", frame_types: list[int] | None = None) -> bytes:
    magic = amr_walker.MAGIC_WB if variant == "wb" else amr_walker.MAGIC_NB
    frame_types = frame_types if frame_types is not None else [7, 7, 0]
    return magic + b"".join(_amr_frame(t, variant) for t in frame_types)


# ---------------------------------------------------------------------------
# MP4/QuickTime (ISO-BMFF) byte-building helpers
# ---------------------------------------------------------------------------


def _mp4_box(box_type: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", 8 + len(payload)) + box_type + payload


def _legacy_text_atom(text: str) -> bytes:
    data = text.encode("utf-8")
    return struct.pack(">HH", len(data), 0) + data


def build_mov_with_legacy_udta_bytes() -> bytes:
    ftyp = _mp4_box(b"ftyp", b"qt  " + struct.pack(">I", 0) + b"qt  ")

    mvhd_payload = (
        b"\x00\x00\x00\x00"
        + struct.pack(">I", 0)  # creation_time
        + struct.pack(">I", 0)  # modification_time
        + struct.pack(">I", 1000)  # timescale
        + struct.pack(">I", 5000)  # duration (5s @ 1000)
        + struct.pack(">I", 0x00010000)  # rate
        + struct.pack(">H", 0x0100)  # volume
        + b"\x00" * 10  # reserved
        + b"\x00" * 36  # matrix
        + b"\x00" * 24  # predefined
        + struct.pack(">I", 2)  # next_track_id
    )
    mvhd = _mp4_box(b"mvhd", mvhd_payload)

    nam = _mp4_box("\xa9nam".encode("latin-1"), _legacy_text_atom("Test Title"))
    art = _mp4_box("\xa9ART".encode("latin-1"), _legacy_text_atom("Test Artist"))
    udta = _mp4_box(b"udta", nam + art)

    moov = _mp4_box(b"moov", mvhd + udta)
    return ftyp + moov


# ---------------------------------------------------------------------------
# CAF byte-building helpers
# ---------------------------------------------------------------------------


def _caf_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    return chunk_type + struct.pack(">q", len(payload)) + payload


def build_caf_desc_payload(
    sample_rate: float = 48000.0,
    format_id: bytes = b"lpcm",
    format_flags: int = 0,
    bytes_per_packet: int = 4,
    frames_per_packet: int = 1,
    channels_per_frame: int = 2,
    bits_per_channel: int = 16,
) -> bytes:
    return struct.pack(">d", sample_rate) + format_id + struct.pack(
        ">IIIII", format_flags, bytes_per_packet, frames_per_packet, channels_per_frame, bits_per_channel
    )


def build_caf_info_payload(pairs: dict[str, str]) -> bytes:
    body = struct.pack(">I", len(pairs))
    for key, value in pairs.items():
        body += key.encode("utf-8") + b"\x00" + value.encode("utf-8") + b"\x00"
    return body


def build_caf_bytes() -> bytes:
    header = b"caff" + struct.pack(">HH", 1, 0)
    desc = _caf_chunk(b"desc", build_caf_desc_payload())
    info = _caf_chunk(b"info", build_caf_info_payload({"title": "Test Title", "artist": "Test Artist"}))
    free = _caf_chunk(b"free", b"\x00" * 8)
    return header + desc + info + free


# ---------------------------------------------------------------------------
# DTS byte-building helpers
# ---------------------------------------------------------------------------


class _BitWriter:
    def __init__(self) -> None:
        self._bits: list[int] = []

    def write(self, value: int, n: int) -> None:
        for i in range(n - 1, -1, -1):
            self._bits.append((value >> i) & 1)

    def to_bytes(self) -> bytes:
        bits = self._bits[:]
        while len(bits) % 8 != 0:
            bits.append(0)
        out = bytearray()
        for i in range(0, len(bits), 8):
            byte = 0
            for b in bits[i : i + 8]:
                byte = (byte << 1) | b
            out.append(byte)
        return bytes(out)


def build_dts_frame_bytes(
    frame_type: int = 1,
    crc_present: int = 0,
    nblks: int = 15,
    fsize: int = 511,
    amode: int = 2,
    sfreq: int = 13,
    rate_index: int = 7,
    dynf: int = 0,
    timef: int = 0,
    auxf: int = 0,
    hdcd: int = 0,
    aspf: int = 0,
    lff: int = 0,
) -> bytes:
    w = _BitWriter()
    w.write(int.from_bytes(dts_walker.SYNC_WORD, "big"), 32)
    w.write(frame_type, 1)
    w.write(0, 5)  # SHORT (deficit sample count) — not decoded
    w.write(crc_present, 1)
    w.write(nblks, 7)
    w.write(fsize, 14)
    w.write(amode, 6)
    w.write(sfreq, 4)
    w.write(rate_index, 5)
    w.write(0, 1)  # FixedBit/MIX — not decoded
    w.write(dynf, 1)
    w.write(timef, 1)
    w.write(auxf, 1)
    w.write(hdcd, 1)
    w.write(0, 3)  # EXT_AUDIO_ID — not decoded
    w.write(0, 1)  # EXT_AUDIO — not decoded
    w.write(aspf, 1)
    w.write(lff, 2)
    w.write(0, 1)  # HFLAG — not decoded
    return w.to_bytes()


# ---------------------------------------------------------------------------
# Phase 1: chunk walkers
# ---------------------------------------------------------------------------


def test_riff_walker_reads_known_chunks():
    wav = build_minimal_wav()
    chunks = riff_walker.walk(wav)
    ids = [c.chunk_id for c in chunks]
    assert ids == ["fmt ", "data"]
    assert len(chunks[0].raw) == 16


def test_riff_walker_survives_truncation():
    wav = build_minimal_wav()
    truncated = wav[:-50]
    chunks = riff_walker.walk(truncated)
    # must not raise, and must return whatever it could read
    assert len(chunks) >= 1


def test_riff_walker_survives_lying_size_field():
    wav = bytearray(build_minimal_wav())
    # Corrupt the RIFF-level size field to something wrong.
    struct.pack_into("<I", wav, 4, 99999)
    chunks = riff_walker.walk(bytes(wav))
    assert any(c.chunk_id == "fmt " for c in chunks)


def test_iff_walker_reads_aiff_chunks():
    name_chunk = _chunk(b"NAME", b"Test AIFF", big_endian=True)
    comm_payload = struct.pack(">hlh", 2, 100, 16) + b"\x40\x0e\xac\x44\x00\x00\x00\x00\x00\x00"
    comm_chunk = _chunk(b"COMM", comm_payload, big_endian=True)
    aiff = _form(b"AIFF", name_chunk + comm_chunk)

    assert iff_walker.is_iff(aiff)
    assert iff_walker.form_type(aiff) == "AIFF"
    chunks = iff_walker.walk(aiff)
    ids = [c.chunk_id for c in chunks]
    assert ids == ["NAME", "COMM"]
    assert chunks[0].raw == b"Test AIFF"


def test_rf64_resolves_sentinel_data_size():
    data_payload = b"\xab" * 200
    fmt_payload = struct.pack("<HHIIHH", 1, 2, 48000, 48000 * 2 * 2, 4, 16)

    ds64_table_entries = b""  # no other overflowed chunks
    ds64_payload = (
        struct.pack("<Q", 0)  # riff size (unused by our walk() assertions)
        + struct.pack("<Q", len(data_payload))  # data size
        + struct.pack("<Q", 0)  # sample count
        + struct.pack("<I", 0)  # table length
        + ds64_table_entries
    )

    data_chunk_header = b"data" + struct.pack("<I", 0xFFFFFFFF)
    chunks_bytes = (
        _chunk(b"ds64", ds64_payload)
        + _chunk(b"fmt ", fmt_payload)
        + data_chunk_header
        + data_payload
    )
    rf64_bytes = b"RF64" + struct.pack("<I", 0xFFFFFFFF) + b"WAVE" + chunks_bytes

    assert rf64.is_rf64(rf64_bytes)
    chunks = rf64.walk(rf64_bytes)
    ids = [c.chunk_id for c in chunks]
    assert ids == ["fmt ", "data"]
    data_chunk = next(c for c in chunks if c.chunk_id == "data")
    assert data_chunk.raw == data_payload


def test_extractor_routes_rf64_files_correctly(tmp_path: Path):
    # Regression test: is_riff() and is_rf64() check the same 4 magic bytes
    # for mutually exclusive values ("RIFF" vs "RF64"/"BW64"), so nesting
    # the rf64 check inside the riff check made it permanently unreachable —
    # every real RF64/BW64 file fell through to "unknown format". This goes
    # through metaparser.extractor.extract() end-to-end (not rf64.walk()
    # directly) specifically because that's the path the bug was in.
    data_payload = b"\xcd" * 50
    ds64_payload = (
        struct.pack("<Q", 0)
        + struct.pack("<Q", len(data_payload))
        + struct.pack("<Q", 0)
        + struct.pack("<I", 0)
    )
    chunks_bytes = _chunk(b"ds64", ds64_payload) + b"data" + struct.pack("<I", 0xFFFFFFFF) + data_payload
    rf64_bytes = b"RF64" + struct.pack("<I", 0xFFFFFFFF) + b"WAVE" + chunks_bytes

    path = tmp_path / "test.wav"
    path.write_bytes(rf64_bytes)

    meta = extractor.extract(path)

    assert meta.file_format == "rf64"
    assert meta.errors == []


# ---------------------------------------------------------------------------
# EBML walker + Matroska interpreter
# ---------------------------------------------------------------------------


def test_ebml_walker_reads_top_level_elements():
    ebml_header = _ebml_element(0x4282, b"matroska")
    segment_payload = b"\x00" * 4
    data = _ebml_element(ebml_walker.EBML_HEADER_ID, ebml_header) + _ebml_element(0x18538067, segment_payload)

    elements = ebml_walker.walk(data)
    ids = [e.element_id for e in elements]
    assert ids == [ebml_walker.EBML_HEADER_ID, 0x18538067]
    assert elements[1].raw == segment_payload


def test_ebml_walker_survives_truncated_header():
    data = _ebml_element(ebml_walker.EBML_HEADER_ID, b"x" * 20)
    truncated = data[:2]  # cuts off mid size-vint
    elements = ebml_walker.walk(truncated)  # must not raise
    assert elements == []


def test_ebml_walker_survives_truncated_payload():
    data = _ebml_element(ebml_walker.EBML_HEADER_ID, b"x" * 20)
    truncated = data[:-5]
    elements = ebml_walker.walk(truncated)  # must not raise
    assert len(elements) == 1
    assert len(elements[0].raw) < 20


def test_ebml_walker_handles_unknown_size_sentinel():
    # 8-byte size vint, marker bit + all data bits set to 1 -> "unknown size".
    unknown_size_vint = b"\x01" + b"\xff" * 7
    payload = b"hello world"
    data = _ebml_id_bytes(0x18538067) + unknown_size_vint + payload

    elements = ebml_walker.walk(data)
    assert len(elements) == 1
    assert elements[0].size_unknown is True
    assert elements[0].raw == payload


def test_is_ebml_detects_magic():
    assert ebml_walker.is_ebml(_ebml_element(ebml_walker.EBML_HEADER_ID, b"\x00"))
    assert not ebml_walker.is_ebml(b"RIFF....")


def test_matroska_parses_info_tracks_tags_and_stops_at_cluster():
    data = build_matroska_bytes()
    tree = matroska.parse(data)

    info = matroska.extract_info(tree)
    assert info["Title"] == "Test Title"
    assert info["MuxingApp"] == "libmatroska"
    assert info["Duration"] == pytest.approx(12.5, rel=1e-4)  # raw tick count, NOT seconds — see extract_duration_secs

    tracks = matroska.extract_tracks(tree)
    assert len(tracks) == 1
    assert tracks[0]["codec_id"] == "A_AAC"
    assert tracks[0]["language"] == "eng"
    assert tracks[0]["sampling_frequency"] == pytest.approx(48000.0, rel=1e-4)
    assert tracks[0]["channels"] == 2

    tags = matroska.extract_tags(tree)
    assert tags["ARTIST"] == "Test Artist"

    segment = tree["Segment"]
    assert "Cluster" not in segment  # media data must never be walked into or recorded


def test_matroska_extract_duration_secs_applies_timecode_scale():
    # Regression: Duration is a tick count in units of TimecodeScale
    # (ns/tick), not literal seconds. 5000 ticks * 1,000,000 ns/tick =
    # 5,000,000,000 ns = 5s — treating the raw tick count as seconds
    # directly (the original bug) would have reported 5000s instead.
    info_payload = _ebml_element(0x2AD7B1, (1_000_000).to_bytes(4, "big")) + _ebml_element(
        0x4489, struct.pack(">f", 5000.0)
    )
    data = _ebml_element(ebml_walker.EBML_HEADER_ID, b"\x00") + _ebml_element(
        0x18538067, _ebml_element(0x1549A966, info_payload)
    )
    tree = matroska.parse(data)
    assert matroska.extract_duration_secs(tree) == pytest.approx(5.0)


def test_matroska_extract_duration_secs_defaults_scale_when_absent():
    # No TimecodeScale element present -> the spec's default of 1ms/tick
    # applies: 2000 ticks * 1ms = 2s.
    info_payload = _ebml_element(0x4489, struct.pack(">f", 2000.0))
    data = _ebml_element(ebml_walker.EBML_HEADER_ID, b"\x00") + _ebml_element(
        0x18538067, _ebml_element(0x1549A966, info_payload)
    )
    tree = matroska.parse(data)
    assert matroska.extract_duration_secs(tree) == pytest.approx(2.0)


def test_matroska_extract_duration_secs_none_when_no_duration():
    tree = {"Segment": {"Info": {"Title": "No duration here"}}}
    assert matroska.extract_duration_secs(tree) is None


def test_matroska_rejects_non_ebml_data():
    with pytest.raises(matroska.MatroskaParseError):
        matroska.parse(b"RIFF....WAVEfmt ")


def test_realmedia_walker_reads_objects():
    data = build_realmedia_bytes()
    objects = realmedia_walker.walk(data)
    ids = [o.object_id for o in objects]
    assert ids == [".RMF", "CONT", "MDPR", "DATA"]


def test_realmedia_walker_survives_truncation():
    data = build_realmedia_bytes()
    truncated = data[:-10]
    objects = realmedia_walker.walk(truncated)  # must not raise
    assert len(objects) >= 1


def test_realmedia_rejects_non_rmf_data():
    with pytest.raises(realmedia_walker.RealMediaParseError):
        realmedia_walker.walk(b"RIFF....WAVEfmt ")


def test_realmedia_parses_cont_and_mdpr_and_keeps_unknown_raw():
    data = build_realmedia_bytes()
    tree = realmedia.parse(data)

    assert tree["CONT"]["title"] == "Test Title"
    assert tree["CONT"]["author"] == "Test Author"
    assert tree["MDPR"][0]["stream_name"] == "audio stream"
    assert tree["MDPR"][0]["mime_type"] == "audio/x-pn-realaudio"
    assert tree["DATA"] == b"\x01\x02\x03\x04"  # unrecognized object type, kept raw and dynamic


def test_realmedia_cont_keeps_readable_fields_when_later_field_truncated():
    payload = _rm_pstring("Complete Title", 2) + _rm_pstring("Auth", 2)[:-1]  # author cut mid-text
    fields = realmedia.parse_cont(payload)  # must not raise
    assert fields["title"] == "Complete Title"
    assert "author" not in fields


def test_amf0_decodes_mixed_object_dynamically():
    # No fixed schema on either side: decode_all doesn't know "duration" or
    # "stereo" are coming — it walks whatever key/value pairs are present.
    encoded = _amf0_string("onMetaData") + _amf0_ecma_array(
        {
            "duration": _amf0_number(12.5),
            "width": _amf0_number(1920),
            "stereo": _amf0_boolean(True),
            "encoder": _amf0_string("Lavf"),
        }
    )
    values = amf0.decode_all(encoded)
    assert values[0] == "onMetaData"
    props = values[1]
    assert props["duration"] == pytest.approx(12.5)
    assert props["width"] == pytest.approx(1920.0)
    assert props["stereo"] is True
    assert props["encoder"] == "Lavf"


def test_amf0_stops_gracefully_on_truncated_trailing_value():
    encoded = _amf0_string("first") + bytes([amf0.MARKER_NUMBER]) + b"\x00\x00"  # truncated number
    values = amf0.decode_all(encoded)  # must not raise
    assert values == ["first"]


def test_amf0_decodes_nested_objects():
    inner = _amf0_object({"nested_key": _amf0_string("nested_value")})
    encoded = _amf0_object({"outer": inner})
    values = amf0.decode_all(encoded)
    assert values[0]["outer"]["nested_key"] == "nested_value"


def test_flv_walker_reads_tags():
    data = build_flv_bytes()
    tags = flv_walker.walk(data)
    types = [t.tag_type for t in tags]
    assert types == [flv_walker.TAG_TYPE_SCRIPT_DATA, flv_walker.TAG_TYPE_AUDIO, flv_walker.TAG_TYPE_VIDEO]


def test_flv_walker_survives_truncation():
    data = build_flv_bytes()
    truncated = data[:-3]
    tags = flv_walker.walk(truncated)  # must not raise
    assert len(tags) >= 2


def test_flv_rejects_non_flv_data():
    with pytest.raises(flv_walker.FlvParseError):
        flv_walker.walk(b"RIFF....WAVEfmt ")


def test_flash_video_decodes_script_data_dynamically():
    data = build_flv_bytes()
    summary = flash_video.parse(data)

    assert summary["script_data"]["duration"] == pytest.approx(30.0)
    assert summary["script_data"]["width"] == pytest.approx(1280.0)
    assert summary["audio_tag_count"] == 1
    assert summary["video_tag_count"] == 1


def test_caf_walker_reads_chunks():
    data = build_caf_bytes()
    chunks = caf_walker.walk(data)
    assert [c.chunk_type for c in chunks] == ["desc", "info", "free"]


def test_caf_walker_survives_truncation():
    data = build_caf_bytes()
    truncated = data[:-5]
    chunks = caf_walker.walk(truncated)  # must not raise
    assert len(chunks) >= 2


def test_caf_walker_rejects_non_caf_data():
    with pytest.raises(caf_walker.CafParseError):
        caf_walker.walk(b"RIFF....WAVEfmt ")


def test_caf_parses_desc_and_dynamic_info():
    data = build_caf_bytes()
    result = caf.parse(data)

    assert result["desc"]["sample_rate"] == pytest.approx(48000.0)
    assert result["desc"]["format_id"] == "lpcm"
    assert result["desc"]["channels_per_frame"] == 2
    assert result["desc"]["bits_per_channel"] == 16

    # 'info' is genuinely dynamic — no key whitelist, whatever pairs were
    # written come back exactly as written.
    assert result["info"]["title"] == "Test Title"
    assert result["info"]["artist"] == "Test Artist"

    assert result["free"] == b"\x00" * 8  # unrecognized-by-name chunk kept raw


def test_dts_walker_finds_sync():
    frame = build_dts_frame_bytes()
    data = b"\x00" * 10 + frame
    assert dts_walker.find_sync(data) == 10


def test_dts_rejects_data_without_sync():
    assert dts_walker.find_sync(b"\x00" * 40) is None


def test_dts_decodes_frame_header():
    frame = build_dts_frame_bytes(nblks=15, fsize=511, amode=2, sfreq=13, rate_index=7)
    result = dts.parse(frame)

    assert result["blocks_per_channel"] == 16  # nblks + 1
    assert result["frame_size_bytes"] == 512  # fsize + 1
    assert result["channel_arrangement"] == "L+R (stereo)"
    assert result["sample_rate"] == 48000
    assert result["bit_rate_index"] == 7  # deliberately not mapped to kbps
    assert result["duration_secs_this_frame"] == pytest.approx((16 * 32) / 48000)


def test_dts_reports_unknown_sample_rate_honestly():
    # Regression-flavored: this must report None, not a guessed value, for a
    # reserved SFREQ index — the whole point of this module's narrow scope.
    frame = build_dts_frame_bytes(sfreq=0)
    result = dts.parse(frame)
    assert result["sample_rate"] is None
    assert "duration_secs_this_frame" not in result


def test_dts_parse_raises_without_sync():
    with pytest.raises(dts.DtsInterpretError):
        dts.parse(b"\x00" * 40)


def test_amr_nb_walk_and_parse():
    data = build_amr_bytes(variant="nb", frame_types=[7, 7, 0, 8])  # two 12.2k, one 4.75k, one SID
    variant, frame_count = amr_walker.walk(data)
    assert variant == "nb"
    assert frame_count == 4

    summary = amr.parse(data)
    assert summary["variant"] == "AMR-NB"
    assert summary["frame_count"] == 4
    assert summary["duration_secs"] == pytest.approx(4 * 0.02)


def test_amr_wb_variant_detected():
    data = build_amr_bytes(variant="wb", frame_types=[0, 1])
    variant, frame_count = amr_walker.walk(data)
    assert variant == "wb"
    assert frame_count == 2


def test_amr_stops_gracefully_on_reserved_frame_type():
    # frame type 12 is reserved/unused in the NB table — must stop cleanly,
    # keeping the frames counted before it, not raise or guess a size.
    good_frame = _amr_frame(7, "nb")
    bad_header = bytes([(12 << 3) | 0x04])
    data = amr_walker.MAGIC_NB + good_frame + bad_header
    variant, frame_count = amr_walker.walk(data)
    assert variant == "nb"
    assert frame_count == 1


def test_amr_rejects_data_without_magic():
    with pytest.raises(amr_walker.AmrParseError):
        amr_walker.walk(b"not an amr file at all")


def test_mp4_walker_reads_top_level_boxes():
    data = build_mov_with_legacy_udta_bytes()
    boxes = mp4_walker.walk(data)
    types = [b.box_type for b in boxes]
    assert types == ["ftyp", "moov"]


def test_mp4_walker_survives_truncation():
    data = build_mov_with_legacy_udta_bytes()
    truncated = data[:-20]
    boxes = mp4_walker.walk(truncated)  # must not raise
    assert len(boxes) >= 1


def test_mp4_walker_rejects_non_iso_bmff_data():
    assert not mp4_walker.is_iso_bmff(b"RIFF....WAVEfmt ")
    assert mp4_walker.is_iso_bmff(build_mov_with_legacy_udta_bytes())


def test_mp4_find_path_locates_nested_box():
    data = build_mov_with_legacy_udta_bytes()
    udta_payload = mp4_walker.find_path(data, "moov", "udta")
    assert udta_payload is not None
    assert mp4_walker.find_path(data, "moov", "nonexistent") is None


def test_quicktime_udta_decodes_legacy_text_atoms_mutagen_would_miss():
    # Regression context: mutagen's MP4 reader only understands the modern
    # ilst atom shape — this exact legacy '\xa9nam' text-atom shape (no
    # 'data' box wrapper) comes back with zero tags from mutagen even though
    # the title is genuinely present in the file. This is the gap
    # quicktime_udta.py exists to close.
    data = build_mov_with_legacy_udta_bytes()
    result = quicktime_udta.parse(data)
    assert result["\xa9nam"] == "Test Title"
    assert result["\xa9ART"] == "Test Artist"


def test_quicktime_udta_empty_when_no_udta_present():
    ftyp = _mp4_box(b"ftyp", b"isom" + struct.pack(">I", 0))
    data = ftyp + _mp4_box(b"moov", b"")
    assert quicktime_udta.parse(data) == {}


def test_mpeg_audio_frame_sync_and_decode():
    word = _mpeg_audio_word(
        version_raw=3, layer_raw=1, bitrate_index=5, sample_rate_index=0, channel_mode_raw=0,
        ms_stereo=1, intensity_stereo=0, original=1,
    )
    data = b"\x00" * 10 + struct.pack(">I", word) + b"\x00" * 10

    match = mpeg_walker.find_audio_frame_sync(data)
    assert match is not None
    found_word, offset = match
    assert offset == 10
    assert found_word == word

    fields = mpeg.parse_audio_header(found_word)
    assert fields["mpeg_audio_version"] == 1
    assert fields["audio_layer"] == 3
    assert fields["audio_bitrate"] == 64000
    assert fields["sample_rate"] == 44100
    assert fields["channel_mode"] == "Stereo"
    assert fields["ms_stereo"] is True
    assert fields["intensity_stereo"] is False
    assert fields["original_media"] is True


def test_mpeg_rejects_junk_as_no_sync_found():
    assert mpeg_walker.find_audio_frame_sync(b"\x00" * 40) is None


def test_mpeg_video_sequence_header_decode():
    header_bytes = _mpeg_video_header_bytes(width=720, height=480, aspect_raw=8, frame_rate_raw=3, bitrate_raw=1000)
    data = mpeg_walker.VIDEO_SEQUENCE_HEADER_START_CODE + header_bytes

    found = mpeg_walker.find_video_sequence_header(data)
    assert found == header_bytes

    fields = mpeg.parse_video_header(found)
    assert fields["image_width"] == 720
    assert fields["image_height"] == 480
    assert fields["aspect_ratio"] == "4:3, 625 line, PAL, CCIR601"
    assert fields["frame_rate"] == 25
    assert fields["video_bitrate"] == 400000


def test_mpeg_xing_header_decoded_dynamically():
    word = _mpeg_audio_word(version_raw=3, layer_raw=1, bitrate_index=5, sample_rate_index=0, channel_mode_raw=0)
    frame = struct.pack(">I", word)
    xing_offset = 4 + 32  # version 1, not-mono -> +32 per find_and_parse_xing
    padding = b"\x00" * (xing_offset - 4)
    flags = struct.pack(">I", 0x01 | 0x02 | 0x08)
    xing_body = (
        b"Xing" + flags + struct.pack(">I", 100) + struct.pack(">I", 50000) + struct.pack(">I", 90)
    )
    data = frame + padding + xing_body

    xing = mpeg.find_and_parse_xing(data, frame_end=4, version_raw=3, channel_mode_raw=0)
    assert xing["vbr_frames"] == 100
    assert xing["vbr_bytes"] == 50000
    assert xing["vbr_scale"] == 90


def test_mpeg_parse_end_to_end_combines_audio_and_video():
    audio_word = _mpeg_audio_word(version_raw=3, layer_raw=1, bitrate_index=5, sample_rate_index=0, channel_mode_raw=0)
    video_bytes = _mpeg_video_header_bytes(width=720, height=480, aspect_raw=1, frame_rate_raw=3, bitrate_raw=500)
    data = struct.pack(">I", audio_word) + b"\x00" * 40 + mpeg_walker.VIDEO_SEQUENCE_HEADER_START_CODE + video_bytes

    result = mpeg.parse(data)
    assert result["audio"]["audio_bitrate"] == 64000
    assert result["video"]["image_width"] == 720


def test_ts_walker_reads_packets_and_pcr():
    data = build_ts_bytes()
    packets = ts_walker.walk(data)
    pids = [p.pid for p in packets]
    assert pids == [0, 0x100, 0x101, 0x101]
    assert packets[2].pcr == 0
    assert packets[3].pcr == 600 * 45000


def test_ts_walker_survives_truncation():
    # Stride detection needs 4 full packets' worth of sync bytes to trust a
    # stride over a coincidental 0x47 elsewhere — so the truncation has to
    # land after that, in a 5th packet, to test "survives" rather than
    # "fails to even detect the format".
    extra_packet = _ts_packet(0x101, False, adaptation=_pcr_adaptation_field(90000))
    full = build_ts_bytes() + extra_packet
    truncated = full[: 188 * 4 + 50]  # 4 full packets + a partial 5th
    packets = ts_walker.walk(truncated)  # must not raise
    assert len(packets) == 4


def test_ts_rejects_non_ts_data():
    with pytest.raises(ts_walker.TsParseError):
        ts_walker.walk(b"RIFF....WAVEfmt ")


def test_m2ts_discovers_program_and_ac3_stream_dynamically():
    data = build_ts_bytes()
    result = m2ts.parse(data)

    assert len(result["programs"]) == 1
    program = result["programs"][0]
    assert program["program_number"] == 1
    assert program["pcr_pid"] == 0x101

    assert len(program["streams"]) == 1
    stream = program["streams"][0]
    assert stream["stream_type"] == 0x81
    assert stream["stream_type_name"] == "A52/AC-3 Audio"
    assert stream["elementary_pid"] == 0x101
    assert stream["ac3"]["audio_bitrate"] == 96000
    assert stream["ac3"]["surround_mode"] == "Dolby surround"
    assert stream["ac3"]["audio_channels"] == 2

    assert result["duration_secs"] == pytest.approx(1.0)


def test_dv_walker_finds_sync():
    data = build_dv_bytes()
    assert dv_walker.find_dif_start(data) == 0


def test_dv_walker_returns_none_without_signature():
    assert dv_walker.find_dif_start(b"\x00" * 5000) is None


def test_dv_parses_profile_and_vaux_and_aaux():
    data = build_dv_bytes()
    fields = dv.parse(data)

    assert fields["image_width"] == 720
    assert fields["image_height"] == 480
    assert fields["video_format"] == "IEC 61834, SMPTE-314M - 525/60 (NTSC)"
    assert fields["colorimetry"] == "4:1:1"
    assert fields["frame_rate"] == pytest.approx(29.97, abs=0.01)

    assert fields["date_time_original"] == "2026:03:15 12:15:30"
    assert fields["aspect_ratio"] == "16:9"
    assert fields["video_scan_type"] == "Interlaced"

    assert fields["audio_sample_rate"] == 48000
    assert fields["audio_channels"] == 2
    assert fields["audio_bits_per_sample"] == 16


def test_dv_rejects_data_without_sync():
    with pytest.raises(dv.DvParseError):
        dv.parse(b"\x00" * 5000)


def test_matroska_unrecognized_element_kept_under_raw_hex_key():
    # 0x4999 (not in ELEMENT_NAMES): top byte 0x49 has its marker bit at 0x40,
    # so it round-trips as a valid 2-byte EBML ID — an arbitrary ID like
    # 0x9999 would misparse, since 0x99's own top bit (0x80) would make the
    # walker read it back as a *different*, 1-byte ID.
    unknown_element = _ebml_element(0x4999, b"surprise")
    data = _ebml_element(ebml_walker.EBML_HEADER_ID, unknown_element) + _ebml_element(0x18538067, b"\x00")

    tree = matroska.parse(data)
    assert tree["EBML"]["0x4999"] == b"surprise"


# ---------------------------------------------------------------------------
# Phase 2: payload interpreters
# ---------------------------------------------------------------------------


def test_bext_round_trip():
    payload = build_bext_payload()
    parsed = bext.parse(payload)
    assert parsed.description == "Test description"
    assert parsed.originator == "TestOrig"
    assert parsed.origination_date == "2026-01-01"
    assert parsed.time_reference == 123456789
    assert parsed.version == 2
    assert parsed.loudness_value == pytest.approx(-23.0)
    assert parsed.max_true_peak_level == pytest.approx(-1.0)
    assert "PCM" in parsed.coding_history


def test_bext_pre_v2_has_no_loudness_fields():
    payload = build_bext_payload(version=1)
    parsed = bext.parse(payload)
    assert parsed.loudness_value is None
    assert parsed.max_short_term_loudness is None


def test_bext_rejects_too_short_payload():
    with pytest.raises(bext.BextParseError):
        bext.parse(b"too short")


def test_ixml_generic_walk_and_sfx_extraction():
    tree = ixml.parse(SAMPLE_IXML)
    assert "BWFXML" in tree
    assert tree["BWFXML"]["PROJECT"] == "TestProject"

    sfx = ixml.extract_sfx_fields(tree)
    assert sfx["category"] == "BLAST"
    assert sfx["catid"] == "BLASTExplosion-Large"
    assert sfx["fx_name"] == "Big Boom"
    assert sfx["creator_id"] == "JD"


def test_ixml_recovers_from_malformed_xml():
    malformed = b"<BWFXML><PROJECT>Unclosed<SCENE>1A</SCENE></BWFXML>"
    tree = ixml.parse(malformed)  # must not raise
    assert "BWFXML" in tree


def test_list_info_parses_known_and_unknown_fourccs():
    payload = build_info_payload()
    assert list_info.is_info_list(payload)
    info = list_info.parse_info(payload)
    assert info["title"] == "Big Boom Title"
    assert info["artist"] == "Some Artist"
    assert info["comment"] == "A test comment"
    assert info["XVND"] == "vendor specific value"  # unrecognized fourCC kept raw, not dropped


def test_cue_and_adtl_round_trip():
    cue_payload = struct.pack("<I", 1) + struct.pack("<II4sIII", 1, 500, b"data", 0, 0, 500)
    points = opportunistic.parse_cue(cue_payload)
    assert points == [
        {
            "name_id": 1,
            "position": 500,
            "fcc_chunk": "data",
            "chunk_start": 0,
            "block_start": 0,
            "sample_offset": 500,
        }
    ]

    labl_payload = struct.pack("<I", 1) + b"My Label\x00"
    adtl_payload = b"adtl" + _chunk(b"labl", labl_payload)
    labels = opportunistic.parse_adtl(adtl_payload)
    assert labels[1] == {"kind": "labl", "text": "My Label"}


def test_cue_survives_truncated_payload():
    assert opportunistic.parse_cue(struct.pack("<I", 5) + b"short") == []


# ---------------------------------------------------------------------------
# Phase 3: UCS filename extraction
# ---------------------------------------------------------------------------


def test_ucs_filename_parses_full_pattern():
    result = filename_parser.parse_filename("BLASTExplosion-Large_BigBoom_JD_MyLib.wav")
    assert result.cat_id == "BLASTExplosion-Large"
    assert result.fx_name == "BigBoom"
    assert result.creator_id == "JD"
    assert result.source_id == "MyLib"
    assert result.category_entry is not None
    assert result.category_entry.category == "BLAST"


def test_ucs_filename_handles_thin_filename():
    result = filename_parser.parse_filename("randomfile.wav")
    assert result.cat_id is None
    assert result.fx_name == "randomfile"


def test_ucs_filename_rejects_short_vendor_prefix():
    # Regression: "PM_Phone_Foley_..." (a real PMSFX library filename) was
    # matching "PM" as a false-positive CatID under the old 2-letter
    # threshold — it's a 2-letter product-line prefix, not a UCS category.
    result = filename_parser.parse_filename("PM_Phone_Foley_1 Phone, Pick up.m4a")
    assert result.cat_id is None
    # No CatID detected means no positional shift — "PM" lands as fx_name
    # rather than being dropped, so raw_tokens/downstream data isn't lost,
    # it's just not attributed to the (nonexistent) category slot.
    assert result.fx_name == "PM"


def test_ucs_filename_accepts_multi_hyphen_cat_id():
    # UCS "Advanced" format documents CatID blocks with more than one
    # hyphenated piece (e.g. CatID-UserCategory-FXName) — not seen in real
    # data yet, but the regex should tolerate it since it only adds matches.
    result = filename_parser.parse_filename("GUN-Rifle-AK47_BigBang_JD_MyLib.wav")
    assert result.cat_id == "GUN-Rifle-AK47"


def test_ucs_cross_check_agrees_when_catid_matches():
    ucs_result = filename_parser.parse_filename("BLASTExplosion-Large_BigBoom_JD_MyLib.wav")
    ixml_fields = {"catid": "BLASTExplosion-Large", "category": "BLAST"}
    report = filename_parser.cross_check_against_ixml(ucs_result, ixml_fields)
    assert report["comparable"] is True
    assert report["agrees"] is True


def test_ucs_cross_check_flags_disagreement():
    ucs_result = filename_parser.parse_filename("BLASTExplosion-Large_BigBoom_JD_MyLib.wav")
    ixml_fields = {"catid": "WHOOSHFast-Generic"}
    report = filename_parser.cross_check_against_ixml(ucs_result, ixml_fields)
    assert report["comparable"] is True
    assert report["agrees"] is False


def test_categories_lookup_and_case_insensitive_fallback():
    entry = categories.lookup("BLASTExplosion-Large")
    assert entry is not None
    assert entry.category == "BLAST"
    assert categories.lookup_ci("blastexplosion-large") is not None
    assert categories.lookup("NOT-A-REAL-CATID") is None


# ---------------------------------------------------------------------------
# End-to-end: full synthetic WAV through metaparser.extractor
# ---------------------------------------------------------------------------


def test_end_to_end_extraction(tmp_path: Path):
    bext_payload = build_bext_payload()
    ixml_chunk = _chunk(b"iXML", SAMPLE_IXML)
    bext_chunk = _chunk(b"bext", bext_payload)
    info_chunk = _chunk(b"LIST", build_info_payload())

    wav_bytes = build_minimal_wav(extra_chunks=bext_chunk + ixml_chunk + info_chunk)

    wav_path = tmp_path / "BLASTExplosion-Large_BigBoom_JD_MyLib.wav"
    wav_path.write_bytes(wav_bytes)

    meta = extractor.extract(wav_path)

    assert meta.file_format == "wav"
    assert meta.errors == []
    assert meta.bext_raw["description"] == "Test description"
    assert meta.ixml_raw["BWFXML"]["ASWG"]["FX_NAME"] == "Big Boom"
    assert meta.info_raw["title"] == "Big Boom Title"
    assert meta.ucs_from_filename["cat_id"] == "BLASTExplosion-Large"
    assert meta.ucs_ixml_cross_check["comparable"] is True
    assert meta.ucs_ixml_cross_check["agrees"] is True


def test_end_to_end_matroska_extraction(tmp_path: Path):
    data = build_matroska_bytes()
    path = tmp_path / "test.mkv"
    path.write_bytes(data)

    meta = extractor.extract(path)

    assert meta.file_format == "matroska"
    assert meta.errors == []
    assert meta.matroska_raw is not None
    assert matroska.extract_info(meta.matroska_raw)["Title"] == "Test Title"
    assert matroska.extract_tags(meta.matroska_raw)["ARTIST"] == "Test Artist"


def test_end_to_end_webm_doc_type_detected(tmp_path: Path):
    data = build_matroska_bytes(doc_type=b"webm")
    path = tmp_path / "test.webm"
    path.write_bytes(data)

    meta = extractor.extract(path)

    assert meta.file_format == "webm"


def test_end_to_end_realmedia_extraction(tmp_path: Path):
    data = build_realmedia_bytes()
    path = tmp_path / "sample.rm"
    path.write_bytes(data)

    meta = extractor.extract(path)

    assert meta.file_format == "realmedia"
    assert meta.errors == []
    assert meta.realmedia_raw["CONT"]["title"] == "Test Title"


def test_end_to_end_flv_extraction(tmp_path: Path):
    data = build_flv_bytes()
    path = tmp_path / "sample.flv"
    path.write_bytes(data)

    meta = extractor.extract(path)

    assert meta.file_format == "flv"
    assert meta.errors == []
    assert meta.flv_raw["script_data"]["duration"] == pytest.approx(30.0)


def test_end_to_end_mpeg_extraction(tmp_path: Path):
    audio_word = _mpeg_audio_word(version_raw=3, layer_raw=1, bitrate_index=5, sample_rate_index=0, channel_mode_raw=0)
    data = struct.pack(">I", audio_word) + b"\x00" * 20

    path = tmp_path / "sample.mpg"
    path.write_bytes(data)

    meta = extractor.extract(path)

    assert meta.file_format == "mpeg"
    assert meta.errors == []
    assert meta.mpeg_raw["audio"]["audio_bitrate"] == 64000


def test_end_to_end_m2ts_extraction(tmp_path: Path):
    data = build_ts_bytes()
    path = tmp_path / "sample.m2ts"
    path.write_bytes(data)

    meta = extractor.extract(path)

    assert meta.file_format == "m2ts"
    assert meta.errors == []
    assert meta.m2ts_raw["programs"][0]["streams"][0]["stream_type_name"] == "A52/AC-3 Audio"


def test_end_to_end_dv_extraction(tmp_path: Path):
    data = build_dv_bytes()
    path = tmp_path / "sample.dv"
    path.write_bytes(data)

    meta = extractor.extract(path)

    assert meta.file_format == "dv"
    assert meta.errors == []
    assert meta.dv_raw["video_format"] == "IEC 61834, SMPTE-314M - 525/60 (NTSC)"
    assert meta.dv_raw["date_time_original"] == "2026:03:15 12:15:30"


def test_end_to_end_amr_extraction(tmp_path: Path):
    data = build_amr_bytes(variant="nb", frame_types=[7, 7, 7])
    path = tmp_path / "sample.amr"
    path.write_bytes(data)

    meta = extractor.extract(path)

    assert meta.file_format == "amr"
    assert meta.errors == []
    assert meta.amr_raw["variant"] == "AMR-NB"
    assert meta.amr_raw["frame_count"] == 3


def test_end_to_end_mov_legacy_udta_extraction(tmp_path: Path):
    data = build_mov_with_legacy_udta_bytes()
    path = tmp_path / "sample.mov"
    path.write_bytes(data)

    meta = extractor.extract(path)

    assert meta.udta_raw is not None
    assert meta.udta_raw["\xa9nam"] == "Test Title"
    # mutagen itself should find no ilst tags for this legacy-only file —
    # confirms udta_raw is genuinely filling a gap, not duplicating mutagen.
    assert not (meta.tags_raw or {}).get("tags")


def test_end_to_end_3gp_uses_iso_bmff_video_path(tmp_path: Path):
    # Verifies the previously-unverified 3GP routing: content is identical
    # ISO-BMFF/legacy-udta shape as the .mov test above, just a different
    # extension, and it must be routed through the same video+udta path.
    data = build_mov_with_legacy_udta_bytes()
    path = tmp_path / "sample.3gp"
    path.write_bytes(data)

    meta = extractor.extract(path)

    assert meta.udta_raw is not None
    assert meta.udta_raw["\xa9nam"] == "Test Title"


def test_end_to_end_caf_extraction(tmp_path: Path):
    data = build_caf_bytes()
    path = tmp_path / "sample.caf"
    path.write_bytes(data)

    meta = extractor.extract(path)

    assert meta.file_format == "caf"
    assert meta.errors == []
    assert meta.caf_raw["info"]["title"] == "Test Title"


def test_end_to_end_dts_extraction(tmp_path: Path):
    data = build_dts_frame_bytes()
    path = tmp_path / "sample.dts"
    path.write_bytes(data)

    meta = extractor.extract(path)

    assert meta.file_format == "dts"
    assert meta.errors == []
    assert meta.dts_raw["channel_arrangement"] == "L+R (stereo)"


def test_end_to_end_handles_corrupt_bext_gracefully(tmp_path: Path):
    bad_bext_chunk = _chunk(b"bext", b"too short to be valid")
    wav_bytes = build_minimal_wav(extra_chunks=bad_bext_chunk)

    wav_path = tmp_path / "plain_file.wav"
    wav_path.write_bytes(wav_bytes)

    meta = extractor.extract(wav_path)  # must not raise

    assert meta.bext_raw is None
    assert len(meta.errors) == 1
    assert "bext" in meta.errors[0]


# ---------------------------------------------------------------------------
# db.indexer: search-field extraction from the new raw sources
#
# The point of these tests is the negative space as much as the positive:
# every _fields_from_* helper must only ever put genuinely descriptive
# strings into 'blob' (never numbers, raw bytes, or a per-frame-only value
# masquerading as a whole-file duration), while still surfacing real content
# a person would actually search for.
# ---------------------------------------------------------------------------


def test_indexer_fields_from_matroska_only_surfaces_strings(tmp_path: Path):
    data = build_matroska_bytes()
    path = tmp_path / "sample.mkv"
    path.write_bytes(data)
    meta = extractor.extract(path)

    fields = indexer._fields_from_matroska(meta)
    assert fields["description"] == "Test Title"
    assert set(fields["blob"]) == {"Test Title", "libmatroska", "Test Artist"}
    assert all(isinstance(v, str) for v in fields["blob"])
    assert fields["sample_rate"] == 48000
    assert fields["channels"] == 2
    # Duration must go through the TimecodeScale-aware converter, not the
    # raw tick count directly (build_matroska_bytes has no TimecodeScale
    # element, so the spec default of 1ms/tick applies: 12.5 * 0.001 = 0.0125s).
    assert fields["duration_secs"] == pytest.approx(0.0125)


def test_indexer_fields_from_realmedia_converts_ms_to_secs(tmp_path: Path):
    data = build_realmedia_bytes()
    path = tmp_path / "sample.rm"
    path.write_bytes(data)
    meta = extractor.extract(path)

    fields = indexer._fields_from_realmedia(meta)
    assert fields["description"] == "Test Title"
    assert "Test Author" in fields["blob"]
    assert fields["duration_secs"] == pytest.approx(5.0)  # build_mdpr_payload's duration=5000 -> ms


def test_indexer_fields_from_flv_excludes_numeric_metadata_from_blob(tmp_path: Path):
    data = build_flv_bytes()
    path = tmp_path / "sample.flv"
    path.write_bytes(data)
    meta = extractor.extract(path)

    fields = indexer._fields_from_flv(meta)
    # build_flv_bytes' onMetaData is all-numeric (duration/width/height) —
    # none of it belongs in a free-text search blob.
    assert fields["blob"] == []
    assert fields["duration_secs"] == pytest.approx(30.0)


def test_indexer_fields_from_dv_populates_technical_columns(tmp_path: Path):
    data = build_dv_bytes()
    path = tmp_path / "sample.dv"
    path.write_bytes(data)
    meta = extractor.extract(path)

    fields = indexer._fields_from_dv(meta)
    assert fields["sample_rate"] == 48000
    assert fields["channels"] == 2
    assert fields["duration_secs"] is not None and fields["duration_secs"] > 0


def test_indexer_fields_from_udta_prefers_nam_atom_as_description():
    meta = models.RawFileMetadata(
        file_path="x.mov", file_format="mov",
        udta_raw={"\xa9nam": "Legacy Title", "\xa9ART": "Legacy Artist", "free": b"\x00\x00"},
    )
    fields = indexer._fields_from_udta(meta)
    assert fields["description"] == "Legacy Title"
    assert set(fields["blob"]) == {"Legacy Title", "Legacy Artist"}  # raw bytes value excluded


def test_indexer_fields_from_caf_dynamic_info_and_technical_desc(tmp_path: Path):
    data = build_caf_bytes()
    path = tmp_path / "sample.caf"
    path.write_bytes(data)
    meta = extractor.extract(path)

    fields = indexer._fields_from_caf(meta)
    assert fields["description"] == "Test Title"
    assert set(fields["blob"]) == {"Test Title", "Test Artist"}
    assert fields["sample_rate"] == 48000
    assert fields["channels"] == 2


def test_indexer_fields_from_dts_excludes_per_frame_duration():
    meta = models.RawFileMetadata(
        file_path="x.dts", file_format="dts",
        dts_raw={"channel_arrangement": "L+R (stereo)", "sample_rate": 48000, "duration_secs_this_frame": 0.0107},
    )
    fields = indexer._fields_from_dts(meta)
    assert fields["sample_rate"] == 48000
    assert fields["blob"] == ["L+R (stereo)"]
    # Regression: a per-frame duration must never be reported as if it were
    # the whole file's duration — that would be actively misleading, not
    # just incomplete.
    assert fields["duration_secs"] is None


def test_indexer_extract_row_fields_leaves_ucs_category_columns_unrelated_for_mkv(tmp_path: Path):
    # Matroska/CAF/etc. have no UCS-taxonomy concept — this project's
    # dedicated category/subcategory/cat_id columns must stay untouched by
    # them rather than getting populated with something unrelated.
    data = build_matroska_bytes()
    path = tmp_path / "sample.mkv"
    path.write_bytes(data)
    meta = extractor.extract(path)

    fields = indexer._extract_row_fields(meta)
    assert fields["category"] is None
    assert fields["cat_id"] is None
    assert fields["description"] == "Test Title"
    assert "Test Artist" in fields["tags_blob"]
    assert fields["duration_secs"] == pytest.approx(0.0125)


def test_indexer_index_and_search_finds_matroska_title_end_to_end(tmp_path: Path):
    # The actual question this whole set of tests exists to answer: does a
    # real full-text search over the real SQLite/FTS5 index find a title
    # that only exists in one of the new formats' raw metadata? Runs the
    # complete pipeline — extractor.extract -> indexer.index_file ->
    # search.full_text_search — not just the intermediate field dict.
    data = build_matroska_bytes()
    media_path = tmp_path / "sample.mkv"
    media_path.write_bytes(data)

    db_path = tmp_path / "index.sqlite3"
    conn = schema.open_db(db_path)
    try:
        indexer.index_file(conn, media_path)
        conn.commit()
    finally:
        conn.close()

    results = search.full_text_search(db_path, "Test Title")
    assert len(results) == 1
    assert results[0].filename == "sample.mkv"
    assert results[0].description == "Test Title"
    assert results[0].duration_secs == pytest.approx(0.0125)

    # And a search for something that only exists as a hex-keyed unknown
    # element or a raw numeric field must NOT match — proving search really
    # is scoped to descriptive text, not a blind dump of raw_json.
    assert search.full_text_search(db_path, "libmatroska")[0].filename == "sample.mkv"
    assert search.full_text_search(db_path, "0x4999") == []

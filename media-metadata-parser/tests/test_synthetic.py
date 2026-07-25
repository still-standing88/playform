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

from metaparser import extractor
from metaparser.chunks import iff_walker, rf64, riff_walker
from metaparser.interpreters import bext, ixml, list_info, opportunistic
from metaparser.ucs import categories, filename_parser


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


def test_end_to_end_handles_corrupt_bext_gracefully(tmp_path: Path):
    bad_bext_chunk = _chunk(b"bext", b"too short to be valid")
    wav_bytes = build_minimal_wav(extra_chunks=bad_bext_chunk)

    wav_path = tmp_path / "plain_file.wav"
    wav_path.write_bytes(wav_bytes)

    meta = extractor.extract(wav_path)  # must not raise

    assert meta.bext_raw is None
    assert len(meta.errors) == 1
    assert "bext" in meta.errors[0]

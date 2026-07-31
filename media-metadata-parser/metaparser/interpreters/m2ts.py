"""MPEG-2 Transport Stream (M2TS/TS) interpreter, built on
metaparser.chunks.ts_walker.

Discovers whatever programs and elementary streams are actually declared in
the file's own PAT (Program Association Table) and PMT (Program Map Table)
sections — nothing about what streams "should" exist is assumed. STREAM_TYPES
below is the ISO 13818-1 / DVB stream_type registry (a spec-defined
value->meaning map, the TS equivalent of a MIME-type registry — not an
arbitrary tag-naming convenience layer). Any stream_type not in it still gets
reported, labeled "Unknown (0xNN)", exactly like archive/exiftool's M2TS.pm
does — nothing found in the PMT is dropped for being unrecognized. Cross-
checked against that module's own reference set — see ../../CREDITS.md.

Deliberately NOT ported: M2TS.pm's per-dashcam-vendor GPS/accelerometer
telemetry decoders (Novatek, Innovv, Jomise, Blueskysea, and others) — those
are undocumented, single-sample-reverse-engineered heuristics for
proprietary in-stream data formats, explicitly marked by ExifTool's own
comments as "empirical based on 1 sample" and "highly experimental". Porting
them without real samples of our own to validate against would just be
guessing, and they're specific to dashcam hardware, not general media
metadata this project's SFX/audio/video library use case needs.
"""

from __future__ import annotations

import logging
import struct

from metaparser.chunks import ts_walker

logger = logging.getLogger(__name__)

PAT_PID = 0

# program map table "stream_type" registry (ISO 13818-1 Table 2-34 + common
# DVB/Blu-ray private extensions).
STREAM_TYPES = {
    0x00: "Reserved", 0x01: "MPEG-1 Video", 0x02: "MPEG-2 Video", 0x03: "MPEG-1 Audio",
    0x04: "MPEG-2 Audio", 0x05: "ISO 13818-1 private sections", 0x06: "ISO 13818-1 PES private data",
    0x07: "ISO 13522 MHEG", 0x08: "ISO 13818-1 DSM-CC", 0x09: "ISO 13818-1 auxiliary",
    0x0A: "ISO 13818-6 multi-protocol encap", 0x0B: "ISO 13818-6 DSM-CC U-N msgs",
    0x0C: "ISO 13818-6 stream descriptors", 0x0D: "ISO 13818-6 sections", 0x0E: "ISO 13818-1 auxiliary",
    0x0F: "MPEG-2 AAC Audio", 0x10: "MPEG-4 Video", 0x11: "MPEG-4 LATM AAC Audio",
    0x12: "MPEG-4 generic", 0x13: "ISO 14496-1 SL-packetized",
    0x14: "ISO 13818-6 Synchronized Download Protocol", 0x15: "Packetized metadata",
    0x16: "Sectioned metadata", 0x17: "ISO/IEC 13818-6 DSM CC Data Carousel metadata",
    0x18: "ISO/IEC 13818-6 DSM CC Object Carousel metadata",
    0x19: "ISO/IEC 13818-6 Synchronized Download Protocol metadata",
    0x1A: "ISO/IEC 13818-11 IPMP", 0x1B: "H.264 (AVC) Video",
    0x1C: "ISO/IEC 14496-3 (MPEG-4 raw audio)", 0x1D: "ISO/IEC 14496-17 (MPEG-4 text)",
    0x1E: "ISO/IEC 23002-3 (MPEG-4 auxiliary video)",
    0x1F: "ISO/IEC 14496-10 SVC (MPEG-4 AVC sub-bitstream)",
    0x20: "ISO/IEC 14496-10 MVC (MPEG-4 AVC sub-bitstream)",
    0x21: "ITU-T Rec. T.800 and ISO/IEC 15444 (JPEG 2000 video)", 0x24: "H.265 (HEVC) Video",
    0x42: "Chinese Video Standard", 0x7F: "ISO/IEC 13818-11 IPMP (DRM)",
    0x80: "DigiCipher II Video", 0x81: "A52/AC-3 Audio", 0x82: "HDMV DTS Audio",
    0x83: "LPCM Audio", 0x84: "SDDS Audio", 0x85: "ATSC Program ID", 0x86: "DTS-HD Audio",
    0x87: "E-AC-3 Audio", 0x8A: "DTS Audio",
    0x90: "Presentation Graphic Stream (subtitle)", 0x91: "A52b/AC-3 Audio",
    0x92: "DVD_SPU vls Subtitle", 0x94: "SDDS Audio", 0xA0: "MSCODEC Video",
    0xEA: "Private ES (VC-1)",
}

# PSI "table_id" registry (DVB SI spec).
TABLE_IDS = {
    0x00: "Program Association", 0x01: "Conditional Access", 0x02: "Program Map",
    0x03: "Transport Stream Description", 0x40: "Actual Network Information",
    0x41: "Other Network Information", 0x42: "Actual Service Description",
    0x46: "Other Service Description", 0x4A: "Bouquet Association",
    0x4E: "Actual Event Information - Present/Following",
    0x4F: "Other Event Information - Present/Following",
    0x50: "Actual Event Information - Schedule", 0x60: "Other Event Information - Schedule",
    0x70: "Time/Date", 0x71: "Running Status", 0x72: "Stuffing", 0x73: "Time Offset",
    0x7E: "Discontinuity Information", 0x7F: "Selection Information",
}

_AC3_DESCRIPTOR_TAG = 0x81

AC3_BITRATES = {
    0: 32000, 1: 40000, 2: 48000, 3: 56000, 4: 64000, 5: 80000, 6: 96000, 7: 112000,
    8: 128000, 9: 160000, 10: 192000, 11: 224000, 12: 256000, 13: 320000, 14: 384000,
    15: 448000, 16: 512000, 17: 576000, 18: 640000,
    32: "32000 max", 33: "40000 max", 34: "48000 max", 35: "56000 max", 36: "64000 max",
    37: "80000 max", 38: "96000 max", 39: "112000 max", 40: "128000 max", 41: "160000 max",
    42: "192000 max", 43: "224000 max", 44: "256000 max", 45: "320000 max", 46: "384000 max",
    47: "448000 max", 48: "512000 max", 49: "576000 max", 50: "640000 max",
}
AC3_SURROUND_MODES = {0: "Not indicated", 1: "Not Dolby surround", 2: "Dolby surround"}
AC3_CHANNELS = {0: "1 + 1", 1: 1, 2: 2, 3: 3, 4: "2/1", 5: "3/1", 6: "2/2", 7: "3/2", 8: 1,
                 9: "2 max", 10: "3 max", 11: "4 max", 12: "5 max", 13: "6 max"}


def parse_ac3_descriptor(desc: bytes) -> dict:
    if len(desc) < 3:
        return {}
    v = desc[:3]
    return {
        "audio_bitrate": AC3_BITRATES.get(v[1] >> 2),
        "surround_mode": AC3_SURROUND_MODES.get(v[1] & 0x03),
        "audio_channels": AC3_CHANNELS.get((v[2] >> 1) & 0x0F),
    }


def _assemble_sections(packets: list[ts_walker.RawPacket], pid: int) -> list[bytes]:
    """Reassembles PSI (PAT/PMT) sections for one PID across as many packets
    as it takes, using each section's own declared section_length rather
    than assuming one packet = one section. A section that never completes
    (file ends mid-section) is simply dropped, not returned partial —
    callers shouldn't have to guess whether a section is whole."""
    sections: list[bytes] = []
    buf = b""
    collecting = False
    expected_len: int | None = None

    for packet in packets:
        if packet.pid != pid or not packet.payload:
            continue
        data = packet.payload

        if packet.payload_unit_start:
            collecting = True
            pointer = data[0] if data else 0
            buf = data[1 + pointer :]
            expected_len = 3 + (struct.unpack_from(">H", buf, 1)[0] & 0x0FFF) if len(buf) >= 3 else None
        elif collecting:
            buf += data
        else:
            continue

        if collecting and expected_len is not None and len(buf) >= expected_len:
            sections.append(buf[:expected_len])
            collecting, buf, expected_len = False, b"", None

    return sections


def _read_pat(section: bytes) -> dict[int, int]:
    """Returns {program_number: pmt_pid}, program_number 0 (network PID) excluded."""
    if len(section) < 8:
        return {}
    section_length = struct.unpack_from(">H", section, 1)[0] & 0x0FFF
    end = min(3 + section_length - 4, len(section))  # exclude trailing 4-byte CRC

    programs: dict[int, int] = {}
    pos = 8
    while pos + 4 <= end:
        program_number = struct.unpack_from(">H", section, pos)[0]
        pmt_pid = struct.unpack_from(">H", section, pos + 2)[0] & 0x1FFF
        if program_number != 0:
            programs[program_number] = pmt_pid
        pos += 4
    return programs


def _read_pmt(section: bytes) -> tuple[int | None, list[dict]]:
    if len(section) < 12:
        return None, []
    section_length = struct.unpack_from(">H", section, 1)[0] & 0x0FFF
    end = min(3 + section_length - 4, len(section))
    pcr_pid = struct.unpack_from(">H", section, 8)[0] & 0x1FFF
    program_info_length = struct.unpack_from(">H", section, 10)[0] & 0x0FFF
    pos = 12 + program_info_length

    streams: list[dict] = []
    while pos + 5 <= end:
        stream_type = section[pos]
        elementary_pid = struct.unpack_from(">H", section, pos + 1)[0] & 0x1FFF
        es_info_length = struct.unpack_from(">H", section, pos + 3)[0] & 0x0FFF

        stream: dict = {
            "stream_type": stream_type,
            "stream_type_name": STREAM_TYPES.get(stream_type, f"Unknown (0x{stream_type:02x})"),
            "elementary_pid": elementary_pid,
        }

        desc_pos = pos + 5
        desc_end = min(desc_pos + es_info_length, end)
        while desc_pos + 2 <= desc_end:
            descriptor_tag = section[desc_pos]
            descriptor_length = section[desc_pos + 1]
            desc_data = section[desc_pos + 2 : desc_pos + 2 + descriptor_length]
            if descriptor_tag == _AC3_DESCRIPTOR_TAG:
                stream["ac3"] = parse_ac3_descriptor(desc_data)
            desc_pos += 2 + descriptor_length

        streams.append(stream)
        pos += 5 + es_info_length

    return pcr_pid, streams


def parse(data: bytes) -> dict:
    """Walks the whole transport stream once, reassembles the PAT and every
    PMT it points to, and reports the discovered program/stream structure
    plus a PCR-derived duration when at least two PCR timestamps were seen.
    A malformed PAT/PMT section is logged and simply yields fewer streams,
    never raises past this call.
    """
    packets = ts_walker.walk(data)

    programs: dict[int, int] = {}
    for section in _assemble_sections(packets, PAT_PID):
        try:
            programs.update(_read_pat(section))
        except (struct.error, IndexError) as exc:
            logger.warning("malformed PAT section: %s", exc)

    result_programs = []
    for program_number, pmt_pid in programs.items():
        for section in _assemble_sections(packets, pmt_pid):
            try:
                pcr_pid, streams = _read_pmt(section)
            except (struct.error, IndexError) as exc:
                logger.warning("malformed PMT section for program %d: %s", program_number, exc)
                continue
            result_programs.append({"program_number": program_number, "pcr_pid": pcr_pid, "streams": streams})

    result: dict = {"programs": result_programs}

    pcrs = [p.pcr for p in packets if p.pcr is not None]
    if len(pcrs) >= 2:
        delta = pcrs[-1] - pcrs[0]
        if delta < 0:
            delta += 300 * (1 << 33)  # 33-bit PCR base wraparound
        result["duration_secs"] = delta / 27_000_000  # PCR clock is 27MHz

    return result

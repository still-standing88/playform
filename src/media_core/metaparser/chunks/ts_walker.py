"""MPEG-2 Transport Stream (TS) packet walker — .ts/.m2ts/.mts.

Fixed-size packets (188 bytes; M2TS/BDAV adds an optional 4-byte timecode
prefix per packet, so the real packet stride is 192 bytes for those files —
both are auto-detected by requiring the sync byte to land correctly across
several consecutive packets, not just one, since a single stray 0x47
elsewhere in the stream shouldn't misdetect the stride). Each packet's
4-byte prefix carries the PID and adaptation-field flags; the adaptation
field, when present, can carry a PCR (Program Clock Reference) timestamp.

This module only demuxes packets into (pid, payload_unit_start, pcr,
payload) — PAT/PMT parsing and stream discovery is
metaparser.interpreters.m2ts's job, mirroring this package's usual
chunks/interpreters split. Public spec reference: ISO/IEC 13818-1; the same
reference set archive/exiftool's M2TS.pm cites — see ../../CREDITS.md.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SYNC_BYTE = 0x47
PACKET_SIZE = 188
M2TS_PACKET_SIZE = 192  # 4-byte timecode prefix + 188-byte TS packet


@dataclass(frozen=True)
class RawPacket:
    pid: int
    payload_unit_start: bool
    pcr: int | None
    """Combined 33-bit base + 9-bit extension Program Clock Reference, in
    27MHz clock ticks, or None if this packet's adaptation field carried no
    PCR."""
    payload: bytes
    offset: int


class TsParseError(Exception):
    pass


def _detect_packet_stride(data: bytes) -> int | None:
    for stride, timecode_len in ((PACKET_SIZE, 0), (M2TS_PACKET_SIZE, 4)):
        if len(data) < stride * 4:
            continue
        if all(data[timecode_len + stride * i] == SYNC_BYTE for i in range(4)):
            return stride
    return None


def is_transport_stream(data: bytes) -> bool:
    return _detect_packet_stride(data) is not None


def walk(data: bytes) -> list[RawPacket]:
    stride = _detect_packet_stride(data)
    if stride is None:
        raise TsParseError("no MPEG-TS sync pattern found (0x47 every 188 or 192 bytes)")
    timecode_len = 4 if stride == M2TS_PACKET_SIZE else 0

    packets: list[RawPacket] = []
    pos = 0
    end = len(data)

    while pos + stride <= end:
        packet_start = pos + timecode_len
        if data[packet_start] != SYNC_BYTE:
            logger.warning("lost TS sync at offset %d — stopping walk", packet_start)
            break

        prefix = struct.unpack_from(">I", data, packet_start)[0]
        payload_unit_start = bool(prefix & 0x00400000)
        pid = (prefix & 0x001FFF00) >> 8
        adaptation_field_exists = bool(prefix & 0x00000020)
        payload_exists = bool(prefix & 0x00000010)

        cursor = packet_start + 4
        packet_end = packet_start + PACKET_SIZE
        pcr = None

        if adaptation_field_exists and cursor < packet_end:
            adaptation_length = data[cursor]
            cursor += 1
            if adaptation_length > 0 and cursor + adaptation_length <= packet_end:
                flags = data[cursor]
                if flags & 0x10 and adaptation_length >= 7:  # PCR_flag
                    pcr_base = int.from_bytes(data[cursor + 1 : cursor + 5], "big")
                    pcr_ext = int.from_bytes(data[cursor + 5 : cursor + 7], "big")
                    pcr = 300 * (2 * pcr_base + (pcr_ext >> 15)) + (pcr_ext & 0x1FF)
            cursor += adaptation_length

        payload = data[cursor:packet_end] if payload_exists and cursor <= packet_end else b""

        packets.append(
            RawPacket(
                pid=pid,
                payload_unit_start=payload_unit_start,
                pcr=pcr,
                payload=payload,
                offset=packet_start,
            )
        )
        pos += stride

    return packets

"""DV (raw Digital Video) interpreter, built on metaparser.chunks.dv_walker.

Every field here is either (a) a profile lookup keyed by two header bits
(DSF, VideoSType) against the fixed set of DV format variants the standard
defines (IEC 61834 / SMPTE-314M / SMPTE-370M), or (b) one of a handful of
VAUX/AAUX "pack" types (0x61 video control, 0x62 date, 0x63 time, 0x50 audio
source) — DV's own version of a tag-ID dispatch, though only these few pack
types carry anything this project surfaces. Every other pack type in the
VAUX/AAUX area is skipped not because of a fixed-whitelist shortcut, but
because DV genuinely doesn't define descriptive metadata anywhere else in
the bitstream — confirmed by reading archive/exiftool's DV.pm end to end.
See ../../CREDITS.md: the profile table and every byte offset below are
direct, disclosed transliterations of that module, not independently
re-derived from the DV standard, since this project doesn't hold a copy of
it and has no real DV sample to validate an independent reading against.

Every read here is bounds-checked against the buffer length before use —
this is fixed-offset positional decoding of a raw bitstream with no size
fields to validate against, so "return whatever fields fit safely, skip the
rest" is the only form graceful degradation can take here.
"""

from __future__ import annotations

from media_core.metaparser.chunks import dv_walker

_DV_PROFILES = [
    {"dsf": 0, "video_s_type": 0x0, "frame_size": 120000, "video_format": "IEC 61834, SMPTE-314M - 525/60 (NTSC)",
     "colorimetry": "4:1:1", "frame_rate": 30000 / 1001, "image_height": 480, "image_width": 720},
    {"dsf": 1, "video_s_type": 0x0, "frame_size": 144000, "video_format": "IEC 61834 - 625/50 (PAL)",
     "colorimetry": "4:2:0", "frame_rate": 25.0, "image_height": 576, "image_width": 720},
    {"dsf": 1, "video_s_type": 0x0, "frame_size": 144000, "video_format": "SMPTE-314M - 625/50 (PAL)",
     "colorimetry": "4:1:1", "frame_rate": 25.0, "image_height": 576, "image_width": 720},
    {"dsf": 0, "video_s_type": 0x4, "frame_size": 240000,
     "video_format": "DVCPRO50: SMPTE-314M - 525/60 (NTSC) 50 Mbps",
     "colorimetry": "4:2:2", "frame_rate": 30000 / 1001, "image_height": 480, "image_width": 720},
    {"dsf": 1, "video_s_type": 0x4, "frame_size": 288000,
     "video_format": "DVCPRO50: SMPTE-314M - 625/50 (PAL) 50 Mbps",
     "colorimetry": "4:2:2", "frame_rate": 25.0, "image_height": 576, "image_width": 720},
    {"dsf": 0, "video_s_type": 0x14, "frame_size": 480000,
     "video_format": "DVCPRO HD: SMPTE-370M - 1080i60 100 Mbps",
     "colorimetry": "4:2:2", "frame_rate": 30000 / 1001, "image_height": 1080, "image_width": 1280},
    {"dsf": 1, "video_s_type": 0x14, "frame_size": 576000,
     "video_format": "DVCPRO HD: SMPTE-370M - 1080i50 100 Mbps",
     "colorimetry": "4:2:2", "frame_rate": 25.0, "image_height": 1080, "image_width": 1440},
    {"dsf": 0, "video_s_type": 0x18, "frame_size": 240000,
     "video_format": "DVCPRO HD: SMPTE-370M - 720p60 100 Mbps",
     "colorimetry": "4:2:2", "frame_rate": 60000 / 1001, "image_height": 720, "image_width": 960},
    {"dsf": 1, "video_s_type": 0x18, "frame_size": 288000,
     "video_format": "DVCPRO HD: SMPTE-370M - 720p50 100 Mbps",
     "colorimetry": "4:2:2", "frame_rate": 50.0, "image_height": 720, "image_width": 960},
    {"dsf": 1, "video_s_type": 0x1, "frame_size": 144000, "video_format": "IEC 61883-5 - 625/50 (PAL)",
     "colorimetry": "4:2:0", "frame_rate": 25.0, "image_height": 576, "image_width": 720},
]

_AUDIO_SAMPLE_RATE = {0: 48000, 1: 44100, 2: 32000}
_AUDIO_CHANNELS = {0: 2, 1: 0, 2: 4, 3: 8}


class DvParseError(Exception):
    pass


def _match_profile(dsf: int, stype: int, special_case: bool) -> dict | None:
    if special_case:
        return _DV_PROFILES[2]
    for profile in _DV_PROFILES:
        if profile["dsf"] == dsf and profile["video_s_type"] == stype:
            return profile
    return None


def _parse_vaux(data: bytes, start: int) -> dict:
    """Scans DIF blocks 1-5 of the first DIF sequence for VAUX packs 0x61
    (video control), 0x62 (date), 0x63 (time). Returns whatever of
    {date_time_original, aspect_ratio, video_scan_type} could be read —
    empty dict if the VAUX area wasn't reachable or carried none of these.
    """
    date = time = None
    is_16_9 = interlace = None
    pos = start

    for _ in range(1, 6):
        pos += 80
        if pos >= len(data):
            break
        block_type = data[pos]
        if (block_type & 0xF0) != 0x50:  # not a VAUX-type DIF block
            continue

        for j in range(15):
            p = pos + j * 5 + 3
            if p + 4 >= len(data):
                break
            pack_type = data[p]

            if pack_type == 0x61:  # video control
                apt = data[start + 4] & 0x07 if start + 4 < len(data) else 0
                t = data[p + 2]
                is_16_9 = (t & 0x07) == 0x02 or (not apt and (t & 0x07) == 0x07)
                interlace = bool(data[p + 3] & 0x10)
            elif pack_type == 0x62:  # date
                date_str = f"{data[p + 4]:02x}:{data[p + 3] & 0x1F:02x}:{data[p + 2] & 0x3F:02x}"
                if any(c in "abcdef" for c in date_str):
                    date = None  # a nibble outside 0-9 means this wasn't valid BCD after all
                else:
                    date = ("20" if date_str < "9" else "19") + date_str
                time = None
            elif pack_type == 0x63 and date:  # time (only trusted immediately after a date pack)
                time = f"{data[p + 4] & 0x3F:02x}:{data[p + 3] & 0x7F:02x}:{data[p + 2] & 0x7F:02x}"
                break
            else:
                time = None  # date/time packs must be consecutive to be trusted

    fields: dict = {}
    if date and time:
        fields["date_time_original"] = f"{date} {time}"
        if is_16_9 is not None:
            fields["aspect_ratio"] = "16:9" if is_16_9 else "4:3"
            fields["video_scan_type"] = "Interlaced" if interlace else "Progressive"
    return fields


def _parse_aaux(data: bytes, start: int) -> dict:
    """Reads the audio source pack (type 0x50) at its fixed offset into the
    Audio Auxiliary area of the first DIF sequence. Returns {} if that
    offset isn't reachable or isn't actually an audio source pack."""
    pos = start + 80 * 6 + 80 * 16 * 3 + 3
    if pos + 4 >= len(data) or data[pos] != 0x50:
        return {}

    freq = (data[pos + 4] >> 3) & 0x07
    stype = data[pos + 3] & 0x1F
    quant = data[pos + 4] & 0x07

    fields: dict = {}
    if freq < 3:
        fields["audio_sample_rate"] = _AUDIO_SAMPLE_RATE[freq]
    if stype < 3:
        if stype == 0 and quant and freq == 2:
            stype = 2
        fields["audio_channels"] = _AUDIO_CHANNELS[stype]
    fields["audio_bits_per_sample"] = 12 if quant else 16
    return fields


def parse(data: bytes, file_size: int | None = None) -> dict:
    """Locates the DIF grid, matches it against the known DV format
    profiles, and reads whatever VAUX/AAUX metadata packs are present.
    `file_size` (defaults to len(data)) is used only to estimate Duration
    from the matched profile's byte rate — pass the real on-disk size if
    `data` is a truncated read. Raises DvParseError only if the sync
    signature or minimal profile-identifying bytes can't be found; every
    field past that point is best-effort and bounds-checked, never raising.
    """
    start = dv_walker.find_dif_start(data)
    if start is None:
        raise DvParseError("no DV DIF sync signature found")

    if start + 80 * 5 + 48 + 3 >= len(data):
        raise DvParseError("DIF grid too short to determine format profile")

    dsf = (data[start + 3] & 0x80) >> 7
    stype = data[start + 80 * 5 + 48 + 3] & 0x1F
    special_case = dsf == 1 and stype == 0 and start + 4 < len(data) and bool(data[start + 4] & 0x07)

    profile = _match_profile(dsf, stype, special_case)
    if profile is None:
        return {"error": f"unrecognized DV profile (DSF={dsf}, VideoSType=0x{stype:x})"}

    fields: dict = {
        "image_width": profile["image_width"],
        "image_height": profile["image_height"],
        "video_format": profile["video_format"],
        "colorimetry": profile["colorimetry"],
        "frame_rate": round(profile["frame_rate"], 3),
    }

    byte_rate = profile["frame_size"] * profile["frame_rate"]
    fields["total_bitrate"] = 8 * byte_rate
    size = file_size if file_size is not None else len(data)
    if byte_rate:
        fields["duration"] = size / byte_rate

    fields.update(_parse_vaux(data, start))
    fields.update(_parse_aaux(data, start))

    return fields

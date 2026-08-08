from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class CodecOption:
    """A single tunable exposed by a specific ffmpeg encoder.

    `ffmpeg_flag` is the literal option name accepted by ffmpeg for this
    encoder (e.g. `compression_level`, `application`, `joint_stereo`) as
    documented in archive/docs/ffmpeg-manuals/ffmpeg-codecs/8-audio-encoders/.
    """

    key: str
    label: str
    kind: str  # "choice" | "int" | "float" | "bool"
    ffmpeg_flag: str
    choices: Optional[list] = None
    value_range: Optional[tuple] = None
    default: Optional[object] = None
    description: str = ""


@dataclass(frozen=True)
class AudioFormatCapability:
    id: str
    label: str
    extension: str
    encoder: str
    encoder_label: str
    lossless: bool
    manual_source: str
    sample_rates: Optional[list[int]] = None
    default_sample_rate: Optional[int] = None
    bit_depths: Optional[list[int]] = None
    default_bit_depth: Optional[int] = None
    bitrates_kbps: Optional[list[int]] = None
    default_bitrate_kbps: Optional[int] = None
    vbr_quality_range: Optional[tuple] = None
    default_vbr_quality: Optional[float] = None
    max_channels: Optional[int] = None
    notes: str = ""
    codec_options: list = field(default_factory=list)


_COMMON_SAMPLE_RATES = [8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000, 88200, 96000]
_LOSSY_BITRATE_LADDER = [32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]

_PCM_FORMAT_IDS = {"wav", "aiff"}
_PCM_CODECS = {
    ("wav", 16): "pcm_s16le",
    ("wav", 24): "pcm_s24le",
    ("wav", 32): "pcm_s32le",
    ("aiff", 16): "pcm_s16be",
    ("aiff", 24): "pcm_s24be",
    ("aiff", 32): "pcm_s32be",
}
_LOSSLESS_SAMPLE_FMT = {
    ("flac", 16): "s16",
    ("flac", 24): "s32",
    ("flac", 32): "s32",
    ("wavpack", 16): "s16",
    ("wavpack", 24): "s32",
    ("wavpack", 32): "s32",
}


AUDIO_FORMATS: dict[str, AudioFormatCapability] = {
    "mp3": AudioFormatCapability(
        id="mp3",
        label="MP3 (MPEG Audio Layer 3)",
        extension="mp3",
        encoder="libmp3lame",
        encoder_label="LAME MP3",
        lossless=False,
        manual_source="ffmpeg-codecs/8-audio-encoders/libmp3lame.md",
        sample_rates=[8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000],
        default_sample_rate=44100,
        bitrates_kbps=_LOSSY_BITRATE_LADDER,
        default_bitrate_kbps=192,
        vbr_quality_range=(0, 9),
        default_vbr_quality=4,
        max_channels=2,
        codec_options=[
            CodecOption("compression_level", "Algorithm Quality", "int", "compression_level",
                        value_range=(0, 9), default=2,
                        description="0 = highest quality/slowest, 9 = fastest/worst quality."),
            CodecOption("joint_stereo", "Joint Stereo", "bool", "joint_stereo", default=True),
            CodecOption("cutoff", "Lowpass Cutoff (Hz)", "int", "cutoff", value_range=(0, 20000), default=0),
        ],
    ),
    "ogg": AudioFormatCapability(
        id="ogg",
        label="Ogg Vorbis",
        extension="ogg",
        encoder="libvorbis",
        encoder_label="libvorbis",
        lossless=False,
        manual_source="ffmpeg-codecs/8-audio-encoders/libvorbis.md",
        sample_rates=_COMMON_SAMPLE_RATES,
        default_sample_rate=44100,
        bitrates_kbps=_LOSSY_BITRATE_LADDER,
        default_bitrate_kbps=192,
        vbr_quality_range=(-1.0, 10.0),
        default_vbr_quality=3.0,
        codec_options=[
            CodecOption("cutoff", "Lowpass Cutoff (Hz)", "int", "cutoff", value_range=(0, 20000), default=0),
            CodecOption("minrate", "Min Bitrate (kbps)", "int", "minrate", value_range=(0, 5000), default=0),
            CodecOption("maxrate", "Max Bitrate (kbps)", "int", "maxrate", value_range=(0, 5000), default=0),
        ],
    ),
    "opus": AudioFormatCapability(
        id="opus",
        label="Opus",
        extension="opus",
        encoder="libopus",
        encoder_label="libopus",
        lossless=False,
        manual_source="ffmpeg-codecs/8-audio-encoders/libopus.md",
        sample_rates=[8000, 12000, 16000, 24000, 48000],
        default_sample_rate=48000,
        bitrates_kbps=[16, 24, 32, 48, 64, 96, 128, 160, 192, 256, 320, 510],
        default_bitrate_kbps=128,
        codec_options=[
            CodecOption("vbr", "VBR Mode", "choice", "vbr",
                        choices=["off", "on", "constrained"], default="on"),
            CodecOption("compression_level", "Encoding Complexity", "int", "compression_level",
                        value_range=(0, 10), default=10),
            CodecOption("application", "Application", "choice", "application",
                        choices=["voip", "audio", "lowdelay"], default="audio"),
            CodecOption("frame_duration", "Frame Duration (ms)", "choice", "frame_duration",
                        choices=[2.5, 5, 10, 20, 40, 60], default=20),
            CodecOption("packet_loss", "Expected Packet Loss %", "int", "packet_loss",
                        value_range=(0, 100), default=0),
        ],
    ),
    "aac": AudioFormatCapability(
        id="aac",
        label="AAC (raw)",
        extension="aac",
        encoder="aac",
        encoder_label="Native AAC",
        lossless=False,
        manual_source="ffmpeg-codecs/8-audio-encoders/aac.md",
        sample_rates=_COMMON_SAMPLE_RATES,
        default_sample_rate=44100,
        bitrates_kbps=_LOSSY_BITRATE_LADDER,
        default_bitrate_kbps=128,
        codec_options=[
            CodecOption("profile", "Profile", "choice", "profile",
                        choices=["aac_low", "mpeg2_aac_low", "aac_ltp"], default="aac_low"),
            CodecOption("aac_coder", "Coding Method", "choice", "aac_coder",
                        choices=["twoloop", "anmr", "fast"], default="twoloop"),
            CodecOption("cutoff", "Cutoff Frequency (Hz)", "int", "cutoff", value_range=(0, 20000), default=0),
        ],
    ),
    "m4a": AudioFormatCapability(
        id="m4a",
        label="M4A / MPEG-4 Audio (AAC in MP4 container)",
        extension="m4a",
        encoder="aac",
        encoder_label="Native AAC",
        lossless=False,
        manual_source="ffmpeg-codecs/8-audio-encoders/aac.md",
        sample_rates=_COMMON_SAMPLE_RATES,
        default_sample_rate=44100,
        bitrates_kbps=_LOSSY_BITRATE_LADDER,
        default_bitrate_kbps=128,
        codec_options=[
            CodecOption("profile", "Profile", "choice", "profile",
                        choices=["aac_low", "mpeg2_aac_low", "aac_ltp"], default="aac_low"),
            CodecOption("aac_coder", "Coding Method", "choice", "aac_coder",
                        choices=["twoloop", "anmr", "fast"], default="twoloop"),
        ],
    ),
    "flac": AudioFormatCapability(
        id="flac",
        label="FLAC (Free Lossless Audio Codec)",
        extension="flac",
        encoder="flac",
        encoder_label="Native FLAC",
        lossless=True,
        manual_source="ffmpeg-codecs/8-audio-encoders/flac.md",
        sample_rates=_COMMON_SAMPLE_RATES,
        default_sample_rate=44100,
        bit_depths=[16, 24, 32],
        default_bit_depth=16,
        codec_options=[
            CodecOption("compression_level", "Compression Level", "int", "compression_level",
                        value_range=(0, 12), default=5),
            CodecOption("lpc_type", "LPC Algorithm", "choice", "lpc_type",
                        choices=["none", "fixed", "levinson", "cholesky"], default="levinson"),
            CodecOption("ch_mode", "Channel Mode", "choice", "ch_mode",
                        choices=["auto", "indep", "left_side", "right_side", "mid_side"], default="auto"),
        ],
    ),
    "wav": AudioFormatCapability(
        id="wav",
        label="WAV (Waveform Audio File Format, PCM)",
        extension="wav",
        encoder="pcm_s16le",
        encoder_label="PCM",
        lossless=True,
        manual_source="ffmpeg-codecs/2-codec-options.md",
        sample_rates=_COMMON_SAMPLE_RATES,
        default_sample_rate=44100,
        bit_depths=[16, 24, 32],
        default_bit_depth=16,
    ),
    "aiff": AudioFormatCapability(
        id="aiff",
        label="AIFF (Audio Interchange File Format, PCM)",
        extension="aiff",
        encoder="pcm_s16be",
        encoder_label="PCM",
        lossless=True,
        manual_source="ffmpeg-codecs/2-codec-options.md",
        sample_rates=_COMMON_SAMPLE_RATES,
        default_sample_rate=44100,
        bit_depths=[16, 24, 32],
        default_bit_depth=16,
    ),
    "wma": AudioFormatCapability(
        id="wma",
        label="WMA (Windows Media Audio v2)",
        extension="wma",
        encoder="wmav2",
        encoder_label="Native WMA v2",
        lossless=False,
        manual_source="ffmpeg general codec knowledge (no dedicated manual page vendored)",
        sample_rates=[8000, 11025, 16000, 22050, 32000, 44100, 48000],
        default_sample_rate=44100,
        bitrates_kbps=[48, 64, 96, 128, 160, 192, 256, 320],
        default_bitrate_kbps=128,
        max_channels=2,
    ),
    "ac3": AudioFormatCapability(
        id="ac3",
        label="AC-3 (Dolby Digital)",
        extension="ac3",
        encoder="ac3",
        encoder_label="Native AC-3",
        lossless=False,
        manual_source="ffmpeg-codecs/8-audio-encoders/ac3-and-ac3-fixed.md",
        sample_rates=[32000, 44100, 48000],
        default_sample_rate=48000,
        bitrates_kbps=[64, 96, 128, 160, 192, 224, 256, 320, 384, 448, 512, 576, 640],
        default_bitrate_kbps=192,
        max_channels=6,
        codec_options=[
            CodecOption("cutoff", "Lowpass Cutoff (Hz)", "int", "cutoff", value_range=(0, 20000), default=0),
            CodecOption("dialnorm", "Dialogue Normalization (dB)", "int", "dialnorm",
                        value_range=(-31, -1), default=-31),
        ],
    ),
    "wavpack": AudioFormatCapability(
        id="wavpack",
        label="WavPack (lossless)",
        extension="wv",
        encoder="wavpack",
        encoder_label="Native WavPack",
        lossless=True,
        manual_source="ffmpeg-codecs/8-audio-encoders/wavpack.md",
        sample_rates=_COMMON_SAMPLE_RATES,
        default_sample_rate=44100,
        bit_depths=[16, 24, 32],
        default_bit_depth=16,
        codec_options=[
            CodecOption("compression_level", "Compression Level", "choice", "compression_level",
                        choices=[0, 1, 2, 3], default=1,
                        description="0=fast, 1=normal, 2=high, 3=very high."),
            CodecOption("joint_stereo", "Joint Stereo", "choice", "joint_stereo",
                        choices=["on", "off", "auto"], default="auto"),
        ],
    ),
    "mp2": AudioFormatCapability(
        id="mp2",
        label="MP2 (MPEG Audio Layer 2)",
        extension="mp2",
        encoder="libtwolame",
        encoder_label="TwoLAME MP2",
        lossless=False,
        manual_source="ffmpeg-codecs/8-audio-encoders/libtwolame.md",
        sample_rates=[16000, 22050, 24000, 32000, 44100, 48000],
        default_sample_rate=44100,
        bitrates_kbps=[32, 48, 64, 96, 128, 160, 192, 224, 256, 320, 384],
        default_bitrate_kbps=192,
        vbr_quality_range=(-50, 50),
        codec_options=[
            CodecOption("mode", "Channel Mode", "choice", "mode",
                        choices=["auto", "stereo", "joint_stereo", "dual_channel", "mono"], default="auto"),
        ],
    ),
    "amr": AudioFormatCapability(
        id="amr",
        label="AMR-NB (Adaptive Multi-Rate Narrowband)",
        extension="amr",
        encoder="libopencore_amrnb",
        encoder_label="OpenCORE AMR-NB",
        lossless=False,
        manual_source="ffmpeg-codecs/8-audio-encoders/libopencore-amrnb.md",
        sample_rates=[8000],
        default_sample_rate=8000,
        bitrates_kbps=[4.75, 5.15, 5.9, 6.7, 7.4, 7.95, 10.2, 12.2],
        default_bitrate_kbps=12.2,
        max_channels=1,
        notes="Mono-only, 8000Hz-only encoder unless `strict` is relaxed.",
        codec_options=[
            CodecOption("dtx", "Discontinuous Transmission", "bool", "dtx", default=False),
        ],
    ),
    "alac": AudioFormatCapability(
        id="alac",
        label="ALAC (Apple Lossless, in M4A container)",
        extension="m4a",
        encoder="alac",
        encoder_label="Native ALAC",
        lossless=True,
        manual_source="ffmpeg general codec knowledge (no dedicated manual page vendored)",
        sample_rates=_COMMON_SAMPLE_RATES,
        default_sample_rate=44100,
        bit_depths=[16, 24, 32],
        default_bit_depth=16,
        codec_options=[
            CodecOption("compression_level", "Compression Level", "int", "compression_level",
                        value_range=(0, 2), default=2),
        ],
    ),
}


def get_format_ids() -> list[str]:
    return list(AUDIO_FORMATS.keys())


def get_format(format_id: str) -> AudioFormatCapability:
    return AUDIO_FORMATS[format_id]


def resolve_pcm_codec(format_id: str, bit_depth: int) -> str:
    return _PCM_CODECS.get((format_id, bit_depth), _PCM_CODECS.get((format_id, 16)))


def resolve_lossless_sample_fmt(format_id: str, bit_depth: int) -> Optional[str]:
    return _LOSSLESS_SAMPLE_FMT.get((format_id, bit_depth))


def build_ffmpeg_output_options(
    format_id: str,
    *,
    sample_rate: Optional[int] = None,
    bit_depth: Optional[int] = None,
    bitrate_kbps: Optional[float] = None,
    vbr_quality: Optional[float] = None,
    codec_option_values: Optional[dict] = None,
) -> dict:
    """Build the kwargs dict to pass to `media_core.ffmpeg`'s `.output(url, **options)`."""

    fmt = get_format(format_id)
    options: dict = {}

    if fmt.id in _PCM_FORMAT_IDS:
        options["c:a"] = resolve_pcm_codec(fmt.id, bit_depth or fmt.default_bit_depth)
    else:
        options["c:a"] = fmt.encoder

    resolved_rate = sample_rate or fmt.default_sample_rate
    if resolved_rate:
        options["ar"] = resolved_rate

    if fmt.bitrates_kbps and fmt.id not in _PCM_FORMAT_IDS:
        if bitrate_kbps is not None:
            options["b:a"] = f"{bitrate_kbps}k"
        elif vbr_quality is not None and fmt.vbr_quality_range:
            options["q:a"] = vbr_quality
        elif fmt.default_bitrate_kbps is not None:
            options["b:a"] = f"{fmt.default_bitrate_kbps}k"

    if fmt.lossless and fmt.id not in _PCM_FORMAT_IDS and fmt.bit_depths:
        sample_fmt = resolve_lossless_sample_fmt(fmt.id, bit_depth or fmt.default_bit_depth)
        if sample_fmt:
            options["sample_fmt"] = sample_fmt

    if codec_option_values:
        for option in fmt.codec_options:
            if option.key in codec_option_values and codec_option_values[option.key] is not None:
                options[option.ffmpeg_flag] = codec_option_values[option.key]

    return options


VIDEO_FORMATS: dict[str, str] = {
    "MP4 (H.264)": "libx264",
    "MKV (H.264)": "libx264",
    "WEBM (VP9)": "libvpx-vp9",
    "AVI (MPEG-4)": "mpeg4",
    "MOV (H.264)": "libx264",
}

_VIDEO_CONTAINERS: dict[str, str] = {
    "MP4 (H.264)": ".mp4",
    "MKV (H.264)": ".mkv",
    "WEBM (VP9)": ".webm",
    "AVI (MPEG-4)": ".avi",
    "MOV (H.264)": ".mov",
}


def get_video_formats_map() -> dict[str, str]:
    return VIDEO_FORMATS


def get_container_from_format(format_label: str) -> str:
    return _VIDEO_CONTAINERS.get(format_label, "")

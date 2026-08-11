from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Type

from .mpv_audio_filter import (
    MPVAudioFilter,
    MPVEchoFilter,
    MPVReverbFilter,
    MPVConvolutionReverbFilter,
    MPVLowPassFilter,
    MPVHighPassFilter,
    MPVBandPassFilter,
    MPVBandRejectFilter,
    MPVBassFilter,
    MPVTrebleFilter,
    MPVTiltShelfFilter,
    MPVCompressorFilter,
    MPVLimiterFilter,
    MPVGateFilter,
    MPVDynamicNormalizerFilter,
    MPVSpeechNormalizerFilter,
    MPVCompandFilter,
    MPVDeesserFilter,
    MPVFlangerFilter,
    MPVChorusFilter,
    MPVTremoloFilter,
    MPVVibratoFilter,
    MPVPulsatorFilter,
    MPVPhaserFilter,
    MPVPitchShiftFilter,
    MPVTempoScaleFilter,
    MPVExtraStereoFilter,
    MPVStereoWidenFilter,
    MPVStereoToolsFilter,
    MPVHaasFilter,
    MPVBS2BFilter,
    MPVCrossfeedFilter,
    MPVEarwaxFilter,
    MPVDenoiseFFTFilter,
    MPVDenoiseNLMFilter,
    MPVCrystalizerFilter,
    MPVExciterFilter,
    MPVEqualizerFilter,
)

_MANUAL_DIR = "archive/docs/ffmpeg-manuals/ffmpeg-filters/8-audio-filters"


@dataclass(frozen=True)
class MPVEffectParam:
    key: str
    label: str
    kind: str  # "int" | "float" | "choice" | "bool" | "file"
    default: object
    value_range: Optional[tuple] = None
    choices: Optional[list] = None
    suffix: str = ""


@dataclass(frozen=True)
class MPVEffectDefinition:
    id: str
    label: str
    category: str
    manual_source: str
    filter_class: Type[MPVAudioFilter]
    params: list = field(default_factory=list)


def _p(key, label, kind, default, value_range=None, choices=None, suffix="") -> MPVEffectParam:
    return MPVEffectParam(key, label, kind, default, value_range, choices, suffix)


_BOOL_STR = ["true", "false"]

MPV_EFFECTS: list[MPVEffectDefinition] = [
    MPVEffectDefinition(
        id="echo", label="Echo", category="Time-Based", manual_source=f"{_MANUAL_DIR}/aecho.md",
        filter_class=MPVEchoFilter, params=[
            _p("in_gain", "Input Gain", "float", 0.6, (0.0, 1.0)),
            _p("out_gain", "Output Gain", "float", 0.3, (0.0, 1.0)),
            _p("delays", "Delays (ms, pipe-separated)", "text", "1000"),
            _p("decays", "Decays (pipe-separated)", "text", "0.5"),
        ],
    ),
    MPVEffectDefinition(
        id="reverb", label="Reverb (Simple)", category="Reverb", manual_source=f"{_MANUAL_DIR}/aecho.md",
        filter_class=MPVReverbFilter, params=[
            _p("in_gain", "Input Gain", "float", 0.8, (0.0, 1.0)),
            _p("out_gain", "Output Gain", "float", 0.6, (0.0, 1.0)),
            _p("decay", "Decay", "float", 0.4, (0.0, 0.95)),
            _p("room_size", "Room Size", "float", 1.0, (0.2, 5.0)),
        ],
    ),
    MPVEffectDefinition(
        id="convolution_reverb", label="Convolution Reverb", category="Reverb",
        manual_source=f"{_MANUAL_DIR}/afir.md", filter_class=MPVConvolutionReverbFilter, params=[
            _p("impulse_response_path", "Impulse Response File", "file", ""),
            _p("dry", "Dry Level", "float", 1.0, (0.0, 1.0)),
            _p("wet", "Wet Level", "float", 1.0, (0.0, 1.0)),
        ],
    ),
    MPVEffectDefinition(
        id="lowpass", label="Low Pass", category="Tone", manual_source=f"{_MANUAL_DIR}/lowpass.md",
        filter_class=MPVLowPassFilter, params=[
            _p("frequency", "Frequency", "float", 500.0, (20.0, 20000.0), suffix=" Hz"),
            _p("poles", "Poles", "int", 2, (1, 2)),
            _p("width", "Width", "float", 0.707, (0.1, 10.0)),
            _p("mix", "Mix", "float", 1.0, (0.0, 1.0)),
        ],
    ),
    MPVEffectDefinition(
        id="highpass", label="High Pass", category="Tone", manual_source=f"{_MANUAL_DIR}/highpass.md",
        filter_class=MPVHighPassFilter, params=[
            _p("frequency", "Frequency", "float", 3000.0, (20.0, 20000.0), suffix=" Hz"),
            _p("poles", "Poles", "int", 2, (1, 2)),
            _p("width", "Width", "float", 0.707, (0.1, 10.0)),
            _p("mix", "Mix", "float", 1.0, (0.0, 1.0)),
        ],
    ),
    MPVEffectDefinition(
        id="bandpass", label="Band Pass", category="Tone", manual_source=f"{_MANUAL_DIR}/bandpass.md",
        filter_class=MPVBandPassFilter, params=[
            _p("frequency", "Frequency", "float", 3000.0, (20.0, 20000.0), suffix=" Hz"),
            _p("width", "Width", "float", 100.0, (0.1, 10000.0)),
            _p("csg", "Constant Skirt Gain", "int", 0, (0, 1)),
            _p("mix", "Mix", "float", 1.0, (0.0, 1.0)),
            _p("width_type", "Width Type", "choice", "h", choices=["h", "q", "o", "s", "k"]),
        ],
    ),
    MPVEffectDefinition(
        id="bandreject", label="Band Reject", category="Tone", manual_source=f"{_MANUAL_DIR}/bandreject.md",
        filter_class=MPVBandRejectFilter, params=[
            _p("frequency", "Frequency", "float", 3000.0, (20.0, 20000.0), suffix=" Hz"),
            _p("width_type", "Width Type", "choice", "h", choices=["h", "q", "o", "s", "k"]),
            _p("width", "Width", "float", 100.0, (0.1, 10000.0)),
            _p("mix", "Mix", "float", 1.0, (0.0, 1.0)),
        ],
    ),
    MPVEffectDefinition(
        id="bass", label="Bass (Shelf)", category="Tone", manual_source=f"{_MANUAL_DIR}/bass.md",
        filter_class=MPVBassFilter, params=[
            _p("gain", "Gain", "float", 0.0, (-20.0, 20.0), suffix=" dB"),
            _p("frequency", "Frequency", "float", 100.0, (20.0, 20000.0), suffix=" Hz"),
            _p("width_type", "Width Type", "choice", "q", choices=["h", "q", "o", "s", "k"]),
            _p("width", "Width", "float", 0.5, (0.1, 10000.0)),
            _p("poles", "Poles", "int", 2, (1, 2)),
            _p("mix", "Mix", "float", 1.0, (0.0, 1.0)),
        ],
    ),
    MPVEffectDefinition(
        id="treble", label="Treble (Shelf)", category="Tone", manual_source=f"{_MANUAL_DIR}/treble.md",
        filter_class=MPVTrebleFilter, params=[
            _p("gain", "Gain", "float", 0.0, (-20.0, 20.0), suffix=" dB"),
            _p("frequency", "Frequency", "float", 3000.0, (20.0, 20000.0), suffix=" Hz"),
            _p("width_type", "Width Type", "choice", "q", choices=["h", "q", "o", "s", "k"]),
            _p("width", "Width", "float", 0.5, (0.1, 10000.0)),
            _p("poles", "Poles", "int", 2, (1, 2)),
            _p("mix", "Mix", "float", 1.0, (0.0, 1.0)),
        ],
    ),
    MPVEffectDefinition(
        id="tiltshelf", label="Tilt Shelf", category="Tone", manual_source=f"{_MANUAL_DIR}/tiltshelf.md",
        filter_class=MPVTiltShelfFilter, params=[
            _p("gain", "Gain", "float", 0.0, (-20.0, 20.0), suffix=" dB"),
            _p("frequency", "Frequency", "float", 3000.0, (20.0, 20000.0), suffix=" Hz"),
            _p("width_type", "Width Type", "choice", "q", choices=["h", "q", "o", "s", "k"]),
            _p("width", "Width", "float", 0.5, (0.1, 10000.0)),
            _p("poles", "Poles", "int", 2, (1, 2)),
            _p("mix", "Mix", "float", 1.0, (0.0, 1.0)),
        ],
    ),
    MPVEffectDefinition(
        id="compressor", label="Compressor", category="Dynamics", manual_source=f"{_MANUAL_DIR}/acompressor.md",
        filter_class=MPVCompressorFilter, params=[
            _p("level_in", "Input Level", "float", 1.0, (0.015625, 64.0)),
            _p("threshold", "Threshold", "float", 0.125, (0.00097563, 1.0)),
            _p("ratio", "Ratio", "float", 2.0, (1.0, 20.0)),
            _p("attack", "Attack (ms)", "float", 20.0, (0.01, 2000.0)),
            _p("release", "Release (ms)", "float", 250.0, (0.01, 9000.0)),
            _p("makeup", "Makeup Gain", "float", 1.0, (1.0, 64.0)),
            _p("knee", "Knee", "float", 2.82843, (1.0, 8.0)),
            _p("detection", "Detection", "choice", "rms", choices=["peak", "rms"]),
            _p("mix", "Mix", "float", 1.0, (0.0, 1.0)),
        ],
    ),
    MPVEffectDefinition(
        id="limiter", label="Limiter", category="Dynamics", manual_source=f"{_MANUAL_DIR}/alimiter.md",
        filter_class=MPVLimiterFilter, params=[
            _p("level_in", "Input Level", "float", 1.0, (0.0, 64.0)),
            _p("level_out", "Output Level", "float", 1.0, (0.0, 64.0)),
            _p("limit", "Limit", "float", 1.0, (0.0, 1.0)),
            _p("attack", "Attack (ms)", "float", 5.0, (0.1, 1000.0)),
            _p("release", "Release (ms)", "float", 50.0, (1.0, 9000.0)),
            _p("asc", "Auto Release", "choice", "false", choices=_BOOL_STR),
            _p("asc_level", "Auto Release Level", "float", 0.5, (0.0, 1.0)),
            _p("level", "Auto Leveling", "choice", "true", choices=_BOOL_STR),
        ],
    ),
    MPVEffectDefinition(
        id="gate", label="Gate", category="Dynamics", manual_source=f"{_MANUAL_DIR}/agate.md",
        filter_class=MPVGateFilter, params=[
            _p("level_in", "Input Level", "float", 1.0, (0.015625, 64.0)),
            _p("mode", "Mode", "choice", "downward", choices=["downward", "upward"]),
            _p("range", "Range", "float", 0.06125, (0.0, 1.0)),
            _p("threshold", "Threshold", "float", 0.125, (0.0, 1.0)),
            _p("ratio", "Ratio", "float", 2.0, (1.0, 9000.0)),
            _p("attack", "Attack (ms)", "float", 20.0, (0.01, 9000.0)),
            _p("release", "Release (ms)", "float", 250.0, (0.01, 9000.0)),
            _p("makeup", "Makeup Gain", "float", 1.0, (1.0, 64.0)),
            _p("knee", "Knee", "float", 2.828427125, (1.0, 8.0)),
            _p("detection", "Detection", "choice", "rms", choices=["peak", "rms"]),
            _p("link", "Link", "choice", "average", choices=["average", "maximum"]),
        ],
    ),
    MPVEffectDefinition(
        id="dynaudnorm", label="Dynamic Normalizer", category="Dynamics", manual_source=f"{_MANUAL_DIR}/dynaudnorm.md",
        filter_class=MPVDynamicNormalizerFilter, params=[
            _p("framelen", "Frame Length (ms)", "int", 500, (10, 8000)),
            _p("gausssize", "Gaussian Window", "int", 31, (3, 301)),
            _p("peak", "Target Peak", "float", 0.95, (0.0, 1.0)),
            _p("maxgain", "Max Gain", "float", 10.0, (1.0, 100.0)),
            _p("targetrms", "Target RMS", "float", 0.0, (0.0, 1.0)),
            _p("compress", "Compress Factor", "float", 0.0, (0.0, 30.0)),
        ],
    ),
    MPVEffectDefinition(
        id="speechnorm", label="Speech Normalizer", category="Dynamics", manual_source=f"{_MANUAL_DIR}/speechnorm.md",
        filter_class=MPVSpeechNormalizerFilter, params=[
            _p("peak", "Target Peak", "float", 0.95, (0.0, 1.0)),
            _p("expansion", "Expansion", "float", 2.0, (1.0, 50.0)),
            _p("compression", "Compression", "float", 2.0, (1.0, 50.0)),
            _p("threshold", "Threshold", "float", 0.0, (0.0, 1.0)),
            _p("raise", "Raise Rate", "float", 0.001, (0.0, 1.0)),
            _p("fall", "Fall Rate", "float", 0.001, (0.0, 1.0)),
        ],
    ),
    MPVEffectDefinition(
        id="compand", label="Compand", category="Dynamics", manual_source=f"{_MANUAL_DIR}/compand.md",
        filter_class=MPVCompandFilter, params=[
            _p("attacks", "Attack (s)", "float", 0.3, (0.0, 2.0)),
            _p("decays", "Decay (s)", "float", 0.8, (0.0, 2.0)),
            _p("points", "Transfer Points", "text", "-70/-70|-60/-20|-20/-20|0/-6"),
            _p("soft-knee", "Soft Knee", "float", 0.01, (0.0, 10.0)),
            _p("gain", "Gain", "float", 0.0, (-20.0, 20.0), suffix=" dB"),
        ],
    ),
    MPVEffectDefinition(
        id="deesser", label="De-esser", category="Dynamics", manual_source=f"{_MANUAL_DIR}/deesser.md",
        filter_class=MPVDeesserFilter, params=[
            _p("i", "Intensity", "float", 0.0, (0.0, 1.0)),
            _p("m", "Ducking Amount", "float", 0.5, (0.0, 1.0)),
            _p("f", "Frequency Keep", "float", 0.5, (0.0, 1.0)),
            _p("s", "Output Mode", "choice", "o", choices=["i", "o", "e"]),
        ],
    ),
    MPVEffectDefinition(
        id="flanger", label="Flanger", category="Modulation", manual_source=f"{_MANUAL_DIR}/flanger.md",
        filter_class=MPVFlangerFilter, params=[
            _p("delay", "Delay (ms)", "float", 0.0, (0.0, 30.0)),
            _p("depth", "Depth", "float", 2.0, (0.0, 10.0)),
            _p("regen", "Regeneration", "float", 0.0, (-95.0, 95.0)),
            _p("width", "Width", "float", 71.0, (0.0, 100.0)),
            _p("speed", "Speed (Hz)", "float", 0.5, (0.1, 10.0)),
            _p("shape", "Shape", "choice", "sinusoidal", choices=["sinusoidal", "triangular"]),
            _p("phase", "Phase", "float", 25.0, (0.0, 100.0)),
            _p("interp", "Interpolation", "choice", "linear", choices=["linear", "quadratic"]),
        ],
    ),
    MPVEffectDefinition(
        id="chorus", label="Chorus", category="Modulation", manual_source=f"{_MANUAL_DIR}/chorus.md",
        filter_class=MPVChorusFilter, params=[
            _p("in_gain", "Input Gain", "float", 0.4, (0.0, 1.0)),
            _p("out_gain", "Output Gain", "float", 0.4, (0.0, 1.0)),
            _p("delays", "Delays (ms, pipe-separated)", "text", "55"),
            _p("decays", "Decays (pipe-separated)", "text", "0.4"),
            _p("speeds", "Speeds (Hz, pipe-separated)", "text", "0.25"),
            _p("depths", "Depths (ms, pipe-separated)", "text", "2"),
        ],
    ),
    MPVEffectDefinition(
        id="tremolo", label="Tremolo", category="Modulation", manual_source=f"{_MANUAL_DIR}/tremolo.md",
        filter_class=MPVTremoloFilter, params=[
            _p("f", "Frequency", "float", 5.0, (0.1, 20000.0), suffix=" Hz"),
            _p("d", "Depth", "float", 0.5, (0.0, 1.0)),
        ],
    ),
    MPVEffectDefinition(
        id="vibrato", label="Vibrato", category="Modulation", manual_source=f"{_MANUAL_DIR}/vibrato.md",
        filter_class=MPVVibratoFilter, params=[
            _p("f", "Frequency", "float", 5.0, (0.1, 20000.0), suffix=" Hz"),
            _p("d", "Depth", "float", 0.5, (0.0, 1.0)),
        ],
    ),
    MPVEffectDefinition(
        id="pulsator", label="Pulsator", category="Modulation", manual_source=f"{_MANUAL_DIR}/apulsator.md",
        filter_class=MPVPulsatorFilter, params=[
            _p("level_in", "Input Level", "float", 1.0, (0.015625, 64.0)),
            _p("level_out", "Output Level", "float", 1.0, (0.015625, 64.0)),
            _p("mode", "Waveform", "choice", "sine", choices=["sine", "triangle", "square", "sawup", "sawdown"]),
            _p("amount", "Amount", "float", 1.0, (0.0, 1.0)),
            _p("offset_l", "Left Offset", "float", 0.0, (0.0, 1.0)),
            _p("offset_r", "Right Offset", "float", 0.5, (0.0, 1.0)),
            _p("width", "Pulse Width", "float", 1.0, (0.0, 2.0)),
            _p("hz", "Rate", "float", 2.0, (0.01, 100.0), suffix=" Hz"),
        ],
    ),
    MPVEffectDefinition(
        id="phaser", label="Phaser", category="Modulation", manual_source=f"{_MANUAL_DIR}/aphaser.md",
        filter_class=MPVPhaserFilter, params=[
            _p("in_gain", "Input Gain", "float", 0.4, (0.0, 1.0)),
            _p("out_gain", "Output Gain", "float", 0.74, (0.0, 4.0)),
            _p("delay", "Delay (ms)", "float", 3.0, (0.0, 5.0)),
            _p("decay", "Decay", "float", 0.4, (0.0, 0.99)),
            _p("speed", "Speed (Hz)", "float", 0.5, (0.1, 10.0)),
            _p("type", "Modulation Type", "choice", "triangular", choices=["triangular", "sinusoidal"]),
        ],
    ),
    MPVEffectDefinition(
        id="pitch_shift", label="Pitch Shift", category="Pitch", manual_source=f"{_MANUAL_DIR}/rubberband.md",
        filter_class=MPVPitchShiftFilter, params=[
            _p("pitch-scale", "Pitch Scale", "float", 1.0, (0.1, 100.0)),
            _p("engine", "Engine", "choice", "finer", choices=["faster", "finer"]),
        ],
    ),
    MPVEffectDefinition(
        id="tempo_scale", label="Tempo Scale", category="Time-Based", manual_source="mpv manual (scaletempo, native)",
        filter_class=MPVTempoScaleFilter, params=[
            _p("scale", "Scale", "int", 1, (1, 25)),
            _p("speed", "Speed Mode", "choice", "none", choices=["pitch", "none"]),
        ],
    ),
    MPVEffectDefinition(
        id="extrastereo", label="Extra Stereo", category="Spatial", manual_source=f"{_MANUAL_DIR}/extrastereo.md",
        filter_class=MPVExtraStereoFilter, params=[
            _p("m", "Difference Coefficient", "float", 2.5, (-10.0, 10.0)),
            _p("c", "Clipping", "choice", "true", choices=_BOOL_STR),
        ],
    ),
    MPVEffectDefinition(
        id="stereowiden", label="Stereo Widen", category="Spatial", manual_source=f"{_MANUAL_DIR}/stereowiden.md",
        filter_class=MPVStereoWidenFilter, params=[
            _p("delay", "Delay (ms)", "float", 20.0, (0.0, 100.0)),
            _p("feedback", "Feedback", "float", 0.3, (0.0, 0.9)),
            _p("crossfeed", "Crossfeed", "float", 0.3, (0.0, 0.8)),
            _p("drymix", "Dry Mix", "float", 0.8, (0.0, 1.0)),
        ],
    ),
    MPVEffectDefinition(
        id="stereotools", label="Stereo Tools", category="Spatial", manual_source=f"{_MANUAL_DIR}/stereotools.md",
        filter_class=MPVStereoToolsFilter, params=[
            _p("level_in", "Input Level", "float", 1.0, (0.015625, 64.0)),
            _p("level_out", "Output Level", "float", 1.0, (0.015625, 64.0)),
            _p("balance_in", "Input Balance", "float", 0.0, (-1.0, 1.0)),
            _p("balance_out", "Output Balance", "float", 0.0, (-1.0, 1.0)),
            _p("mode", "Mode", "choice", "lr>lr", choices=[
                "lr>lr", "lr>ms", "ms>lr", "lr>ll", "lr>rr", "lr>l+r", "lr>rl",
                "ms>ll", "ms>rr", "ms>rl", "lr>l-r",
            ]),
            _p("base", "Stereo Base", "float", 0.0, (-1.0, 1.0)),
            _p("phase", "Phase (deg)", "float", 0.0, (0.0, 360.0)),
        ],
    ),
    MPVEffectDefinition(
        id="haas", label="Haas", category="Spatial", manual_source=f"{_MANUAL_DIR}/haas.md",
        filter_class=MPVHaasFilter, params=[
            _p("level_in", "Input Level", "float", 1.0, (0.0, 2.0)),
            _p("level_out", "Output Level", "float", 1.0, (0.0, 2.0)),
            _p("side_gain", "Side Gain", "float", 1.0, (0.0, 2.0)),
            _p("middle_source", "Middle Source", "choice", "mid", choices=["left", "right", "mid", "side"]),
            _p("left_delay", "Left Delay (ms)", "float", 2.05, (0.0, 40.0)),
            _p("right_delay", "Right Delay (ms)", "float", 2.12, (0.0, 40.0)),
        ],
    ),
    MPVEffectDefinition(
        id="bs2b", label="Binaural (bs2b)", category="Spatial", manual_source=f"{_MANUAL_DIR}/bs2b.md",
        filter_class=MPVBS2BFilter, params=[
            _p("profile", "Profile", "choice", "default", choices=["default", "cmoy", "jmeier"]),
            _p("fcut", "Cut Frequency (Hz)", "int", 700, (300, 2000)),
            _p("feed", "Feed Level", "int", 50, (10, 150)),
        ],
    ),
    MPVEffectDefinition(
        id="crossfeed", label="Crossfeed", category="Spatial", manual_source=f"{_MANUAL_DIR}/crossfeed.md",
        filter_class=MPVCrossfeedFilter, params=[
            _p("strength", "Strength", "float", 0.2, (0.0, 1.0)),
            _p("range", "Soundstage Width", "float", 0.5, (0.0, 1.0)),
            _p("slope", "Slope", "float", 0.5, (0.01, 1.0)),
            _p("level_in", "Input Level", "float", 0.9, (0.0, 2.0)),
            _p("level_out", "Output Level", "float", 1.0, (0.0, 2.0)),
        ],
    ),
    MPVEffectDefinition(
        id="earwax", label="Earwax", category="Spatial", manual_source=f"{_MANUAL_DIR}/earwax.md",
        filter_class=MPVEarwaxFilter, params=[],
    ),
    MPVEffectDefinition(
        id="denoise_fft", label="Noise Reduction (FFT)", category="Noise Reduction",
        manual_source=f"{_MANUAL_DIR}/afftdn.md", filter_class=MPVDenoiseFFTFilter, params=[
            _p("nr", "Noise Reduction", "float", 12.0, (0.01, 97.0), suffix=" dB"),
            _p("nf", "Noise Floor", "float", -50.0, (-80.0, -20.0), suffix=" dB"),
            _p("nt", "Noise Type", "choice", "white", choices=["white", "vinyl", "shellac", "custom"]),
            _p("tn", "Track Noise Floor", "choice", "false", choices=_BOOL_STR),
        ],
    ),
    MPVEffectDefinition(
        id="denoise_nlm", label="Noise Reduction (NLM)", category="Noise Reduction",
        manual_source=f"{_MANUAL_DIR}/anlmdn.md", filter_class=MPVDenoiseNLMFilter, params=[
            _p("s", "Strength", "float", 0.00001, (0.00001, 10000.0)),
            _p("p", "Patch Radius (ms)", "float", 2.0, (1.0, 100.0)),
            _p("r", "Research Radius (ms)", "float", 6.0, (2.0, 300.0)),
            _p("m", "Smooth Factor", "float", 11.0, (1.0, 1000.0)),
        ],
    ),
    MPVEffectDefinition(
        id="crystalizer", label="Crystalizer", category="Character", manual_source=f"{_MANUAL_DIR}/crystalizer.md",
        filter_class=MPVCrystalizerFilter, params=[
            _p("i", "Intensity", "float", 2.0, (-10.0, 10.0)),
            _p("c", "Clipping", "choice", "true", choices=_BOOL_STR),
        ],
    ),
    MPVEffectDefinition(
        id="exciter", label="Exciter", category="Character", manual_source=f"{_MANUAL_DIR}/aexciter.md",
        filter_class=MPVExciterFilter, params=[
            _p("level_in", "Input Level", "float", 1.0, (0.0, 64.0)),
            _p("level_out", "Output Level", "float", 1.0, (0.0, 64.0)),
            _p("amount", "Amount", "float", 1.0, (0.0, 64.0)),
            _p("drive", "Drive", "float", 8.5, (0.1, 10.0)),
            _p("blend", "Blend (Octave)", "float", 0.0, (-10.0, 10.0)),
            _p("freq", "Lower Frequency Limit", "float", 7500.0, (2000.0, 12000.0), suffix=" Hz"),
            _p("ceil", "Upper Frequency Limit", "float", 9999.0, (9999.0, 20000.0), suffix=" Hz"),
        ],
    ),
    MPVEffectDefinition(
        id="equalizer", label="Equalizer", category="EQ", manual_source=f"{_MANUAL_DIR}/equalizer.md",
        filter_class=MPVEqualizerFilter, params=[
            _p("preamp", "Preamp", "float", 0.0, (-20.0, 20.0), suffix=" dB"),
        ] + [
            _p(f"band_{i}", f"Band {i}", "float", 0.0, (-20.0, 20.0), suffix=" dB")
            for i in range(len(MPVEqualizerFilter.BAND_FREQUENCIES))
        ],
    ),
]

MPV_EFFECTS_BY_ID: dict[str, MPVEffectDefinition] = {effect.id: effect for effect in MPV_EFFECTS}


def get_mpv_effect(effect_id: str) -> Optional[MPVEffectDefinition]:
    return MPV_EFFECTS_BY_ID.get(effect_id)


def categories() -> list[str]:
    seen: list[str] = []
    for effect in MPV_EFFECTS:
        if effect.category not in seen:
            seen.append(effect.category)
    return seen


def effects_for_category(category: str) -> list[MPVEffectDefinition]:
    return [effect for effect in MPV_EFFECTS if effect.category == category]

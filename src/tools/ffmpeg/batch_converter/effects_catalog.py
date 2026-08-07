from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass(frozen=True)
class EffectParam:
    key: str
    label: str
    kind: str  # "int" | "float" | "choice" | "bool" | "time" | "file"
    default: object
    value_range: Optional[tuple] = None
    choices: Optional[list] = None
    suffix: str = ""


@dataclass(frozen=True)
class EffectDefinition:
    id: str
    label: str
    branch: str  # "edits" | "filters"
    category: str
    manual_source: str
    params: list = field(default_factory=list)
    build_filter: Optional[Callable[[dict], str]] = None
    needs_secondary_input: bool = False
    needs_analysis_pass: Optional[str] = None  # "max_volume" | "mean_volume" | None


def _fmt(value) -> str:
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def _volume_filter(values: dict) -> str:
    mode = values.get("mode", "increase")
    amount = values.get("amount", 0)
    if mode == "multiply":
        return f"volume={_fmt(amount)}"
    sign = "+" if mode == "increase" else "-"
    return f"volume={sign}{_fmt(abs(amount))}dB"


def _fade_filter(values: dict) -> str:
    direction = values.get("direction", "in")
    start = values.get("start_time", 0)
    duration = values.get("duration", 3)
    return f"afade=type={direction}:start_time={_fmt(start)}:duration={_fmt(duration)}"


def _trim_filter(values: dict) -> str:
    parts = []
    if values.get("start_time") not in (None, ""):
        parts.append(f"start={_fmt(values['start_time'])}")
    if values.get("end_time") not in (None, ""):
        parts.append(f"end={_fmt(values['end_time'])}")
    elif values.get("duration") not in (None, ""):
        parts.append(f"duration={_fmt(values['duration'])}")
    return f"atrim={':'.join(parts)},asetpts=PTS-STARTPTS"


def _silence_leading_filter(values: dict) -> str:
    return (f"silenceremove=start_periods=1:start_duration={_fmt(values.get('min_duration', 0.1))}"
            f":start_threshold={_fmt(values.get('threshold_db', -50))}dB")


def _silence_trailing_filter(values: dict) -> str:
    return (f"silenceremove=stop_periods=1:stop_duration={_fmt(values.get('min_duration', 0.1))}"
            f":stop_threshold={_fmt(values.get('threshold_db', -50))}dB")


def _silence_all_filter(values: dict) -> str:
    duration_seconds = _fmt(values.get("min_duration_ms", 500) / 1000)
    return (f"silenceremove=stop_periods=-1:stop_duration={duration_seconds}"
            f":stop_threshold={_fmt(values.get('threshold_db', -50))}dB")


def _silence_custom_filter(values: dict) -> str:
    return (f"silenceremove=start_periods={_fmt(values.get('start_periods', 1))}"
            f":start_duration={_fmt(values.get('start_duration', 0.1))}"
            f":start_threshold={_fmt(values.get('start_threshold_db', -50))}dB"
            f":stop_periods={_fmt(values.get('stop_periods', -1))}"
            f":stop_duration={_fmt(values.get('stop_duration', 0.1))}"
            f":stop_threshold={_fmt(values.get('stop_threshold_db', -50))}dB")


def _loudnorm_filter(values: dict) -> str:
    return (f"loudnorm=I={_fmt(values.get('integrated_lufs', -24))}"
            f":LRA={_fmt(values.get('loudness_range', 7))}"
            f":TP={_fmt(values.get('true_peak_db', -2))}")


def _simple_eq_filter(values: dict) -> str:
    bands = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
    stages = []
    for band in bands:
        gain = values.get(f"band_{band}", 0)
        if gain:
            stages.append(f"equalizer=f={band}:t=q:w=1:g={_fmt(gain)}")
    return ",".join(stages) if stages else "anull"


def _parametric_eq_filter(values: dict) -> str:
    stages = []
    for i in range(1, 4):
        gain = values.get(f"band{i}_gain", 0)
        if not gain:
            continue
        freq = values.get(f"band{i}_freq", 1000)
        q = values.get(f"band{i}_q", 1.0)
        stages.append(f"equalizer=f={_fmt(freq)}:t=q:w={_fmt(q)}:g={_fmt(gain)}")
    return ",".join(stages) if stages else "anull"


def _expander_filter(values: dict) -> str:
    threshold = values.get("threshold_db", -30)
    ratio = values.get("ratio", 2.0)
    probe = threshold - 10
    expanded = threshold + (probe - threshold) * ratio
    return f"compand=attacks=0.05:decays=0.2:points=-90/-90|{_fmt(probe)}/{_fmt(expanded)}|{_fmt(threshold)}/{_fmt(threshold)}|0/0"


def _pitch_only_filter(values: dict) -> str:
    factor = values.get("factor", 1.0)
    source_rate = values.get("_source_sample_rate", 44100)
    target_rate = int(round(source_rate * factor))
    inverse_tempo = 1.0 / factor if factor else 1.0
    return f"asetrate={target_rate},aresample={source_rate},atempo={_fmt(round(inverse_tempo, 6))}"


def _speed_only_filter(values: dict) -> str:
    factor = values.get("factor", 1.0)
    stages = []
    remaining = factor
    while remaining > 2.0:
        stages.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        stages.append("atempo=0.5")
        remaining /= 0.5
    stages.append(f"atempo={_fmt(round(remaining, 6))}")
    return ",".join(stages)


def _reverb_simple_filter(values: dict) -> str:
    size = values.get("room_size", 0.5)
    decay = values.get("decay", 0.5)
    stages = []
    for i, base_delay in enumerate((500, 900, 1400), start=1):
        delay = int(base_delay * (0.5 + size))
        stages.append(f"aecho=0.8:0.88:{delay}:{_fmt(round(decay * (1.0 - i * 0.15), 3))}")
    return ",".join(stages)


EFFECTS: list = [
    EffectDefinition(
        id="normalize_peak", label="Normalize Peak", branch="edits", category="Loudness",
        manual_source="ffmpeg-filters/8-audio-filters/volumedetect.md + volume.md",
        needs_analysis_pass="max_volume",
        params=[EffectParam("target_db", "Target Peak (dBFS)", "float", -1.0, value_range=(-24.0, 0.0))],
        build_filter=lambda values: f"volume={_fmt(values.get('target_db', -1.0) - values.get('_measured_db', 0.0))}dB",
    ),
    EffectDefinition(
        id="normalize_rms", label="Normalize RMS", branch="edits", category="Loudness",
        manual_source="ffmpeg-filters/8-audio-filters/volumedetect.md + volume.md",
        needs_analysis_pass="mean_volume",
        params=[EffectParam("target_db", "Target RMS (dBFS)", "float", -20.0, value_range=(-40.0, 0.0))],
        build_filter=lambda values: f"volume={_fmt(values.get('target_db', -20.0) - values.get('_measured_db', 0.0))}dB",
    ),
    EffectDefinition(
        id="loudnorm", label="EBU R128 Loudness (loudnorm)", branch="edits", category="Loudness",
        manual_source="ffmpeg-filters/8-audio-filters/loudnorm.md",
        params=[
            EffectParam("integrated_lufs", "Integrated Loudness (LUFS)", "float", -24.0, value_range=(-70.0, -5.0)),
            EffectParam("loudness_range", "Loudness Range (LRA)", "float", 7.0, value_range=(1.0, 50.0)),
            EffectParam("true_peak_db", "Max True Peak (dBTP)", "float", -2.0, value_range=(-9.0, 0.0)),
        ],
        build_filter=_loudnorm_filter,
    ),
    EffectDefinition(
        id="replaygain", label="ReplayGain (analyze + apply)", branch="edits", category="Loudness",
        manual_source="ffmpeg-filters/8-audio-filters/replaygain.md",
        needs_analysis_pass="track_gain",
        params=[],
        build_filter=lambda values: f"volume={_fmt(values.get('_measured_db', 0.0))}dB",
    ),
    EffectDefinition(
        id="volume", label="Volume (Increase / Decrease / Multiply)", branch="edits", category="Volume",
        manual_source="ffmpeg-filters/8-audio-filters/volume.md",
        params=[
            EffectParam("mode", "Mode", "choice", "increase", choices=["increase", "decrease", "multiply"]),
            EffectParam("amount", "Amount (dB or factor)", "float", 3.0, value_range=(0.0, 60.0)),
        ],
        build_filter=_volume_filter,
    ),
    EffectDefinition(
        id="silence_leading", label="Remove Leading Silence", branch="edits", category="Silence",
        manual_source="ffmpeg-filters/8-audio-filters/silenceremove.md",
        params=[
            EffectParam("threshold_db", "Silence Threshold (dB)", "float", -50.0, value_range=(-90.0, 0.0)),
            EffectParam("min_duration", "Min Silence Duration (s)", "float", 0.1, value_range=(0.0, 10.0)),
        ],
        build_filter=_silence_leading_filter,
    ),
    EffectDefinition(
        id="silence_trailing", label="Remove Trailing Silence", branch="edits", category="Silence",
        manual_source="ffmpeg-filters/8-audio-filters/silenceremove.md",
        params=[
            EffectParam("threshold_db", "Silence Threshold (dB)", "float", -50.0, value_range=(-90.0, 0.0)),
            EffectParam("min_duration", "Min Silence Duration (s)", "float", 0.1, value_range=(0.0, 10.0)),
        ],
        build_filter=_silence_trailing_filter,
    ),
    EffectDefinition(
        id="silence_all", label="Remove All Silence Longer Than X ms", branch="edits", category="Silence",
        manual_source="ffmpeg-filters/8-audio-filters/silenceremove.md",
        params=[
            EffectParam("threshold_db", "Silence Threshold (dB)", "float", -50.0, value_range=(-90.0, 0.0)),
            EffectParam("min_duration_ms", "Min Silence Duration (ms)", "int", 500, value_range=(0, 60000)),
        ],
        build_filter=_silence_all_filter,
    ),
    EffectDefinition(
        id="silence_custom", label="Trim Silence Below Threshold (Advanced)", branch="edits", category="Silence",
        manual_source="ffmpeg-filters/8-audio-filters/silenceremove.md",
        params=[
            EffectParam("start_periods", "Start Periods", "int", 1, value_range=(0, 10)),
            EffectParam("start_duration", "Start Duration (s)", "float", 0.1, value_range=(0.0, 10.0)),
            EffectParam("start_threshold_db", "Start Threshold (dB)", "float", -50.0, value_range=(-90.0, 0.0)),
            EffectParam("stop_periods", "Stop Periods (-1 = all)", "int", -1, value_range=(-10, 10)),
            EffectParam("stop_duration", "Stop Duration (s)", "float", 0.1, value_range=(0.0, 10.0)),
            EffectParam("stop_threshold_db", "Stop Threshold (dB)", "float", -50.0, value_range=(-90.0, 0.0)),
        ],
        build_filter=_silence_custom_filter,
    ),
    EffectDefinition(
        id="fade_in", label="Fade In", branch="edits", category="Fade",
        manual_source="ffmpeg-filters/8-audio-filters/afade.md",
        params=[EffectParam("duration", "Duration (s)", "float", 3.0, value_range=(0.0, 60.0))],
        build_filter=lambda values: _fade_filter({**values, "direction": "in", "start_time": 0}),
    ),
    EffectDefinition(
        id="fade_out", label="Fade Out", branch="edits", category="Fade",
        manual_source="ffmpeg-filters/8-audio-filters/afade.md",
        params=[
            EffectParam("start_time", "Start Time (s)", "float", 0.0, value_range=(0.0, 36000.0)),
            EffectParam("duration", "Duration (s)", "float", 3.0, value_range=(0.0, 60.0)),
        ],
        build_filter=lambda values: _fade_filter({**values, "direction": "out"}),
    ),
    EffectDefinition(
        id="trim", label="Trim (Start / End / Duration)", branch="edits", category="Trim",
        manual_source="ffmpeg-filters/8-audio-filters/atrim.md",
        params=[
            EffectParam("start_time", "Start Time (s)", "float", None, value_range=(0.0, 36000.0)),
            EffectParam("end_time", "End Time (s)", "float", None, value_range=(0.0, 36000.0)),
            EffectParam("duration", "Duration (s)", "float", None, value_range=(0.0, 36000.0)),
        ],
        build_filter=_trim_filter,
    ),
    EffectDefinition(
        id="reverse", label="Reverse Audio", branch="edits", category="Reverse",
        manual_source="ffmpeg-filters/8-audio-filters/areverse.md",
        params=[],
        build_filter=lambda values: "areverse",
    ),
    EffectDefinition(
        id="eq_simple", label="Simple EQ (10-Band)", branch="filters", category="EQ",
        manual_source="ffmpeg-filters/8-audio-filters/equalizer.md",
        params=[
            EffectParam(f"band_{band}", f"{band} Hz (dB)", "float", 0.0, value_range=(-12.0, 12.0))
            for band in (31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000)
        ],
        build_filter=_simple_eq_filter,
    ),
    EffectDefinition(
        id="eq_parametric", label="Parametric EQ (3-Band)", branch="filters", category="EQ",
        manual_source="ffmpeg-filters/8-audio-filters/equalizer.md",
        params=[
            param
            for i in range(1, 4)
            for param in (
                EffectParam(f"band{i}_freq", f"Band {i} Frequency (Hz)", "float", 1000.0 * i, value_range=(20.0, 20000.0)),
                EffectParam(f"band{i}_gain", f"Band {i} Gain (dB)", "float", 0.0, value_range=(-24.0, 24.0)),
                EffectParam(f"band{i}_q", f"Band {i} Q", "float", 1.0, value_range=(0.1, 10.0)),
            )
        ],
        build_filter=_parametric_eq_filter,
    ),
    EffectDefinition(
        id="highpass", label="High-Pass", branch="filters", category="EQ",
        manual_source="ffmpeg-filters/8-audio-filters/highpass.md",
        params=[
            EffectParam("frequency", "Cutoff Frequency (Hz)", "float", 200.0, value_range=(1.0, 20000.0)),
            EffectParam("poles", "Poles", "choice", 2, choices=[1, 2]),
        ],
        build_filter=lambda values: f"highpass=f={_fmt(values.get('frequency', 200))}:poles={_fmt(values.get('poles', 2))}",
    ),
    EffectDefinition(
        id="lowpass", label="Low-Pass", branch="filters", category="EQ",
        manual_source="ffmpeg-filters/8-audio-filters/lowpass.md",
        params=[
            EffectParam("frequency", "Cutoff Frequency (Hz)", "float", 8000.0, value_range=(1.0, 20000.0)),
            EffectParam("poles", "Poles", "choice", 2, choices=[1, 2]),
        ],
        build_filter=lambda values: f"lowpass=f={_fmt(values.get('frequency', 8000))}:poles={_fmt(values.get('poles', 2))}",
    ),
    EffectDefinition(
        id="bandpass", label="Band-Pass", branch="filters", category="EQ",
        manual_source="ffmpeg-filters/8-audio-filters/bandpass.md",
        params=[
            EffectParam("frequency", "Center Frequency (Hz)", "float", 1000.0, value_range=(1.0, 20000.0)),
            EffectParam("width", "Width (Q)", "float", 1.0, value_range=(0.1, 10.0)),
        ],
        build_filter=lambda values: f"bandpass=f={_fmt(values.get('frequency', 1000))}:width_type=q:w={_fmt(values.get('width', 1.0))}",
    ),
    EffectDefinition(
        id="notch", label="Notch (Band-Reject)", branch="filters", category="EQ",
        manual_source="ffmpeg-filters/8-audio-filters/bandreject.md",
        params=[
            EffectParam("frequency", "Center Frequency (Hz)", "float", 1000.0, value_range=(1.0, 20000.0)),
            EffectParam("width", "Width (Q)", "float", 1.0, value_range=(0.1, 10.0)),
        ],
        build_filter=lambda values: f"bandreject=f={_fmt(values.get('frequency', 1000))}:width_type=q:w={_fmt(values.get('width', 1.0))}",
    ),
    EffectDefinition(
        id="compressor", label="Compressor", branch="filters", category="Dynamics",
        manual_source="ffmpeg-filters/8-audio-filters/acompressor.md",
        params=[
            EffectParam("threshold_db", "Threshold (dB)", "float", -20.0, value_range=(-60.0, 0.0)),
            EffectParam("ratio", "Ratio", "float", 3.0, value_range=(1.0, 20.0)),
            EffectParam("attack_ms", "Attack (ms)", "float", 20.0, value_range=(0.01, 2000.0)),
            EffectParam("release_ms", "Release (ms)", "float", 250.0, value_range=(0.01, 9000.0)),
            EffectParam("makeup_db", "Makeup Gain (dB)", "float", 0.0, value_range=(0.0, 24.0)),
        ],
        build_filter=lambda values: (
            f"acompressor=threshold={_fmt(values.get('threshold_db', -20))}dB"
            f":ratio={_fmt(values.get('ratio', 3))}:attack={_fmt(values.get('attack_ms', 20))}"
            f":release={_fmt(values.get('release_ms', 250))}:makeup={_fmt(values.get('makeup_db', 0))}dB"
        ),
    ),
    EffectDefinition(
        id="limiter", label="Limiter", branch="filters", category="Dynamics",
        manual_source="ffmpeg-filters/8-audio-filters/alimiter.md",
        params=[
            EffectParam("limit_db", "Limit (dB)", "float", -1.0, value_range=(-30.0, 0.0)),
            EffectParam("attack_ms", "Attack (ms)", "float", 5.0, value_range=(0.1, 80.0)),
            EffectParam("release_ms", "Release (ms)", "float", 50.0, value_range=(1.0, 8000.0)),
        ],
        build_filter=lambda values: (
            f"alimiter=limit={_fmt(values.get('limit_db', -1))}dB"
            f":attack={_fmt(values.get('attack_ms', 5))}:release={_fmt(values.get('release_ms', 50))}"
        ),
    ),
    EffectDefinition(
        id="expander", label="Expander", branch="filters", category="Dynamics",
        manual_source="ffmpeg-filters/8-audio-filters/compand.md",
        params=[
            EffectParam("threshold_db", "Threshold (dB)", "float", -30.0, value_range=(-60.0, 0.0)),
            EffectParam("ratio", "Ratio", "float", 2.0, value_range=(1.0, 10.0)),
        ],
        build_filter=_expander_filter,
    ),
    EffectDefinition(
        id="noise_gate", label="Noise Gate", branch="filters", category="Dynamics",
        manual_source="ffmpeg-filters/8-audio-filters/agate.md",
        params=[
            EffectParam("threshold_db", "Threshold (dB)", "float", -40.0, value_range=(-80.0, 0.0)),
            EffectParam("ratio", "Ratio", "float", 2.0, value_range=(1.0, 20.0)),
            EffectParam("attack_ms", "Attack (ms)", "float", 20.0, value_range=(0.01, 9000.0)),
            EffectParam("release_ms", "Release (ms)", "float", 250.0, value_range=(0.01, 9000.0)),
            EffectParam("range_db", "Range (dB)", "float", -30.0, value_range=(-90.0, 0.0)),
        ],
        build_filter=lambda values: (
            f"agate=threshold={_fmt(values.get('threshold_db', -40))}dB:ratio={_fmt(values.get('ratio', 2))}"
            f":attack={_fmt(values.get('attack_ms', 20))}:release={_fmt(values.get('release_ms', 250))}"
            f":range={_fmt(values.get('range_db', -30))}dB"
        ),
    ),
    EffectDefinition(
        id="speed_no_pitch", label="Speed Without Pitch", branch="filters", category="Pitch",
        manual_source="ffmpeg-filters/8-audio-filters/atempo.md",
        params=[EffectParam("factor", "Speed Factor", "float", 1.0, value_range=(0.25, 4.0))],
        build_filter=_speed_only_filter,
    ),
    EffectDefinition(
        id="pitch_no_speed", label="Pitch Without Speed", branch="filters", category="Pitch",
        manual_source="ffmpeg-filters/8-audio-filters/rubberband.md (asetrate/atempo fallback used by default)",
        params=[EffectParam("factor", "Pitch Factor", "float", 1.0, value_range=(0.5, 2.0))],
        build_filter=_pitch_only_filter,
    ),
    EffectDefinition(
        id="delay", label="Delay", branch="filters", category="Time-Based",
        manual_source="ffmpeg-filters/8-audio-filters/adelay.md",
        params=[EffectParam("delay_ms", "Delay (ms)", "int", 200, value_range=(0, 10000))],
        build_filter=lambda values: f"adelay=delays={_fmt(values.get('delay_ms', 200))}:all=1",
    ),
    EffectDefinition(
        id="echo", label="Echo", branch="filters", category="Time-Based",
        manual_source="ffmpeg-filters/8-audio-filters/aecho.md",
        params=[
            EffectParam("in_gain", "Input Gain", "float", 0.8, value_range=(0.0, 1.0)),
            EffectParam("out_gain", "Output Gain", "float", 0.88, value_range=(0.0, 1.0)),
            EffectParam("delay_ms", "Delay (ms)", "int", 900, value_range=(0, 90000)),
            EffectParam("decay", "Decay", "float", 0.4, value_range=(0.0, 1.0)),
        ],
        build_filter=lambda values: (
            f"aecho={_fmt(values.get('in_gain', 0.8))}:{_fmt(values.get('out_gain', 0.88))}"
            f":{_fmt(values.get('delay_ms', 900))}:{_fmt(values.get('decay', 0.4))}"
        ),
    ),
    EffectDefinition(
        id="reverb_simple", label="Reverb (Algorithmic)", branch="filters", category="Time-Based",
        manual_source="ffmpeg-filters/8-audio-filters/aecho.md (chained approximation)",
        params=[
            EffectParam("room_size", "Room Size", "float", 0.5, value_range=(0.0, 1.0)),
            EffectParam("decay", "Decay", "float", 0.5, value_range=(0.0, 1.0)),
        ],
        build_filter=_reverb_simple_filter,
    ),
    EffectDefinition(
        id="chorus", label="Chorus", branch="filters", category="Time-Based",
        manual_source="ffmpeg-filters/8-audio-filters/chorus.md",
        params=[
            EffectParam("delay_ms", "Delay (ms)", "float", 40.0, value_range=(20.0, 100.0)),
            EffectParam("decay", "Decay", "float", 0.4, value_range=(0.0, 1.0)),
            EffectParam("speed", "Speed (Hz)", "float", 0.8, value_range=(0.1, 5.0)),
            EffectParam("depth", "Depth (ms)", "float", 2.0, value_range=(0.0, 10.0)),
        ],
        build_filter=lambda values: (
            f"chorus=0.7:0.9:{_fmt(values.get('delay_ms', 40))}:{_fmt(values.get('decay', 0.4))}"
            f":{_fmt(values.get('speed', 0.8))}:{_fmt(values.get('depth', 2.0))}"
        ),
    ),
    EffectDefinition(
        id="flanger", label="Flanger", branch="filters", category="Time-Based",
        manual_source="ffmpeg-filters/8-audio-filters/flanger.md",
        params=[
            EffectParam("delay_ms", "Delay (ms)", "float", 0.0, value_range=(0.0, 30.0)),
            EffectParam("depth_ms", "Depth (ms)", "float", 2.0, value_range=(0.0, 10.0)),
            EffectParam("speed", "Speed (Hz)", "float", 0.5, value_range=(0.1, 10.0)),
        ],
        build_filter=lambda values: (
            f"flanger=delay={_fmt(values.get('delay_ms', 0))}:depth={_fmt(values.get('depth_ms', 2))}"
            f":speed={_fmt(values.get('speed', 0.5))}"
        ),
    ),
    EffectDefinition(
        id="phaser", label="Phaser", branch="filters", category="Time-Based",
        manual_source="ffmpeg-filters/8-audio-filters/aphaser.md",
        params=[
            EffectParam("delay_ms", "Delay (ms)", "float", 3.0, value_range=(0.0, 5.0)),
            EffectParam("decay", "Decay", "float", 0.4, value_range=(0.0, 0.99)),
            EffectParam("speed", "Speed (Hz)", "float", 0.5, value_range=(0.1, 10.0)),
        ],
        build_filter=lambda values: (
            f"aphaser=in_gain=0.4:out_gain=0.74:delay={_fmt(values.get('delay_ms', 3))}"
            f":decay={_fmt(values.get('decay', 0.4))}:speed={_fmt(values.get('speed', 0.5))}"
        ),
    ),
    EffectDefinition(
        id="convolution_reverb", label="Convolution Reverb", branch="filters", category="Time-Based",
        manual_source="ffmpeg-filters/8-audio-filters/afir.md",
        needs_secondary_input=True,
        params=[
            EffectParam("impulse_response_path", "Impulse Response File", "file", ""),
            EffectParam("dry", "Dry Gain", "float", 1.0, value_range=(0.0, 10.0)),
            EffectParam("wet", "Wet Gain", "float", 1.0, value_range=(0.0, 10.0)),
        ],
        build_filter=lambda values: f"afir=dry={_fmt(values.get('dry', 1.0))}:wet={_fmt(values.get('wet', 1.0))}",
    ),
]

EFFECTS_BY_ID: dict = {effect.id: effect for effect in EFFECTS}


def get_effect(effect_id: str) -> EffectDefinition:
    return EFFECTS_BY_ID[effect_id]


def effects_for_branch(branch: str) -> list:
    return [effect for effect in EFFECTS if effect.branch == branch]


def categories_for_branch(branch: str) -> list:
    seen = []
    for effect in effects_for_branch(branch):
        if effect.category not in seen:
            seen.append(effect.category)
    return seen

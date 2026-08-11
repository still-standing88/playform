import os
from typing import Any, List, Optional
from .__AV_Common import *
from .audio_filter import AudioFilter


def escape_lavfi_path(path: str) -> str:
    """Escape a filesystem path for embedding inside an mpv `lavfi=[...]`
    filter-graph string (e.g. `amovie='<path>'`).

    ffmpeg's filtergraph parser treats `'`, `\\`, `:`, `,`, `[`, `]`, `;` as
    structural. Wrapping the whole path in single quotes and backslash-
    escaping any embedded `\\`/`'` is ffmpeg's own documented way to pass
    an arbitrary path through -- this matters here specifically because
    Windows paths carry both backslashes and a colon right after the drive
    letter (`C:\\...`), either of which breaks the graph parser unescaped.
    """
    escaped = path.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


class MPVAudioFilter(AVFilter):
    def __init__(self, filter_handle: str, parameters: dict[str, ParameterValue], backend_additional_info: dict[Any, Any]):
        super().__init__(AVFilterType.AV_TYPE_AUDIO, AVMediaBackend.AV_BACKEND_MPV, filter_handle, parameters, backend_additional_info)
        self._validate_parameters()
    
    def _validate_parameters(self):
        mpv_param_map = self.info.get("mpv_param_map", {})
        current_params = self.get_parameters()
        
        for param_name, param_value in current_params.items():
            if param_name in mpv_param_map:
                _, param_type, param_range = mpv_param_map[param_name]
                
                if not isinstance(param_value, param_type):
                    raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER_TYPE, 
                                f"Parameter {param_name} must be of type {param_type.__name__}")
                
                if param_range and param_type in [int, float]:
                    min_val, max_val = param_range[:2]
                    if not (min_val <= param_value <= max_val):
                        raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER_RANGE,
                                    f"Parameter {param_name} must be between {min_val} and {max_val}")
    
    def set_parameter(self, name: str, value: ParameterValue):
        mpv_param_map = self.info.get("mpv_param_map", {})
        if name in mpv_param_map:
            _, param_type, param_range = mpv_param_map[name]
            
            if not isinstance(value, param_type):
                raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER_TYPE,
                            f"Parameter {name} must be of type {param_type.__name__}")
            
            if param_range and param_type in [int, float]:
                min_val, max_val = param_range[:2]
                if not (min_val <= value <= max_val):
                    raise AVError(AVErrorInfo.INVALID_FILTER_PARAMETER_RANGE,
                                f"Parameter {name} must be between {min_val} and {max_val}")
        
        super().set_parameter(name, value)
    
    def construct(self) -> str:
        mpv_filter_name = self.info.get("mpv_filter_name", "")
        effect_syntax = self.info.get("effect_syntax", "lavfi")
        mpv_param_map = self.info.get("mpv_param_map", {})
        
        if not mpv_filter_name:
            return ""
        
        params = self.get_parameters()
        param_strings = []
        
        for param_name, param_value in params.items():
            if param_name in mpv_param_map:
                mpv_param_name, _, _ = mpv_param_map[param_name]
                param_strings.append(f"{mpv_param_name}={param_value}")
        
        param_string = ":".join(param_strings)
        
        if effect_syntax == "lavfi":
            if param_string:
                return f"lavfi=[{mpv_filter_name}={param_string}]"
            else:
                return f"lavfi=[{mpv_filter_name}]"
        elif effect_syntax == "@rb":
            if param_string:
                return f"@rb:{mpv_filter_name}={param_string}"
            else:
                return f"@rb:{mpv_filter_name}"
        else:
            if param_string:
                return f"{mpv_filter_name}={param_string}"
            else:
                return mpv_filter_name


class MPVEchoFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "in_gain": ("in_gain", float, (0.0, 1.0, 0.05, 0.6)),
            "out_gain": ("out_gain", float, (0.0, 1.0, 0.05, 0.3)),
            "delays": ("delays", str, ()),
            "decays": ("decays", str, ())
        }
        
        parameters = {
            "in_gain": 0.6,
            "out_gain": 0.3,
            "delays": "1000",
            "decays": "0.5"
        }
        
        backend_info = {
            "mpv_filter_name": "aecho",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Echo", parameters, backend_info)

class MPVReverbFilter(MPVAudioFilter):
    """Simulates reverb with a bank of closely-spaced aecho taps with
    decreasing decay. The obvious ffmpeg building block for reverb, afir,
    is a 2-input convolution filter (dry signal + a separate impulse-
    response stream) -- used single-input as originally written here, mpv
    refused to initialize it at all ("lavfi: exactly 2 pads required"),
    which killed the whole audio filter chain (not just this effect), so
    any other filter checked alongside Reverb appeared broken too."""

    _TAP_DELAYS_MS = [29, 37, 53, 67, 83, 101]

    def __init__(self):
        mpv_param_map = {
            "in_gain": ("in_gain", float, (0.0, 1.0, 0.05, 0.8)),
            "out_gain": ("out_gain", float, (0.0, 1.0, 0.05, 0.6)),
            "decay": ("decay", float, (0.0, 0.95, 0.05, 0.4)),
            "room_size": ("room_size", float, (0.2, 5.0, 0.1, 1.0)),
        }

        parameters = {
            "in_gain": 0.8,
            "out_gain": 0.6,
            "decay": 0.4,
            "room_size": 1.0,
        }

        backend_info = {
            "mpv_filter_name": "aecho",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }

        super().__init__("Reverb", parameters, backend_info)

    def construct(self) -> str:
        params = self.get_parameters()
        in_gain = params.get("in_gain", 0.8)
        out_gain = params.get("out_gain", 0.6)
        decay = params.get("decay", 0.4)
        room_size = params.get("room_size", 1.0)

        delays = [max(1, round(ms * room_size)) for ms in self._TAP_DELAYS_MS]
        decays = [round(decay * (0.9 ** i), 4) for i in range(len(self._TAP_DELAYS_MS))]

        delays_str = "|".join(str(d) for d in delays)
        decays_str = "|".join(str(d) for d in decays)
        return f"lavfi=[aecho=in_gain={in_gain}:out_gain={out_gain}:delays={delays_str}:decays={decays_str}]"

class MPVLowPassFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "frequency": ("frequency", float, (20.0, 20000.0, 10.0, 500.0)),
            "poles": ("poles", int, (1, 2, 1, 2)),
            "width": ("width", float, (0.1, 10.0, 0.1, 0.707)),
            "mix": ("mix", float, (0.0, 1.0, 0.1, 1.0))
        }
        
        parameters = {
            "frequency": 500.0,
            "poles": 2,
            "width": 0.707,
            "mix": 1.0
        }
        
        backend_info = {
            "mpv_filter_name": "lowpass",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Low Pass", parameters, backend_info)

class MPVHighPassFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "frequency": ("frequency", float, (20.0, 20000.0, 10.0, 3000.0)),
            "poles": ("poles", int, (1, 2, 1, 2)),
            "width": ("width", float, (0.1, 10.0, 0.1, 0.707)),
            "mix": ("mix", float, (0.0, 1.0, 0.1, 1.0))
        }
        
        parameters = {
            "frequency": 3000.0,
            "poles": 2,
            "width": 0.707,
            "mix": 1.0
        }
        
        backend_info = {
            "mpv_filter_name": "highpass",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("High Pass", parameters, backend_info)

class MPVCompressorFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "level_in": ("level_in", float, (0.015625, 64.0, 0.1, 1.0)),
            "threshold": ("threshold", float, (0.00097563, 1.0, 0.01, 0.125)),
            "ratio": ("ratio", float, (1.0, 20.0, 0.1, 2.0)),
            "attack": ("attack", float, (0.01, 2000.0, 1.0, 20.0)),
            "release": ("release", float, (0.01, 9000.0, 1.0, 250.0)),
            "makeup": ("makeup", float, (1.0, 64.0, 0.1, 1.0)),
            "knee": ("knee", float, (1.0, 8.0, 0.1, 2.82843)),
            "detection": ("detection", str, ()),
            "mix": ("mix", float, (0.0, 1.0, 0.1, 1.0))
        }
        
        parameters = {
            "level_in": 1.0,
            "threshold": 0.125,
            "ratio": 2.0,
            "attack": 20.0,
            "release": 250.0,
            "makeup": 1.0,
            "knee": 2.82843,
            "detection": "rms",
            "mix": 1.0
        }
        
        backend_info = {
            "mpv_filter_name": "acompressor",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Compressor", parameters, backend_info)

class MPVFlangerFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "delay": ("delay", float, (0.0, 30.0, 0.1, 0.0)),
            "depth": ("depth", float, (0.0, 10.0, 0.1, 2.0)),
            "regen": ("regen", float, (-95.0, 95.0, 1.0, 0.0)),
            "width": ("width", float, (0.0, 100.0, 1.0, 71.0)),
            "speed": ("speed", float, (0.1, 10.0, 0.1, 0.5)),
            "shape": ("shape", str, ()),
            "phase": ("phase", float, (0.0, 100.0, 1.0, 25.0)),
            "interp": ("interp", str, ())
        }
        
        parameters = {
            "delay": 0.0,
            "depth": 2.0,
            "regen": 0.0,
            "width": 71.0,
            "speed": 0.5,
            "shape": "sinusoidal",
            "phase": 25.0,
            "interp": "linear"
        }
        
        backend_info = {
            "mpv_filter_name": "flanger",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Flanger", parameters, backend_info)

class MPVChorusFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "in_gain": ("in_gain", float, (0.0, 1.0, 0.05, 0.4)),
            "out_gain": ("out_gain", float, (0.0, 1.0, 0.05, 0.4)),
            "delays": ("delays", str, ()),
            "decays": ("decays", str, ()),
            "speeds": ("speeds", str, ()),
            "depths": ("depths", str, ())
        }
        
        parameters = {
            "in_gain": 0.4,
            "out_gain": 0.4,
            "delays": "55",
            "decays": "0.4",
            "speeds": "0.25",
            "depths": "2"
        }
        
        backend_info = {
            "mpv_filter_name": "chorus",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Chorus", parameters, backend_info)

class MPVPitchShiftFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "pitch-scale": ("pitch-scale", float, (1.0, 100.0, 1.0, 1.0)),
            "engine": ("engine", str, ("faster", "finer"))
        }
        
        parameters = {
            "pitch-scale": 1.0,
            "engine": "finer"
        }
        
        backend_info = {
            "mpv_filter_name": "rubberband",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "@rb:"
        }
        
        super().__init__("Pitch Shift", parameters, backend_info)

class MPVTempoScaleFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "scale": ("scale", int, (1, 25, 1, 1)),
            "speed": ("speed", str, ("pitch", "none"))
        }
        
        parameters = {
            "scale": 1,
            "speed": "none"
        }
        
        backend_info = {
            "mpv_filter_name": "scaletempo",
            "mpv_param_map": mpv_param_map,
            # scaletempo is a native mpv audio filter, not an ffmpeg/lavfi
            # one -- construct() defaults effect_syntax to "lavfi" when
            # absent, which wrapped it as lavfi=[scaletempo=...]. mpv then
            # tried to resolve "scaletempo" as an ffmpeg filter name inside
            # that graph and failed ("No such filter: 'scaletempo'"),
            # which failed the *entire* audio filter chain, not just this
            # effect (verified empirically). Any non-lavfi/@rb value here
            # makes construct() emit the plain native filter syntax instead.
            "effect_syntax": "native",
        }

        super().__init__("Tempo Scale", parameters, backend_info)

class MPVLimiterFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "level_in": ("level_in", float, (0.0, 64.0, 0.1, 1.0)),
            "level_out": ("level_out", float, (0.0, 64.0, 0.1, 1.0)),
            "limit": ("limit", float, (0.0, 1.0, 0.01, 1.0)),
            "attack": ("attack", float, (0.1, 1000.0, 0.1, 5.0)),
            "release": ("release", float, (1.0, 9000.0, 1.0, 50.0)),
            "asc": ("asc", str, ()),
            "asc_level": ("asc_level", float, (0.0, 1.0, 0.1, 0.5)),
            "level": ("level", str, ())
        }
        
        parameters = {
            "level_in": 1.0,
            "level_out": 1.0,
            "limit": 1.0,
            "attack": 5.0,
            "release": 50.0,
            "asc": "false",
            "asc_level": 0.5,
            "level": "true"
        }
        
        backend_info = {
            "mpv_filter_name": "alimiter",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Limiter", parameters, backend_info)

class MPVBandPassFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "frequency": ("frequency", float, (20.0, 20000.0, 10.0, 3000.0)),
            "width": ("width", float, (0.1, 1000.0, 0.1, 100.0)),
            "csg": ("csg", int, (0, 1, 1, 0)),
            "mix": ("mix", float, (0.0, 1.0, 0.1, 1.0)),
            "width_type": ("width_type", str, ())
        }
        
        parameters = {
            "frequency": 3000.0,
            "width": 100.0,
            "csg": 0,
            "mix": 1.0,
            "width_type": "h"
        }
        
        backend_info = {
            "mpv_filter_name": "bandpass",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Band Pass", parameters, backend_info)

class MPVGateFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "level_in": ("level_in", float, (0.015625, 64.0, 0.1, 1.0)),
            "mode": ("mode", str, ()),
            "range": ("range", float, (0.0, 1.0, 0.01, 0.06125)),
            "threshold": ("threshold", float, (0.0, 1.0, 0.01, 0.125)),
            "ratio": ("ratio", float, (1.0, 9000.0, 0.1, 2.0)),
            "attack": ("attack", float, (0.01, 9000.0, 1.0, 20.0)),
            "release": ("release", float, (0.01, 9000.0, 1.0, 250.0)),
            "makeup": ("makeup", float, (1.0, 64.0, 0.1, 1.0)),
            "knee": ("knee", float, (1.0, 8.0, 0.1, 2.828427125)),
            "detection": ("detection", str, ()),
            "link": ("link", str, ())
        }
        
        parameters = {
            "level_in": 1.0,
            "mode": "downward",
            "range": 0.06125,
            "threshold": 0.125,
            "ratio": 2.0,
            "attack": 20.0,
            "release": 250.0,
            "makeup": 1.0,
            "knee": 2.828427125,
            "detection": "rms",
            "link": "average"
        }
        
        backend_info = {
            "mpv_filter_name": "agate",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }

        super().__init__("Gate", parameters, backend_info)


class MPVEqualizerFilter(MPVAudioFilter):
    """10-band graphic equalizer built from chained ffmpeg `equalizer` nodes,
    at the standard ISO/Winamp band frequencies, so existing preset data and
    UI (band count/frequencies) carry over as-is."""

    BAND_FREQUENCIES = [60.0, 170.0, 310.0, 600.0, 1000.0, 3000.0, 6000.0, 12000.0, 14000.0, 16000.0]

    def __init__(self, band_amps: Optional[List[float]] = None, preamp: float = 0.0):
        mpv_param_map = {"preamp": ("preamp", float, (-20.0, 20.0, 0.5, 0.0))}
        for i in range(len(self.BAND_FREQUENCIES)):
            mpv_param_map[f"band_{i}"] = (f"band_{i}", float, (-20.0, 20.0, 0.5, 0.0))

        amps = list(band_amps) if band_amps else [0.0] * len(self.BAND_FREQUENCIES)
        parameters: dict = {"preamp": preamp}
        for i, amp in enumerate(amps):
            parameters[f"band_{i}"] = float(amp)

        backend_info = {
            "mpv_filter_name": "equalizer",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }

        super().__init__("Equalizer", parameters, backend_info)

    def construct(self) -> str:
        params = self.get_parameters()
        preamp = params.get("preamp", 0.0)
        stages = [f"volume={preamp}dB"] if preamp else []
        for i, freq in enumerate(self.BAND_FREQUENCIES):
            gain = params.get(f"band_{i}", 0.0)
            stages.append(f"equalizer=f={freq}:width_type=o:w=1:g={gain}")
        return f"lavfi=[{','.join(stages)}]" if stages else ""

    def set_band(self, index: int, amp: float):
        if 0 <= index < len(self.BAND_FREQUENCIES):
            self.set_parameter(f"band_{index}", float(amp))

    def set_preamp(self, preamp: float):
        self.set_parameter("preamp", float(preamp))


class MPVTremoloFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "f": ("f", float, (0.1, 20000.0, 0.1, 5.0)),
            "d": ("d", float, (0.0, 1.0, 0.05, 0.5)),
        }
        parameters = {"f": 5.0, "d": 0.5}
        backend_info = {"mpv_filter_name": "tremolo", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Tremolo", parameters, backend_info)


class MPVVibratoFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "f": ("f", float, (0.1, 20000.0, 0.1, 5.0)),
            "d": ("d", float, (0.0, 1.0, 0.05, 0.5)),
        }
        parameters = {"f": 5.0, "d": 0.5}
        backend_info = {"mpv_filter_name": "vibrato", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Vibrato", parameters, backend_info)


class MPVPulsatorFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "level_in": ("level_in", float, (0.015625, 64.0, 0.1, 1.0)),
            "level_out": ("level_out", float, (0.015625, 64.0, 0.1, 1.0)),
            "mode": ("mode", str, ()),
            "amount": ("amount", float, (0.0, 1.0, 0.05, 1.0)),
            "offset_l": ("offset_l", float, (0.0, 1.0, 0.05, 0.0)),
            "offset_r": ("offset_r", float, (0.0, 1.0, 0.05, 0.5)),
            "width": ("width", float, (0.0, 2.0, 0.05, 1.0)),
            "hz": ("hz", float, (0.01, 100.0, 0.1, 2.0)),
        }
        parameters = {
            "level_in": 1.0, "level_out": 1.0, "mode": "sine", "amount": 1.0,
            "offset_l": 0.0, "offset_r": 0.5, "width": 1.0, "hz": 2.0,
        }
        backend_info = {"mpv_filter_name": "apulsator", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Pulsator", parameters, backend_info)


class MPVExtraStereoFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "m": ("m", float, (-10.0, 10.0, 0.1, 2.5)),
            "c": ("c", str, ()),
        }
        parameters = {"m": 2.5, "c": "true"}
        backend_info = {"mpv_filter_name": "extrastereo", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Extra Stereo", parameters, backend_info)


class MPVStereoWidenFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "delay": ("delay", float, (0.0, 100.0, 1.0, 20.0)),
            "feedback": ("feedback", float, (0.0, 0.9, 0.05, 0.3)),
            "crossfeed": ("crossfeed", float, (0.0, 0.8, 0.05, 0.3)),
            "drymix": ("drymix", float, (0.0, 1.0, 0.05, 0.8)),
        }
        parameters = {"delay": 20.0, "feedback": 0.3, "crossfeed": 0.3, "drymix": 0.8}
        backend_info = {"mpv_filter_name": "stereowiden", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Stereo Widen", parameters, backend_info)


class MPVStereoToolsFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "level_in": ("level_in", float, (0.015625, 64.0, 0.1, 1.0)),
            "level_out": ("level_out", float, (0.015625, 64.0, 0.1, 1.0)),
            "balance_in": ("balance_in", float, (-1.0, 1.0, 0.05, 0.0)),
            "balance_out": ("balance_out", float, (-1.0, 1.0, 0.05, 0.0)),
            "mode": ("mode", str, ()),
            "base": ("base", float, (-1.0, 1.0, 0.05, 0.0)),
            "phase": ("phase", float, (0.0, 360.0, 1.0, 0.0)),
        }
        parameters = {
            "level_in": 1.0, "level_out": 1.0, "balance_in": 0.0, "balance_out": 0.0,
            "mode": "lr>lr", "base": 0.0, "phase": 0.0,
        }
        backend_info = {"mpv_filter_name": "stereotools", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Stereo Tools", parameters, backend_info)


class MPVHaasFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "level_in": ("level_in", float, (0.0, 2.0, 0.05, 1.0)),
            "level_out": ("level_out", float, (0.0, 2.0, 0.05, 1.0)),
            "side_gain": ("side_gain", float, (0.0, 2.0, 0.05, 1.0)),
            "middle_source": ("middle_source", str, ()),
            "left_delay": ("left_delay", float, (0.0, 40.0, 0.5, 2.05)),
            "right_delay": ("right_delay", float, (0.0, 40.0, 0.5, 2.12)),
        }
        parameters = {
            "level_in": 1.0, "level_out": 1.0, "side_gain": 1.0,
            "middle_source": "mid", "left_delay": 2.05, "right_delay": 2.12,
        }
        backend_info = {"mpv_filter_name": "haas", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Haas", parameters, backend_info)


class MPVBS2BFilter(MPVAudioFilter):
    """Bauer stereo-to-binaural -- requires ffmpeg built with --enable-libbs2b;
    if the bundled ffmpeg/libmpv lacks it, mpv will reject this filter node
    the same way any unknown lavfi filter name fails (logged, chain node
    dropped), not a crash."""

    def __init__(self):
        mpv_param_map = {
            "profile": ("profile", str, ()),
            "fcut": ("fcut", int, (300, 2000, 10, 700)),
            "feed": ("feed", int, (10, 150, 5, 50)),
        }
        parameters = {"profile": "default", "fcut": 700, "feed": 50}
        backend_info = {"mpv_filter_name": "bs2b", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Binaural (bs2b)", parameters, backend_info)


class MPVCrossfeedFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "strength": ("strength", float, (0.0, 1.0, 0.05, 0.2)),
            "range": ("range", float, (0.0, 1.0, 0.05, 0.5)),
            "slope": ("slope", float, (0.01, 1.0, 0.01, 0.5)),
            "level_in": ("level_in", float, (0.0, 2.0, 0.05, 0.9)),
            "level_out": ("level_out", float, (0.0, 2.0, 0.05, 1.0)),
        }
        parameters = {"strength": 0.2, "range": 0.5, "slope": 0.5, "level_in": 0.9, "level_out": 1.0}
        backend_info = {"mpv_filter_name": "crossfeed", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Crossfeed", parameters, backend_info)


class MPVBandRejectFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "frequency": ("frequency", float, (20.0, 20000.0, 10.0, 3000.0)),
            "width_type": ("width_type", str, ()),
            "width": ("width", float, (0.1, 10000.0, 0.1, 100.0)),
            "mix": ("mix", float, (0.0, 1.0, 0.1, 1.0)),
        }
        parameters = {"frequency": 3000.0, "width_type": "h", "width": 100.0, "mix": 1.0}
        backend_info = {"mpv_filter_name": "bandreject", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Band Reject", parameters, backend_info)


class MPVBassFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "gain": ("gain", float, (-20.0, 20.0, 0.5, 0.0)),
            "frequency": ("frequency", float, (20.0, 20000.0, 10.0, 100.0)),
            "width_type": ("width_type", str, ()),
            "width": ("width", float, (0.1, 10000.0, 0.1, 0.5)),
            "poles": ("poles", int, (1, 2, 1, 2)),
            "mix": ("mix", float, (0.0, 1.0, 0.1, 1.0)),
        }
        parameters = {"gain": 0.0, "frequency": 100.0, "width_type": "q", "width": 0.5, "poles": 2, "mix": 1.0}
        backend_info = {"mpv_filter_name": "bass", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Bass (Shelf)", parameters, backend_info)


class MPVTrebleFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "gain": ("gain", float, (-20.0, 20.0, 0.5, 0.0)),
            "frequency": ("frequency", float, (20.0, 20000.0, 10.0, 3000.0)),
            "width_type": ("width_type", str, ()),
            "width": ("width", float, (0.1, 10000.0, 0.1, 0.5)),
            "poles": ("poles", int, (1, 2, 1, 2)),
            "mix": ("mix", float, (0.0, 1.0, 0.1, 1.0)),
        }
        parameters = {"gain": 0.0, "frequency": 3000.0, "width_type": "q", "width": 0.5, "poles": 2, "mix": 1.0}
        backend_info = {"mpv_filter_name": "treble", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Treble (Shelf)", parameters, backend_info)


class MPVTiltShelfFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "gain": ("gain", float, (-20.0, 20.0, 0.5, 0.0)),
            "frequency": ("frequency", float, (20.0, 20000.0, 10.0, 3000.0)),
            "width_type": ("width_type", str, ()),
            "width": ("width", float, (0.1, 10000.0, 0.1, 0.5)),
            "poles": ("poles", int, (1, 2, 1, 2)),
            "mix": ("mix", float, (0.0, 1.0, 0.1, 1.0)),
        }
        parameters = {"gain": 0.0, "frequency": 3000.0, "width_type": "q", "width": 0.5, "poles": 2, "mix": 1.0}
        backend_info = {"mpv_filter_name": "tiltshelf", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Tilt Shelf", parameters, backend_info)


class MPVDynamicNormalizerFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "framelen": ("framelen", int, (10, 8000, 10, 500)),
            "gausssize": ("gausssize", int, (3, 301, 2, 31)),
            "peak": ("peak", float, (0.0, 1.0, 0.01, 0.95)),
            "maxgain": ("maxgain", float, (1.0, 100.0, 0.5, 10.0)),
            "targetrms": ("targetrms", float, (0.0, 1.0, 0.05, 0.0)),
            "compress": ("compress", float, (0.0, 30.0, 0.5, 0.0)),
        }
        parameters = {
            "framelen": 500, "gausssize": 31, "peak": 0.95,
            "maxgain": 10.0, "targetrms": 0.0, "compress": 0.0,
        }
        backend_info = {"mpv_filter_name": "dynaudnorm", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Dynamic Normalizer", parameters, backend_info)


class MPVSpeechNormalizerFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "peak": ("peak", float, (0.0, 1.0, 0.01, 0.95)),
            "expansion": ("expansion", float, (1.0, 50.0, 0.5, 2.0)),
            "compression": ("compression", float, (1.0, 50.0, 0.5, 2.0)),
            "threshold": ("threshold", float, (0.0, 1.0, 0.01, 0.0)),
            "raise": ("raise", float, (0.0, 1.0, 0.001, 0.001)),
            "fall": ("fall", float, (0.0, 1.0, 0.001, 0.001)),
        }
        parameters = {
            "peak": 0.95, "expansion": 2.0, "compression": 2.0,
            "threshold": 0.0, "raise": 0.001, "fall": 0.001,
        }
        backend_info = {"mpv_filter_name": "speechnorm", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Speech Normalizer", parameters, backend_info)


class MPVCompandFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "attacks": ("attacks", float, (0.0, 2.0, 0.05, 0.3)),
            "decays": ("decays", float, (0.0, 2.0, 0.05, 0.8)),
            "points": ("points", str, ()),
            "soft-knee": ("soft-knee", float, (0.0, 10.0, 0.1, 0.01)),
            "gain": ("gain", float, (-20.0, 20.0, 0.5, 0.0)),
        }
        parameters = {
            "attacks": 0.3, "decays": 0.8,
            "points": "-70/-70|-60/-20|-20/-20|0/-6", "soft-knee": 0.01, "gain": 0.0,
        }
        backend_info = {"mpv_filter_name": "compand", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Compand", parameters, backend_info)


class MPVDeesserFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "i": ("i", float, (0.0, 1.0, 0.05, 0.0)),
            "m": ("m", float, (0.0, 1.0, 0.05, 0.5)),
            "f": ("f", float, (0.0, 1.0, 0.05, 0.5)),
            "s": ("s", str, ()),
        }
        parameters = {"i": 0.0, "m": 0.5, "f": 0.5, "s": "o"}
        backend_info = {"mpv_filter_name": "deesser", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("De-esser", parameters, backend_info)


class MPVDenoiseFFTFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "nr": ("nr", float, (0.01, 97.0, 0.5, 12.0)),
            "nf": ("nf", float, (-80.0, -20.0, 1.0, -50.0)),
            "nt": ("nt", str, ()),
            "tn": ("tn", str, ()),
        }
        parameters = {"nr": 12.0, "nf": -50.0, "nt": "white", "tn": "false"}
        backend_info = {"mpv_filter_name": "afftdn", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Noise Reduction (FFT)", parameters, backend_info)


class MPVDenoiseNLMFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "s": ("s", float, (0.00001, 10000.0, 0.001, 0.00001)),
            "p": ("p", float, (1.0, 100.0, 1.0, 2.0)),
            "r": ("r", float, (2.0, 300.0, 1.0, 6.0)),
            "m": ("m", float, (1.0, 1000.0, 1.0, 11.0)),
        }
        parameters = {"s": 0.00001, "p": 2.0, "r": 6.0, "m": 11.0}
        backend_info = {"mpv_filter_name": "anlmdn", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Noise Reduction (NLM)", parameters, backend_info)


class MPVCrystalizerFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "i": ("i", float, (-10.0, 10.0, 0.1, 2.0)),
            "c": ("c", str, ()),
        }
        parameters = {"i": 2.0, "c": "true"}
        backend_info = {"mpv_filter_name": "crystalizer", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Crystalizer", parameters, backend_info)


class MPVExciterFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "level_in": ("level_in", float, (0.0, 64.0, 0.1, 1.0)),
            "level_out": ("level_out", float, (0.0, 64.0, 0.1, 1.0)),
            "amount": ("amount", float, (0.0, 64.0, 0.1, 1.0)),
            "drive": ("drive", float, (0.1, 10.0, 0.1, 8.5)),
            "blend": ("blend", float, (-10.0, 10.0, 0.5, 0.0)),
            "freq": ("freq", float, (2000.0, 12000.0, 100.0, 7500.0)),
            "ceil": ("ceil", float, (9999.0, 20000.0, 100.0, 9999.0)),
        }
        parameters = {
            "level_in": 1.0, "level_out": 1.0, "amount": 1.0, "drive": 8.5,
            "blend": 0.0, "freq": 7500.0, "ceil": 9999.0,
        }
        backend_info = {"mpv_filter_name": "aexciter", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Exciter", parameters, backend_info)


class MPVPhaserFilter(MPVAudioFilter):
    def __init__(self):
        mpv_param_map = {
            "in_gain": ("in_gain", float, (0.0, 1.0, 0.05, 0.4)),
            "out_gain": ("out_gain", float, (0.0, 4.0, 0.05, 0.74)),
            "delay": ("delay", float, (0.0, 5.0, 0.1, 3.0)),
            "decay": ("decay", float, (0.0, 0.99, 0.05, 0.4)),
            "speed": ("speed", float, (0.1, 10.0, 0.1, 0.5)),
            "type": ("type", str, ()),
        }
        parameters = {
            "in_gain": 0.4, "out_gain": 0.74, "delay": 3.0,
            "decay": 0.4, "speed": 0.5, "type": "triangular",
        }
        backend_info = {"mpv_filter_name": "aphaser", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Phaser", parameters, backend_info)


class MPVEarwaxFilter(MPVAudioFilter):
    """No configurable parameters -- adds fixed headphone-widening cues to
    44.1kHz stereo audio (ported from SoX)."""

    def __init__(self):
        backend_info = {"mpv_filter_name": "earwax", "mpv_param_map": {}, "effect_syntax": "lavfi"}
        super().__init__("Earwax", {}, backend_info)


class MPVConvolutionReverbFilter(MPVAudioFilter):
    """Real convolution reverb via ffmpeg's `afir`, driven by a user-picked
    (or bundled, see media_core.av_play.mpv_effects_catalog) impulse-
    response .wav file.

    `afir` is a 2-input filter (dry signal + a separate IR stream) -- the
    same shape that made the naive attempt at MPVReverbFilter above fail
    outright ("lavfi: exactly 2 pads required", killing the *entire* audio
    filter chain, not just this effect). The fix is to source the IR
    *inside* this filter's own self-contained lavfi graph via `amovie=`,
    so the node still only exposes one external in/out pad to mpv:

        lavfi=[amovie='<escaped_path>'[reverbir];[in][reverbir]afir=dry=D:wet=W[out]]

    `amovie=` opens its own decoder for the IR file independently of mpv's
    main playback pipeline, which is exactly the technique ffmpeg's own
    afir manual documents for multi-IR graphs (see
    archive/docs/ffmpeg-manuals/ffmpeg-filters/8-audio-filters/afir.md).

    TODO(verify): this exact syntax has not yet been confirmed against a
    real mpv instance -- do that (real playback + mpv log output) before
    relying on it, and update this docstring with the confirmed-working
    form once it has been. An invalid/missing IR path must never reach
    this string (see construct() below), since a mid-graph amovie failure
    takes the whole chain down the same way the original 2-pad afir
    attempt did.
    """

    def __init__(self):
        mpv_param_map = {
            "dry": ("dry", float, (0.0, 1.0, 0.05, 1.0)),
            "wet": ("wet", float, (0.0, 1.0, 0.05, 1.0)),
        }
        parameters = {
            "impulse_response_path": "",
            "dry": 1.0,
            "wet": 1.0,
        }
        backend_info = {"mpv_filter_name": "afir", "mpv_param_map": mpv_param_map, "effect_syntax": "lavfi"}
        super().__init__("Convolution Reverb", parameters, backend_info)

    def _validate_parameters(self):
        # impulse_response_path is a plain string with no mpv_param_map
        # entry (it never gets key=value interpolated -- see construct()),
        # so the base class's numeric-range validation loop must skip it.
        pass

    def set_parameter(self, name: str, value):
        if name == "impulse_response_path":
            self.parameters[name] = value
            return
        super().set_parameter(name, value)

    def construct(self) -> str:
        params = self.get_parameters()
        ir_path = params.get("impulse_response_path") or ""
        dry = params.get("dry", 1.0)
        wet = params.get("wet", 1.0)

        if not ir_path or not os.path.isfile(ir_path):
            # Graceful degradation: omit this node entirely rather than
            # handing mpv a graph that references a missing/invalid file --
            # an amovie failure inside the graph breaks the whole chain,
            # not just this effect (see class docstring).
            return ""

        escaped_path = escape_lavfi_path(ir_path)
        return (
            f"lavfi=[amovie={escaped_path}[reverbir];"
            f"[in][reverbir]afir=dry={dry}:wet={wet}[out]]"
        )

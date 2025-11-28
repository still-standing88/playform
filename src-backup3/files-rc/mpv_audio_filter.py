from typing import Any
from .__AV_Common import *
from .audio_filter import AudioFilter

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
    def __init__(self):
        mpv_param_map = {
            "dry": ("dry", float, (0.0, 1.0, 0.1, 1.0)),
            "wet": ("wet", float, (0.0, 1.0, 0.1, 0.3)),
            "length": ("length", int, (1, 100, 1, 1)),
            "irnorm": ("irnorm", float, (-1.0, 2.0, 0.1, 1.0)),
            "irgain": ("irgain", float, (0.0, 1.0, 0.1, 1.0))
        }
        
        parameters = {
            "dry": 1.0,
            "wet": 0.3,
            "length": 1,
            "irnorm": 1.0,
            "irgain": 1.0
        }
        
        backend_info = {
            "mpv_filter_name": "afir",
            "mpv_param_map": mpv_param_map,
            "effect_syntax": "lavfi"
        }
        
        super().__init__("Reverb", parameters, backend_info)

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
            "mpv_param_map": mpv_param_map
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
        
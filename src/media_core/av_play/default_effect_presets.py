import os

from utilities.functions import get_ir_dir

# Factory presets seeded into data/presets/audio_effects/<effect_id>/ the
# first time mpv_effect_presets.list_presets(effect_id) is called for a
# freshly-installed effect id (see _seed_defaults_if_empty there). After
# that, they're just ordinary preset files -- the user can edit or delete
# them like anything else they saved themselves.
#
# Keys must match the effect's MPVAudioFilter subclass's own
# mpv_param_map keys 1:1 (see media_core.av_play.mpv_audio_filter and the
# matching entry in mpv_effects_catalog.MPV_EFFECTS).

_ir_path = lambda name: os.path.join(get_ir_dir(), name)

DEFAULT_EFFECT_PRESETS: dict[str, list] = {
    "echo": [
        ("Slap Delay", {"in_gain": 0.7, "out_gain": 0.5, "delays": "120", "decays": "0.25"}),
        ("Hall Echo", {"in_gain": 0.6, "out_gain": 0.4, "delays": "500", "decays": "0.5"}),
        ("Long Ambient", {"in_gain": 0.5, "out_gain": 0.3, "delays": "1000", "decays": "0.6"}),
    ],
    "reverb": [
        ("Small Room", {"in_gain": 0.8, "out_gain": 0.5, "decay": 0.25, "room_size": 0.6}),
        ("Hall", {"in_gain": 0.8, "out_gain": 0.6, "decay": 0.4, "room_size": 1.0}),
        ("Vocal Booth", {"in_gain": 0.7, "out_gain": 0.35, "decay": 0.15, "room_size": 0.35}),
        ("Cathedral", {"in_gain": 0.85, "out_gain": 0.7, "decay": 0.6, "room_size": 2.2}),
    ],
    "convolution_reverb": [
        ("Small Speaker (Close)", {"impulse_response_path": _ir_path("Small-Speaker1.wav"), "dry": 1.0, "wet": 0.6}),
        ("Small Speaker (Distant)", {"impulse_response_path": _ir_path("Small-Speaker3.wav"), "dry": 0.8, "wet": 0.9}),
        ("Car Interior", {"impulse_response_path": _ir_path("car1.wav"), "dry": 1.0, "wet": 0.7}),
        ("Car Interior (Alt)", {"impulse_response_path": _ir_path("car2.wav"), "dry": 1.0, "wet": 0.7}),
    ],
    "lowpass": [
        ("Telephone", {"frequency": 3000.0, "poles": 2, "width": 0.707, "mix": 1.0}),
        ("Muffled / Next Room", {"frequency": 800.0, "poles": 2, "width": 0.707, "mix": 1.0}),
        ("Gentle Air Roll-off", {"frequency": 12000.0, "poles": 1, "width": 0.707, "mix": 1.0}),
    ],
    "highpass": [
        ("Remove Rumble", {"frequency": 80.0, "poles": 2, "width": 0.707, "mix": 1.0}),
        ("Thin/Radio Voice", {"frequency": 500.0, "poles": 2, "width": 0.707, "mix": 1.0}),
        ("Tighten Bass Bleed", {"frequency": 150.0, "poles": 1, "width": 0.707, "mix": 1.0}),
    ],
    "bandpass": [
        ("Old Radio", {"frequency": 1800.0, "width": 1500.0, "csg": 0, "mix": 1.0, "width_type": "h"}),
        ("Telephone Voice", {"frequency": 1500.0, "width": 2000.0, "csg": 0, "mix": 1.0, "width_type": "h"}),
    ],
    "bandreject": [
        ("Notch Hum (60Hz)", {"frequency": 60.0, "width_type": "h", "width": 10.0, "mix": 1.0}),
        ("Notch Hum (50Hz)", {"frequency": 50.0, "width_type": "h", "width": 10.0, "mix": 1.0}),
        ("Scoop Mids", {"frequency": 1000.0, "width_type": "o", "width": 1.0, "mix": 1.0}),
    ],
    "bass": [
        ("Warm Boost", {"gain": 4.0, "frequency": 100.0, "width_type": "q", "width": 0.5, "poles": 2, "mix": 1.0}),
        ("Tight Cut", {"gain": -4.0, "frequency": 120.0, "width_type": "q", "width": 0.7, "poles": 2, "mix": 1.0}),
        ("Subwoofer Boost", {"gain": 6.0, "frequency": 60.0, "width_type": "q", "width": 0.5, "poles": 2, "mix": 1.0}),
    ],
    "treble": [
        ("Bright/Airy", {"gain": 4.0, "frequency": 8000.0, "width_type": "q", "width": 0.5, "poles": 2, "mix": 1.0}),
        ("De-harsh", {"gain": -3.0, "frequency": 6000.0, "width_type": "q", "width": 0.7, "poles": 2, "mix": 1.0}),
    ],
    "tiltshelf": [
        ("Warmer Overall", {"gain": -3.0, "frequency": 3000.0, "width_type": "q", "width": 0.5, "poles": 2, "mix": 1.0}),
        ("Brighter Overall", {"gain": 3.0, "frequency": 3000.0, "width_type": "q", "width": 0.5, "poles": 2, "mix": 1.0}),
    ],
    "compressor": [
        ("Gentle", {"level_in": 1.0, "threshold": 0.35, "ratio": 2.0, "attack": 20.0, "release": 250.0,
                     "makeup": 1.2, "knee": 2.82843, "detection": "rms", "mix": 1.0}),
        ("Podcast Voice", {"level_in": 1.0, "threshold": 0.15, "ratio": 4.0, "attack": 10.0, "release": 180.0,
                            "makeup": 1.6, "knee": 2.82843, "detection": "rms", "mix": 1.0}),
        ("Broadcast Limiting", {"level_in": 1.0, "threshold": 0.09, "ratio": 8.0, "attack": 5.0, "release": 120.0,
                                 "makeup": 2.0, "knee": 1.5, "detection": "peak", "mix": 1.0}),
    ],
    "limiter": [
        ("Transparent", {"level_in": 1.0, "level_out": 1.0, "limit": 0.95, "attack": 5.0, "release": 50.0,
                          "asc": "true", "asc_level": 0.5, "level": "true"}),
        ("Loud/Streaming-Safe", {"level_in": 1.0, "level_out": 1.0, "limit": 0.89, "attack": 2.0, "release": 100.0,
                                  "asc": "true", "asc_level": 0.7, "level": "true"}),
    ],
    "gate": [
        ("Noise Gate (Vocal)", {"level_in": 1.0, "mode": "downward", "range": 0.02, "threshold": 0.08,
                                 "ratio": 4.0, "attack": 5.0, "release": 150.0, "makeup": 1.0,
                                 "knee": 2.828427125, "detection": "rms", "link": "average"}),
        ("Aggressive Gate", {"level_in": 1.0, "mode": "downward", "range": 0.0, "threshold": 0.15,
                              "ratio": 8.0, "attack": 2.0, "release": 80.0, "makeup": 1.0,
                              "knee": 1.0, "detection": "peak", "link": "average"}),
    ],
    "dynaudnorm": [
        ("Podcast Leveling", {"framelen": 500, "gausssize": 31, "peak": 0.95, "maxgain": 10.0,
                               "targetrms": 0.3, "compress": 0.0}),
        ("Music Loudness Match", {"framelen": 500, "gausssize": 15, "peak": 0.95, "maxgain": 6.0,
                                   "targetrms": 0.0, "compress": 0.0}),
    ],
    "speechnorm": [
        ("Weak/Slow", {"peak": 0.95, "expansion": 3.0, "compression": 2.0, "threshold": 0.0, "raise": 0.00001, "fall": 0.00001}),
        ("Strong/Fast (Podcast)", {"peak": 0.95, "expansion": 12.5, "compression": 2.0, "threshold": 0.0, "raise": 0.0001, "fall": 0.0001}),
    ],
    "compand": [
        ("Noisy Environment Listening", {"attacks": 0.3, "decays": 0.8,
                                          "points": "-90/-60|-60/-40|-40/-30|-20/-20", "soft-knee": 6.0, "gain": 0.0}),
        ("2:1 Compression", {"attacks": 0.3, "decays": 0.8,
                              "points": "-80/-80|-6/-6|0/-3.8|20/3.5", "soft-knee": 0.01, "gain": 0.0}),
    ],
    "deesser": [
        ("Mild De-ess", {"i": 0.3, "m": 0.4, "f": 0.6, "s": "o"}),
        ("Strong De-ess", {"i": 0.6, "m": 0.7, "f": 0.4, "s": "o"}),
    ],
    "flanger": [
        ("Classic Flange", {"delay": 0.0, "depth": 2.0, "regen": 0.0, "width": 71.0, "speed": 0.5,
                             "shape": "sinusoidal", "phase": 25.0, "interp": "linear"}),
        ("Jet Sweep", {"delay": 2.0, "depth": 6.0, "regen": 40.0, "width": 90.0, "speed": 0.2,
                        "shape": "sinusoidal", "phase": 25.0, "interp": "linear"}),
    ],
    "chorus": [
        ("Subtle Thicken", {"in_gain": 0.5, "out_gain": 0.5, "delays": "40", "decays": "0.3",
                             "speeds": "0.2", "depths": "1.5"}),
        ("Lush 80s Chorus", {"in_gain": 0.4, "out_gain": 0.4, "delays": "55", "decays": "0.4",
                              "speeds": "0.25", "depths": "2"}),
    ],
    "tremolo": [
        ("Subtle Pulse", {"f": 4.0, "d": 0.3}),
        ("Classic Amp Tremolo", {"f": 6.0, "d": 0.6}),
        ("Ring Mod (Extreme)", {"f": 50.0, "d": 1.0}),
    ],
    "vibrato": [
        ("Gentle Vibrato", {"f": 5.0, "d": 0.3}),
        ("Wide Vibrato", {"f": 7.0, "d": 0.7}),
    ],
    "pulsator": [
        ("Slow Autopan", {"level_in": 1.0, "level_out": 1.0, "mode": "sine", "amount": 1.0,
                           "offset_l": 0.0, "offset_r": 0.5, "width": 1.0, "hz": 0.5}),
        ("Tremolo (Synced)", {"level_in": 1.0, "level_out": 1.0, "mode": "square", "amount": 1.0,
                               "offset_l": 0.0, "offset_r": 0.0, "width": 1.0, "hz": 4.0}),
    ],
    "phaser": [
        ("Classic Phaser", {"in_gain": 0.4, "out_gain": 0.74, "delay": 3.0, "decay": 0.4,
                             "speed": 0.5, "type": "triangular"}),
        ("Slow Sweep", {"in_gain": 0.4, "out_gain": 0.74, "delay": 3.0, "decay": 0.6,
                         "speed": 0.15, "type": "sinusoidal"}),
    ],
    "pitch_shift": [
        ("One Octave Up", {"pitch-scale": 2.0, "engine": "finer"}),
        ("One Octave Down", {"pitch-scale": 0.5, "engine": "finer"}),
        ("Subtle Detune", {"pitch-scale": 1.05, "engine": "finer"}),
    ],
    "tempo_scale": [
        ("Half Speed", {"scale": 1, "speed": "none"}),
        ("Double Speed", {"scale": 2, "speed": "none"}),
    ],
    "extrastereo": [
        ("Subtle Widen", {"m": 1.5, "c": "true"}),
        ("Wide Stage", {"m": 3.5, "c": "true"}),
    ],
    "stereowiden": [
        ("Gentle Widen", {"delay": 15.0, "feedback": 0.2, "crossfeed": 0.2, "drymix": 0.85}),
        ("Wide Stage", {"delay": 25.0, "feedback": 0.4, "crossfeed": 0.4, "drymix": 0.7}),
    ],
    "stereotools": [
        ("Mid/Side Widen", {"level_in": 1.0, "level_out": 1.0, "balance_in": 0.0, "balance_out": 0.0,
                             "mode": "lr>lr", "base": 0.4, "phase": 0.0}),
        ("Mono Downmix", {"level_in": 1.0, "level_out": 1.0, "balance_in": 0.0, "balance_out": 0.0,
                           "mode": "lr>l+r", "base": 0.0, "phase": 0.0}),
    ],
    "haas": [
        ("Mono-to-Stereo Widen", {"level_in": 1.0, "level_out": 1.0, "side_gain": 1.0,
                                   "middle_source": "mid", "left_delay": 2.05, "right_delay": 15.0}),
    ],
    "bs2b": [
        ("Default Headphone", {"profile": "default", "fcut": 700, "feed": 50}),
        ("Chu Moy", {"profile": "cmoy", "fcut": 700, "feed": 60}),
        ("Jan Meier", {"profile": "jmeier", "fcut": 650, "feed": 95}),
    ],
    "crossfeed": [
        ("Subtle Headphone Crossfeed", {"strength": 0.15, "range": 0.5, "slope": 0.5, "level_in": 0.9, "level_out": 1.0}),
        ("Strong Speaker-Like", {"strength": 0.5, "range": 0.7, "slope": 0.3, "level_in": 0.9, "level_out": 1.0}),
    ],
    "denoise_fft": [
        ("Light Hiss Reduction", {"nr": 6.0, "nf": -50.0, "nt": "white", "tn": "false"}),
        ("Vinyl Crackle", {"nr": 12.0, "nf": -45.0, "nt": "vinyl", "tn": "false"}),
        ("Adaptive/Field Recording", {"nr": 15.0, "nf": -50.0, "nt": "white", "tn": "true"}),
    ],
    "denoise_nlm": [
        ("Gentle", {"s": 0.00003, "p": 2.0, "r": 6.0, "m": 11.0}),
        ("Strong", {"s": 0.001, "p": 4.0, "r": 12.0, "m": 15.0}),
    ],
    "crystalizer": [
        ("Add Sparkle", {"i": 2.0, "c": "true"}),
        ("Subtle Sharpen", {"i": 0.8, "c": "true"}),
    ],
    "exciter": [
        ("Vocal Presence", {"level_in": 1.0, "level_out": 1.0, "amount": 1.0, "drive": 8.5,
                             "blend": 0.0, "freq": 7500.0, "ceil": 9999.0}),
        ("Air/Sparkle", {"level_in": 1.0, "level_out": 1.0, "amount": 2.0, "drive": 6.0,
                          "blend": 2.0, "freq": 9000.0, "ceil": 15000.0}),
    ],
    "equalizer": [
        ("Bass Boost", {"preamp": 0.0, "band_0": 6.0, "band_1": 4.0, "band_2": 2.0, "band_3": 0.0,
                         "band_4": 0.0, "band_5": 0.0, "band_6": 0.0, "band_7": 0.0, "band_8": 0.0, "band_9": 0.0}),
        ("Vocal Boost", {"preamp": 0.0, "band_0": -2.0, "band_1": -1.0, "band_2": 0.0, "band_3": 2.0,
                          "band_4": 4.0, "band_5": 3.0, "band_6": 2.0, "band_7": 0.0, "band_8": 0.0, "band_9": 0.0}),
        ("Treble Boost", {"preamp": 0.0, "band_0": 0.0, "band_1": 0.0, "band_2": 0.0, "band_3": 0.0,
                           "band_4": 0.0, "band_5": 1.0, "band_6": 3.0, "band_7": 5.0, "band_8": 6.0, "band_9": 6.0}),
        ("Flat", {"preamp": 0.0, "band_0": 0.0, "band_1": 0.0, "band_2": 0.0, "band_3": 0.0,
                   "band_4": 0.0, "band_5": 0.0, "band_6": 0.0, "band_7": 0.0, "band_8": 0.0, "band_9": 0.0}),
    ],
}

from copy import deepcopy
from math import isfinite


ACTION_LABELS = {
    "disabled": "Disabled",
    "toggle_controls": "Show/hide controls",
    "play_pause": "Play/Pause",
    "seek_backward": "Seek backward",
    "seek_forward": "Seek forward",
    "previous": "Previous track",
    "next": "Next track",
    "mute": "Mute/Unmute",
    "fullscreen": "Enter/exit fullscreen",
    "bookmark": "Add bookmark",
    "loop_start": "Set repeat loop start",
    "loop_end": "Set repeat loop end",
    "clear_loop": "Clear repeat loop",
    "menu": "Show playback menu",
    "subtitles": "Show/hide subtitles",
    "screenshot": "Take screenshot",
    "playlist": "Show playlist",
    "queue": "Show queue",
    "temporary_speed": "Temporary fast playback while held",
    "seek": "Scrub playback position",
    "volume": "Adjust volume",
    "brightness": "Adjust video brightness",
    "zoom": "Zoom video",
    "pan": "Pan video",
}
TAP_ACTIONS = tuple(list(ACTION_LABELS)[:18])
GESTURES = {
    "tap": ("Taps and holds", "Single tap", TAP_ACTIONS),
    "double_tap_left": ("Taps and holds", "Double tap: left third", TAP_ACTIONS),
    "double_tap_center": ("Taps and holds", "Double tap: centre third", TAP_ACTIONS),
    "double_tap_right": ("Taps and holds", "Double tap: right third", TAP_ACTIONS),
    "long_press": ("Taps and holds", "Long press", TAP_ACTIONS + ("temporary_speed",)),
    "horizontal_drag": ("One-finger swipes", "Horizontal swipe", ("disabled", "seek")),
    "vertical_drag_left": ("One-finger swipes", "Vertical swipe: left half", ("disabled", "volume", "brightness")),
    "vertical_drag_right": ("One-finger swipes", "Vertical swipe: right half", ("disabled", "volume", "brightness")),
    "pinch": ("Two-finger gestures", "Pinch", ("disabled", "zoom")),
    "two_finger_drag": ("Two-finger gestures", "Two-finger drag", ("disabled", "pan")),
}
DEFAULT_SETTINGS = {
    "enabled": True,
    "fullscreen_only": False,
    "feedback": True,
    "seek_backward_seconds": 10,
    "seek_forward_seconds": 10,
    "scrub_seconds": 120,
    "sensitivity": 1.0,
    "volume_limit": 150,
    "hold_ms": 600,
    "double_tap_ms": 300,
    "drag_threshold": 20,
    "hold_speed": 2.0,
    "bindings": {
        "tap": "toggle_controls",
        "double_tap_left": "seek_backward",
        "double_tap_center": "play_pause",
        "double_tap_right": "seek_forward",
        "long_press": "menu",
        "horizontal_drag": "seek",
        "vertical_drag_left": "brightness",
        "vertical_drag_right": "volume",
        "pinch": "zoom",
        "two_finger_drag": "pan",
    },
}
SETTING_RANGES = {
    "seek_backward_seconds": (1, 600), "seek_forward_seconds": (1, 600),
    "scrub_seconds": (10, 3600), "sensitivity": (0.25, 3.0),
    "volume_limit": (10, 300), "hold_ms": (300, 2000),
    "double_tap_ms": (150, 700), "drag_threshold": (8, 80),
    "hold_speed": (0.25, 3.0),
}


def default_settings(preset="video"):
    settings = deepcopy(DEFAULT_SETTINGS)
    if preset == "audio":
        settings["seek_backward_seconds"] = 10
        settings["seek_forward_seconds"] = 30
        settings["bindings"].update({
            "long_press": "bookmark", "vertical_drag_left": "disabled",
            "pinch": "disabled", "two_finger_drag": "disabled",
        })
    return settings


def normalize_settings(value):
    settings = default_settings()
    if not isinstance(value, dict):
        return settings
    for key in ("enabled", "fullscreen_only", "feedback"):
        if isinstance(value.get(key), bool):
            settings[key] = value[key]
    for key, (low, high) in SETTING_RANGES.items():
        number = value.get(key)
        if isinstance(number, (int, float)) and not isinstance(number, bool) and isfinite(number):
            number = max(low, min(high, number))
            settings[key] = float(number) if isinstance(settings[key], float) else int(number)
    bindings = value.get("bindings")
    if isinstance(bindings, dict):
        for gesture, (_, _, actions) in GESTURES.items():
            if bindings.get(gesture) in actions:
                settings["bindings"][gesture] = bindings[gesture]
    return settings

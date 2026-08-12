import os

from utilities.functions import get_parent_dir
from utilities.formats import formats as media_formats
from .misc import screenshot_formats

prefs = {
"autoplay": True,
"repeat_mode": 0,
"shuffle": False,
"offset": {"seek": 5,"volume":5},
"player_volume": 120,
"explorer_volume": 120,
"explorer_loop": False,
"mpv_logging": True,
"debug_level": 0,
"yt-dlp_logging": False,
"yt-dlp_verbose_output": False,
"last_path": "",
"device": 0,
"device_name": "",
"default path": "",
"ffmpeg_binary": "",
"ffmpeg_path": os.path.join(get_parent_dir(), "bin"),
"image_format": screenshot_formats[1],
"color_theme": "system",
"language":"en",
"should_restart": False,
"subtitle-language":"en-US",
"auto_check_for_updates": True,
"youtube_cookies": "",
"mpv_extra_options": "",
"yt-dlp_binary": "",
"yt-dlp_path": os.path.join(get_parent_dir(), "bin"),
"accessibility_feedback": False,
"tts_speech_interrupt": True,
"tts_prefer_sapi": False,
"tts_voice": "",
"tts_volume": 80.0,
"tts_rate": 1.0,
"save_urls": False,
"urlls": [],
"equalizer_enabled": False,
"equalizer_preamp": 0.0,
"equalizer_bands": [],
"equalizer_preset": -1,
"ui_zoom_level": 0,
"catalog_extensions": media_formats["audio"] + media_formats["video"],
"catalog_auto_rescan": False,
"explorer_view_mode": "list",
"explorer_sort_mode": "name_asc",
"store_search_history": True,
"search_history": [],
"audio_effects_chain": []
}

# Keys actually surfaced in the Preferences dialog (general_panel.py,
# media_panel.py, accessibility_panel.py, advanced_panel.py,
# database_panel.py) -- these, and only these, persist to prefs.json.
# Everything else in `prefs` above is pure runtime/app state that used to
# ride along in the same file; it now persists in app_settings
# (user.sqlite3, key "runtime_prefs") instead. See app_config/prefs.py.
DIALOG_PREFS_KEYS = frozenset({
    "language", "image_format", "color_theme", "auto_check_for_updates",
    "save_urls", "offset", "device", "device_name",
    "accessibility_feedback", "tts_speech_interrupt", "tts_voice",
    "tts_volume", "tts_rate", "mpv_logging", "debug_level",
    "mpv_extra_options", "youtube_cookies", "yt-dlp_path", "ffmpeg_path",
    "yt-dlp_logging", "yt-dlp_verbose_output", "catalog_extensions",
    "store_search_history",
})

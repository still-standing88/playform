import os

from utilities.functions import get_parent_dir
from .misc import screenshot_formats

prefs = {
"autoplay": True,
"repeat_mode": 0,
"shuffle": False,
"offset": {"seek": 5,"volume":5},
"volume": 80,
"vlc_logging": True,
"debug_level": 0,
"yt-dlp_logging": False,
"yt-dlp_verbose_output": False,
"last_path": "",
"device": 0,
"default path": "",
"ffmpeg_binary": "",
"image_format": screenshot_formats[1],
"color_theme": "system",
"language":"en",
"subtitle-language":"en-US",
"auto_check_for_updates": True,
"youtube_cookies": "",
"vlc_args": "",
"yt-dlp_path": os.path.join(get_parent_dir(), "bin"),
"urlls": []
}

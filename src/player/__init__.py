import os
import sys

from app_config import prefs
from utilities.functions import get_app_path
from .url import set_ytdlp_path, set_ytdlp_log

ytdlp_path = os.path.join(
    prefs.prefs.get("yt-dlp_path", ""),
    f"yt-dlp{".exe" if sys.platform == "win32" else ""}")
set_ytdlp_path(ytdlp_path)

if prefs.prefs.get("yt-dlp_logging", False):
    log_file = os.path.join(get_app_path(), "logs", "yt-dlp.log")
    set_ytdlp_log(log_file, prefs.prefs.get("yt-dlp_verbose_output", False))
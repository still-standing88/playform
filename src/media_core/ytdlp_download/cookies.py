"""Cookie file staging shared by every yt-dlp invocation.

yt-dlp rewrites whatever file --cookies points at when the run ends, so the
file picked in Preferences is never handed to it directly. The user's file is
copied into the app's data folder (the app's own master copy), and each yt-dlp
run is pointed at a throwaway copy of that master, rewritten right before the
process starts (cookies_args()). Whatever a crashed or interrupted run does to
its cookie file is therefore confined to the scratch copy in the temp folder.

Zero Qt/app_config imports at module level, same as engine.py.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile

logger = logging.getLogger(__name__)

_COOKIE_FILE_NAME = "ytdlp_cookies.txt"


def _pref_cookies_file() -> str:
    try:
        from app_config import prefs as _prefs
        value = _prefs.prefs.get("youtube_cookies", "")
    except Exception:
        return ""
    return str(value) if value else ""


def _data_dir() -> str:
    try:
        from app_config import prefs as _prefs
        return _prefs.data_path
    except Exception:
        return ""


def master_cookie_path() -> str:
    """The app's own copy of the user's cookies file, in the data folder
    (app_config.prefs.data_path)."""
    data_dir = _data_dir()
    return os.path.join(data_dir, _COOKIE_FILE_NAME) if data_dir else ""


def scratch_cookie_path() -> str:
    """The disposable copy yt-dlp is actually given, replaced on every run."""
    return os.path.join(tempfile.gettempdir(), "PlayForm", _COOKIE_FILE_NAME)


def _copy(source: str, destination: str) -> bool:
    try:
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copyfile(source, destination)
        return True
    except OSError as exc:
        logger.warning("Could not copy cookies file to %s: %s", destination, exc)
        return False


def cookie_args(source: str = "") -> list:
    """yt-dlp "--cookies <file>" arguments, or [] when none can be staged.

    `source` defaults to the prefs' YouTube cookies file. The user's file is
    copied to the data folder, and that copy to the scratch file yt-dlp is
    pointed at. A missing source file degrades to a cookieless run rather than
    failing the command, matching the previous behavior."""
    source = source or _pref_cookies_file()
    if not source:
        return []
    if not os.path.isfile(source):
        logger.warning("Configured YouTube cookies file not found, ignoring: %s", source)
        return []

    master = master_cookie_path()
    if not master or not _copy(source, master):
        return []

    scratch = scratch_cookie_path()
    if not _copy(master, scratch):
        return []
    return ["--cookies", scratch]

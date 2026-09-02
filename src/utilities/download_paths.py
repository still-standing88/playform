"""Resolves the app's download destinations from prefs.

Each helper returns the user's configured folder when the matching pref is
set and falls back to the built-in downloads/ layout otherwise, so the
Downloads preferences page actually governs where files land.
"""

import os

from utilities.functions import get_app_path


def _configured(key: str) -> str:
    from app_config import prefs
    value = prefs.prefs.get(key) or ""
    return str(value).strip()


def default_download_dir() -> str:
    return _configured("download_dir") or os.path.join(get_app_path(), "downloads")


def podcast_download_dir() -> str:
    return _configured("download_podcast_dir") or os.path.join(
        get_app_path(), "downloads", "podcasts")


def ytdlp_download_dir() -> str:
    configured = _configured("download_dir")
    if configured:
        return os.path.join(configured, "yt-dlp")
    return os.path.join(get_app_path(), "downloads", "yt-dlp")

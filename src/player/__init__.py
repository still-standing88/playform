import os
import sys


from app_config import prefs
from utilities.functions import get_logs_dir, get_parent_dir
from .utilities import resolve_ytdlp_binary_path
from .url import set_ytdlp_path, set_ytdlp_log, preload_extractors

__all__ = ['init_binaries', 'reinit_ytdlp_settings']

def init_binaries():
    from .utilities import update_prefs_with_found_binaries
    current_path = get_parent_dir()
    bin_dir = os.path.join(current_path, "bin")

    # Deprecated: FFmpeg is now provisioned through the Utility Download Center
    # rather than unpacked from ffmpeg_binary.py / pyffmpeg at startup.
    # if not prefs.prefs.get("ffmpeg_binary") or not os.path.exists(prefs.prefs.get("ffmpeg_binary", "")):
    #     extracted_ffmpeg, _ = extract_ffmpeg_from_pyffmpeg(bin_dir)
    #     if extracted_ffmpeg:
    #         prefs.prefs["ffmpeg_binary"] = extracted_ffmpeg
    #         prefs.prefs["ffmpeg_path"] = bin_dir

    updated_prefs = update_prefs_with_found_binaries(prefs.prefs)
    if updated_prefs != prefs:
        prefs.prefs.update(updated_prefs)
        prefs.save()


ytdlp_path = resolve_ytdlp_binary_path()

if not ytdlp_path:
    ytdlp_path = os.path.join(
        prefs.prefs.get("yt-dlp_path", ""),
        f"yt-dlp{".exe" if sys.platform == "win32" else ""}")

if ytdlp_path:
    set_ytdlp_path(ytdlp_path)

if prefs.prefs.get("yt-dlp_logging", False):
    log_file = os.path.join(get_logs_dir(), "yt-dlp.log")
    set_ytdlp_log(log_file, prefs.prefs.get("yt-dlp_verbose_output", False))

preload_extractors()

def reinit_ytdlp_settings():
    ytdlp_path = resolve_ytdlp_binary_path()
    
    if not ytdlp_path:
        ytdlp_path = os.path.join(
            prefs.prefs.get("yt-dlp_path", ""),
            f"yt-dlp{".exe" if sys.platform == "win32" else ""}")
    
    if ytdlp_path:
        set_ytdlp_path(ytdlp_path)
    
    if prefs.prefs.get("yt-dlp_logging", False):
        log_file = os.path.join(get_logs_dir(), "yt-dlp.log")
        set_ytdlp_log(log_file, prefs.prefs.get("yt-dlp_verbose_output", False))
    else:
        set_ytdlp_log(None, False)


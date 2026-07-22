import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional, Tuple

from PySide6.QtWidgets import QMessageBox, QWidget

from app_config import prefs as app_prefs
from app_constance import prefs_dict
from utilities.functions import get_parent_dir


@dataclass(frozen=True)
class BinaryCheckResult:
    name: str
    path: str
    exists: bool
    runnable: bool
    detected: bool
    version: Optional[str]
    major: Optional[int]
    ok: bool
    message: str


def _get_pref_value(key: str, default: str = "") -> str:
    if key in app_prefs.prefs:
        value = app_prefs.prefs.get(key, default)
    else:
        value = prefs_dict.prefs.get(key, default)
    return str(value) if value is not None else default


def _run_command(args: list[str], timeout_s: float = 5.0) -> Tuple[int, str, str]:
    creationflags = 0
    if sys.platform == "win32":
        creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))

    try:
        p = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            creationflags=creationflags,
        )
        return p.returncode, p.stdout or "", p.stderr or ""
    except FileNotFoundError:
        return 127, "", "file not found"
    except Exception as e:
        return 1, "", str(e)


def _get_bin_ext() -> str:
    return '.exe' if os.name == 'nt' else ''


def _find_in_path(binary_name: str) -> Optional[str]:
    full_name = binary_name + _get_bin_ext()
    path_var = os.environ.get('PATH', '')
    for path_dir in path_var.split(os.pathsep):
        bin_path = os.path.join(path_dir, full_name)
        if os.path.isfile(bin_path) and os.access(bin_path, os.X_OK):
            return bin_path
    return None


def _verify_binary_exists(bin_path: str) -> bool:
    if not bin_path or not os.path.exists(bin_path):
        return False
    if not os.path.isfile(bin_path):
        return False
    if os.name == 'nt':
        return bin_path.lower().endswith('.exe')
    return os.access(bin_path, os.X_OK)


def resolve_ytdlp_binary_path() -> str:
    prefs_dict_copy = {}
    if hasattr(app_prefs, 'prefs'):
        prefs_dict_copy = app_prefs.prefs.copy()
    
    ytdlp_path = _locate_ytdlp(prefs_dict_copy)
    if ytdlp_path and _verify_binary_exists(ytdlp_path):
        return os.path.normpath(ytdlp_path)
    
    base = _get_pref_value("yt-dlp_path", "")
    exe_name = "yt-dlp" + _get_bin_ext()

    if not base:
        return ""

    candidate = base
    if os.path.isdir(candidate):
        candidate = os.path.join(candidate, exe_name)

    return os.path.normpath(candidate) if candidate else ""


def _locate_ytdlp(prefs: dict) -> Optional[str]:
    ytdlp_name = 'yt-dlp'
    
    pref_bin = prefs.get('yt-dlp_binary', '')
    if pref_bin and _verify_binary_exists(pref_bin):
        return pref_bin
    
    pref_path = prefs.get('yt-dlp_path', '')
    if pref_path and os.path.isdir(pref_path):
        ytdlp_candidate = os.path.join(pref_path, ytdlp_name + _get_bin_ext())
        if _verify_binary_exists(ytdlp_candidate):
            return ytdlp_candidate
    
    env_ytdlp = _find_in_path(ytdlp_name)
    if env_ytdlp:
        return env_ytdlp
    
    return None


def resolve_ffmpeg_binary_path() -> str:
    prefs_dict_copy = {}
    if hasattr(app_prefs, 'prefs'):
        prefs_dict_copy = app_prefs.prefs.copy()

    ffmpeg_path, _ = _locate_ffmpeg(prefs_dict_copy)
    if ffmpeg_path and _verify_binary_exists(ffmpeg_path):
        return os.path.normpath(ffmpeg_path)

    path = _get_pref_value("ffmpeg_binary", "")
    return os.path.normpath(path) if path else ""


def resolve_ffprobe_binary_path() -> str:
    prefs_dict_copy = {}
    if hasattr(app_prefs, 'prefs'):
        prefs_dict_copy = app_prefs.prefs.copy()

    _, ffprobe_path = _locate_ffmpeg(prefs_dict_copy)
    if ffprobe_path and _verify_binary_exists(ffprobe_path):
        return os.path.normpath(ffprobe_path)

    return ""


def _locate_ffmpeg(prefs: dict) -> Tuple[Optional[str], Optional[str]]:
    ffmpeg_name = 'ffmpeg'
    ffprobe_name = 'ffprobe'
    
    ffmpeg_path = None
    ffprobe_path = None
    
    pref_ffmpeg = prefs.get('ffmpeg_binary', '')
    if pref_ffmpeg and _verify_binary_exists(pref_ffmpeg):
        ffmpeg_path = pref_ffmpeg
        pref_dir = os.path.dirname(pref_ffmpeg)
        ffprobe_candidate = os.path.join(pref_dir, ffprobe_name + _get_bin_ext())
        if _verify_binary_exists(ffprobe_candidate):
            ffprobe_path = ffprobe_candidate
    
    pref_path = prefs.get('ffmpeg_path', '')
    if not ffmpeg_path and pref_path and os.path.isdir(pref_path):
        ffmpeg_candidate = os.path.join(pref_path, ffmpeg_name + _get_bin_ext())
        ffprobe_candidate = os.path.join(pref_path, ffprobe_name + _get_bin_ext())
        if _verify_binary_exists(ffmpeg_candidate):
            ffmpeg_path = ffmpeg_candidate
        if _verify_binary_exists(ffprobe_candidate):
            ffprobe_path = ffprobe_candidate

    app_bin_dir = os.path.join(get_parent_dir(), "bin")
    if os.path.isdir(app_bin_dir):
        ffmpeg_candidate = os.path.join(app_bin_dir, ffmpeg_name + _get_bin_ext())
        ffprobe_candidate = os.path.join(app_bin_dir, ffprobe_name + _get_bin_ext())
        if not ffmpeg_path and _verify_binary_exists(ffmpeg_candidate):
            ffmpeg_path = ffmpeg_candidate
        if not ffprobe_path and _verify_binary_exists(ffprobe_candidate):
            ffprobe_path = ffprobe_candidate
    
    if not ffmpeg_path:
        env_ffmpeg = _find_in_path(ffmpeg_name)
        if env_ffmpeg:
            ffmpeg_path = env_ffmpeg
    
    if not ffprobe_path:
        env_ffprobe = _find_in_path(ffprobe_name)
        if env_ffprobe:
            ffprobe_path = env_ffprobe
    
    return ffmpeg_path, ffprobe_path


def update_prefs_with_found_binaries(prefs: dict) -> dict:
    ffmpeg_path, ffprobe_path = _locate_ffmpeg(prefs)
    ytdlp_path = _locate_ytdlp(prefs)
    
    if ffmpeg_path:
        prefs['ffmpeg_binary'] = ffmpeg_path
        if ffprobe_path:
            prefs['ffmpeg_path'] = os.path.dirname(ffmpeg_path)
    
    if ytdlp_path:
        prefs['yt-dlp_binary'] = ytdlp_path
        prefs['yt-dlp_path'] = os.path.dirname(ytdlp_path)
    
    return prefs


def check_ytdlp() -> BinaryCheckResult:
    path = resolve_ytdlp_binary_path()

    if not path:
        return BinaryCheckResult(
            name="yt-dlp",
            path="",
            exists=False,
            runnable=False,
            detected=False,
            version=None,
            major=None,
            ok=False,
            message="yt-dlp path is not configured.",
        )

    exists = os.path.exists(path)
    if not exists:
        return BinaryCheckResult(
            name="yt-dlp",
            path=path,
            exists=False,
            runnable=False,
            detected=False,
            version=None,
            major=None,
            ok=False,
            message="yt-dlp was not found at the configured path.",
        )

    rc, out, err = _run_command([path, "--version"])
    runnable = rc == 0
    version = out.strip().splitlines()[0].strip() if out.strip() else None

    rc2, out2, err2 = _run_command([path, "--help"])
    combined = (out2 + "\n" + err2).lower()
    detected = ((rc2 == 0) or bool(out2) or bool(err2)) and ("yt-dlp" in combined)

    ok = bool(runnable and detected)
    if ok:
        msg = "yt-dlp is available."
    else:
        msg = "yt-dlp was found but does not appear to be a valid yt-dlp executable."

    if not runnable:
        details = err.strip() or "command failed"
        msg = f"yt-dlp was found but could not be executed: {details}"

    return BinaryCheckResult(
        name="yt-dlp",
        path=path,
        exists=True,
        runnable=runnable,
        detected=detected,
        version=version,
        major=None,
        ok=ok,
        message=msg,
    )


def check_ffmpeg(min_major: int = 6) -> BinaryCheckResult:
    path = resolve_ffmpeg_binary_path()

    if not path:
        return BinaryCheckResult(
            name="ffmpeg",
            path="",
            exists=False,
            runnable=False,
            detected=False,
            version=None,
            major=None,
            ok=False,
            message="FFmpeg path is not configured. Use Get/Update Utilities to download FFmpeg.",
        )

    exists = os.path.exists(path)
    if not exists:
        return BinaryCheckResult(
            name="ffmpeg",
            path=path,
            exists=False,
            runnable=False,
            detected=False,
            version=None,
            major=None,
            ok=False,
            message="FFmpeg was not found at the configured path. Use Get/Update Utilities to install FFmpeg.",
        )

    rc, out, err = _run_command([path, "-version"])
    runnable = rc == 0
    combined = (out + "\n" + err).strip()
    lower = combined.lower()

    detected = "ffmpeg version" in lower

    first_line = combined.splitlines()[0].strip() if combined.splitlines() else ""
    version = first_line if first_line else None

    m = re.search(r"ffmpeg version\s+n?(\d+)", lower)
    major = int(m.group(1)) if m else None

    meets = major is not None and major >= min_major
    ok = bool(runnable and detected and meets)

    if not runnable:
        details = err.strip() or "command failed"
        msg = f"FFmpeg was found but could not be executed: {details}"
    elif not detected:
        msg = "FFmpeg was found but does not appear to be a valid ffmpeg executable."
    elif not meets:
        found = str(major) if major is not None else "unknown"
        msg = f"FFmpeg version is not sufficient. Required {min_major}.x+, found {found}."
    else:
        msg = "FFmpeg is available and meets the minimum version requirement."

    return BinaryCheckResult(
        name="ffmpeg",
        path=path,
        exists=True,
        runnable=runnable,
        detected=detected,
        version=version,
        major=major,
        ok=ok,
        message=msg,
    )


def check_ffprobe(min_major: int = 6) -> BinaryCheckResult:
    path = resolve_ffprobe_binary_path()

    if not path:
        return BinaryCheckResult(
            name="ffprobe",
            path="",
            exists=False,
            runnable=False,
            detected=False,
            version=None,
            major=None,
            ok=False,
            message="ffprobe path is not configured. Use Get/Update Utilities to download FFmpeg (ffprobe ships alongside it).",
        )

    exists = os.path.exists(path)
    if not exists:
        return BinaryCheckResult(
            name="ffprobe",
            path=path,
            exists=False,
            runnable=False,
            detected=False,
            version=None,
            major=None,
            ok=False,
            message="ffprobe was not found at the configured path. Use Get/Update Utilities to install FFmpeg.",
        )

    rc, out, err = _run_command([path, "-version"])
    runnable = rc == 0
    combined = (out + "\n" + err).strip()
    lower = combined.lower()

    detected = "ffprobe version" in lower

    first_line = combined.splitlines()[0].strip() if combined.splitlines() else ""
    version = first_line if first_line else None

    m = re.search(r"ffprobe version\s+n?(\d+)", lower)
    major = int(m.group(1)) if m else None

    meets = major is not None and major >= min_major
    ok = bool(runnable and detected and meets)

    if not runnable:
        details = err.strip() or "command failed"
        msg = f"ffprobe was found but could not be executed: {details}"
    elif not detected:
        msg = "ffprobe was found but does not appear to be a valid ffprobe executable."
    elif not meets:
        found = str(major) if major is not None else "unknown"
        msg = f"ffprobe version is not sufficient. Required {min_major}.x+, found {found}."
    else:
        msg = "ffprobe is available and meets the minimum version requirement."

    return BinaryCheckResult(
        name="ffprobe",
        path=path,
        exists=True,
        runnable=runnable,
        detected=detected,
        version=version,
        major=major,
        ok=ok,
        message=msg,
    )


def show_binary_check_result(parent: Optional[QWidget], result: BinaryCheckResult, title: Optional[str] = None):
    window_title = title or f"{result.name} Check"

    details = []
    if result.path:
        details.append(f"Path: {result.path}")
    if result.version:
        details.append(f"Version: {result.version}")

    text = result.message
    if details:
        text = text + "\n\n" + "\n".join(details)

    if result.ok:
        QMessageBox.information(parent, window_title, text)
    else:
        QMessageBox.critical(parent, window_title, text)


def ensure_ytdlp_available(parent: Optional[QWidget] = None, show_message: bool = True) -> bool:
    result = check_ytdlp()
    if result.ok:
        return True
    if show_message:
        show_binary_check_result(parent, result, "yt-dlp Not Available")
    return False


def ensure_ffmpeg_available(parent: Optional[QWidget] = None, show_message: bool = True, min_major: int = 6) -> bool:
    result = check_ffmpeg(min_major=min_major)
    if result.ok:
        return True
    if show_message:
        show_binary_check_result(parent, result, "FFmpeg Not Available")
    return False


def ensure_ffprobe_available(parent: Optional[QWidget] = None, show_message: bool = True, min_major: int = 6) -> bool:
    result = check_ffprobe(min_major=min_major)
    if result.ok:
        return True
    if show_message:
        show_binary_check_result(parent, result, "ffprobe Not Available")
    return False


def prefs_keys_present() -> dict[str, bool]:
    keys = ["yt-dlp_path", "ffmpeg_binary"]
    return {
        f"app_config.prefs:{k}": k in app_prefs.prefs
        for k in keys
    } | {
        f"app_constance.prefs_dict:{k}": k in prefs_dict.prefs
        for k in keys
    }

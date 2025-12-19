import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional, Tuple

from PySide6.QtWidgets import QMessageBox, QWidget

from app_config import prefs as app_prefs
from app_constance import prefs_dict


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


def resolve_ytdlp_binary_path() -> str:
    base = _get_pref_value("yt-dlp_path", "")
    exe_name = "yt-dlp" + (".exe" if sys.platform == "win32" else "")

    if not base:
        return ""

    candidate = base
    if os.path.isdir(candidate):
        candidate = os.path.join(candidate, exe_name)

    return os.path.normpath(candidate)


def resolve_ffmpeg_binary_path() -> str:
    path = _get_pref_value("ffmpeg_binary", "")
    return os.path.normpath(path) if path else ""


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
            message="FFmpeg path is not configured.",
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
            message="FFmpeg was not found at the configured path.",
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


def prefs_keys_present() -> dict[str, bool]:
    keys = ["yt-dlp_path", "ffmpeg_binary"]
    return {
        f"app_config.prefs:{k}": k in app_prefs.prefs
        for k in keys
    } | {
        f"app_constance.prefs_dict:{k}": k in prefs_dict.prefs
        for k in keys
    }

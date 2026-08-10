from __future__ import annotations

import platform as _platform

from media_core.av_capture.backends.base import CaptureBackend, InputSpec

CURRENT_OS = _platform.system()  # "Windows" / "Darwin" / "Linux"


def create_backend(ffmpeg_executable: str = "ffmpeg") -> CaptureBackend:
    if CURRENT_OS == "Windows":
        from media_core.av_capture.backends.windows_backend import WindowsBackend
        return WindowsBackend(ffmpeg_executable)
    if CURRENT_OS == "Darwin":
        from media_core.av_capture.backends.macos_backend import MacOSBackend
        return MacOSBackend(ffmpeg_executable)
    if CURRENT_OS == "Linux":
        from media_core.av_capture.backends.linux_backend import LinuxBackend
        return LinuxBackend(ffmpeg_executable)
    return CaptureBackend(ffmpeg_executable)  # unknown platform: everything reports unavailable


__all__ = ["CURRENT_OS", "CaptureBackend", "InputSpec", "create_backend"]

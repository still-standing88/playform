"""ctypes-only Win32 monitor/window enumeration.

Neither `gdigrab` nor ffmpeg in general has a device-listing mechanism for
monitors or windows (unlike dshow) - the gdigrab manual just says "capture
a region of the display" / "capture the contents of a single window" and
leaves picking that region/window to the caller. This is the platform-native
half of that: WinAPI EnumDisplayMonitors/EnumWindows, no PySide6/Qt import
so media_core stays framework-agnostic. Only imported on win32 (guarded by
the `try/except ImportError` in windows_backend.py, and by CURRENT_OS gating
in capabilities.py before that).
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

DWMWA_CLOAKED = 14
MONITORINFOF_PRIMARY = 0x1


class _MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


def enum_monitors() -> list[dict]:
    monitors: list[dict] = []

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
    )

    def _callback(hmonitor, hdc, rect_ptr, data):
        info = _MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(_MONITORINFOEXW)
        if user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            rect = info.rcMonitor
            monitors.append({
                "left": rect.left, "top": rect.top, "right": rect.right, "bottom": rect.bottom,
                "primary": bool(info.dwFlags & MONITORINFOF_PRIMARY),
                "device": info.szDevice,
            })
        return True

    user32.EnumDisplayMonitors(None, None, MonitorEnumProc(_callback), 0)
    monitors.sort(key=lambda m: (not m["primary"], m["left"], m["top"]))
    return monitors


def _is_cloaked(hwnd) -> bool:
    cloaked = wintypes.DWORD(0)
    try:
        dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
    except OSError:
        return False
    return bool(cloaked.value)


def enum_windows() -> list[tuple[int, str]]:
    results: list[tuple[int, str]] = []

    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _callback(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.GetWindowTextLengthW(hwnd) == 0:
            return True
        if user32.GetAncestor(hwnd, 3) != hwnd:  # GA_ROOTOWNER = 3 - skip non-top-level windows
            return True
        if _is_cloaked(hwnd):  # suspended UWP windows report visible but paint nothing
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()
        if title:
            results.append((int(hwnd), title))
        return True

    user32.EnumWindows(EnumWindowsProc(_callback), 0)
    return results

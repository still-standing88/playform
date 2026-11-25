import logging
import sys

from PySide6.QtCore import QObject, QEvent, QTimer
from PySide6.QtGui import QGuiApplication


logger = logging.getLogger(__name__)
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
LWA_ALPHA = 2


class NativeVideoInput(QObject):
    """Let Qt receive input through mpv's Windows child window."""

    def __init__(self, surface, enabled=True):
        super().__init__(surface)
        self.surface = surface
        self.enabled = enabled
        self._windows = {}
        self._attempts = 0
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._refresh)
        surface.installEventFilter(self)
        self.refresh()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.WinIdChange, QEvent.Type.Show):
            self.refresh()
        return False

    def set_enabled(self, enabled):
        self.enabled = enabled
        self._timer.stop()
        if enabled:
            self.refresh()
        else:
            self._restore()

    def refresh(self):
        if self.enabled and sys.platform == "win32" and QGuiApplication.platformName() == "windows":
            self._attempts = 30
            self._timer.start()

    @staticmethod
    def _api():
        import ctypes
        from ctypes import wintypes
        api = ctypes.WinDLL("user32", use_last_error=True)
        api.GetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int)
        api.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        api.SetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t)
        api.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        api.GetClassNameW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
        api.IsWindow.argtypes = (wintypes.HWND,)
        api.IsChild.argtypes = (wintypes.HWND, wintypes.HWND)
        api.SetLayeredWindowAttributes.argtypes = (wintypes.HWND, wintypes.DWORD, wintypes.BYTE, wintypes.DWORD)
        return api

    def _refresh(self):
        import ctypes
        from ctypes import wintypes
        api = self._api()
        parent = int(self.surface.winId())
        self._windows = {handle: entry for handle, entry in self._windows.items() if api.IsWindow(handle)}
        matched = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def visit(handle, data):
            name = ctypes.create_unicode_buffer(256)
            api.GetClassNameW(handle, name, len(name))
            if name.value == "mpv":
                matched.append(int(handle))
            return True

        api.EnumChildWindows.argtypes = (wintypes.HWND, callback_type, wintypes.LPARAM)
        api.EnumChildWindows(parent, callback_type(visit), 0)
        for handle in matched:
            style = api.GetWindowLongPtrW(handle, GWL_EXSTYLE)
            added = self._windows.get(handle, (parent, (WS_EX_LAYERED | WS_EX_TRANSPARENT) & ~style))[1]
            # mpv deliberately skips input-cursor-passthrough in --wid mode.
            # A layered, input-transparent child lets the Qt parent receive
            # real touchscreen input without subclassing mpv's window proc.
            ctypes.set_last_error(0)
            api.SetWindowLongPtrW(handle, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
            if ctypes.get_last_error():
                logger.error("Could not enable native video input passthrough: %s", ctypes.get_last_error())
                continue
            if added & WS_EX_LAYERED and not api.SetLayeredWindowAttributes(handle, 0, 255, LWA_ALPHA):
                api.SetWindowLongPtrW(handle, GWL_EXSTYLE, style)
                logger.error("Could not enable layered video window: %s", ctypes.get_last_error())
                continue
            self._windows[handle] = (parent, added)
        self._attempts -= 1
        if matched or self._attempts <= 0:
            self._timer.stop()

    def _restore(self):
        if not self._windows:
            return
        api = self._api()
        for handle, (parent, added) in self._windows.items():
            if api.IsWindow(handle) and api.IsChild(parent, handle):
                style = api.GetWindowLongPtrW(handle, GWL_EXSTYLE)
                api.SetWindowLongPtrW(handle, GWL_EXSTYLE, style & ~added)
        self._windows.clear()

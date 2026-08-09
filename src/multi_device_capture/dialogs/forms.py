"""Per-media-type settings forms used by page 2 of the Source wizard and by
the Settings tab's global-defaults panel.

Only exposes fields QtMultimedia actually backs (see
platform_capabilities.PlatformCapabilities docstrings / the *_note() methods
for what's deliberately left out and why).
"""
from __future__ import annotations

from PySide6.QtMultimedia import QAudioDevice, QCameraDevice
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QSpinBox, QWidget

from ..platform_capabilities import PlatformCapabilities


class AudioSettingsForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        form = QFormLayout(self)
        self.sample_rate = QComboBox()
        self.sample_rate.setAccessibleName(_("Sample rate"))
        self.sample_rate.addItems(["44100", "48000", "96000"])
        self.channels = QComboBox()
        self.channels.setAccessibleName(_("Channels"))
        self.channels.addItems([_("Mono"), _("Stereo")])
        self.volume = QSpinBox()
        self.volume.setRange(0, 100)
        self.volume.setValue(100)
        self.volume.setSuffix(" %")
        form.addRow(_("Sample rate (Hz)"), self.sample_rate)
        form.addRow(_("Channels"), self.channels)
        form.addRow(_("Volume"), self.volume)

    def load_device_defaults(self, dev: QAudioDevice) -> None:
        preferred = dev.preferredFormat()
        rate_str = str(preferred.sampleRate())
        idx = self.sample_rate.findText(rate_str)
        if idx < 0:
            self.sample_rate.insertItem(0, rate_str)
            idx = 0
        self.sample_rate.setCurrentIndex(idx)
        self.channels.setCurrentIndex(0 if preferred.channelCount() == 1 else 1)

    def to_settings(self) -> dict:
        return {
            "sample_rate": int(self.sample_rate.currentText()),
            "channels": 1 if self.channels.currentIndex() == 0 else 2,
            "volume": self.volume.value(),
        }

    def from_settings(self, s: dict) -> None:
        if "sample_rate" in s:
            idx = self.sample_rate.findText(str(s["sample_rate"]))
            if idx >= 0:
                self.sample_rate.setCurrentIndex(idx)
        if "channels" in s:
            self.channels.setCurrentIndex(0 if s["channels"] == 1 else 1)
        if "volume" in s:
            self.volume.setValue(s["volume"])


class CameraSettingsForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        form = QFormLayout(self)
        self.resolution = QComboBox()
        self.resolution.setAccessibleName(_("Resolution"))
        self.fps = QComboBox()
        self.fps.setAccessibleName(_("Frame rate"))
        form.addRow(_("Resolution"), self.resolution)
        form.addRow(_("Frame rate"), self.fps)
        self._formats = []

    def load_device_formats(self, dev: QCameraDevice) -> None:
        self.resolution.clear()
        self._formats = list(dev.videoFormats())
        seen = set()
        for fmt in self._formats:
            res = fmt.resolution()
            key = (res.width(), res.height())
            if key in seen:
                continue
            seen.add(key)
            self.resolution.addItem(f"{res.width()}x{res.height()}", key)
        self.resolution.currentIndexChanged.connect(self._refresh_fps)
        if self.resolution.count():
            self._refresh_fps(0)

    def _refresh_fps(self, index: int) -> None:
        self.fps.clear()
        target = self.resolution.itemData(index)
        if target is None:
            return
        seen = set()
        for fmt in self._formats:
            res = fmt.resolution()
            if (res.width(), res.height()) != target:
                continue
            lo, hi = fmt.minFrameRate(), fmt.maxFrameRate()
            for candidate in (lo, hi):
                r = round(candidate)
                if r and r not in seen:
                    seen.add(r)
                    self.fps.addItem(str(r), r)

    def to_settings(self) -> dict:
        res = self.resolution.currentData()
        return {
            "resolution": f"{res[0]}x{res[1]}" if res else "",
            "fps": self.fps.currentData() or 0,
        }

    def from_settings(self, s: dict) -> None:
        if "resolution" in s:
            idx = self.resolution.findText(s["resolution"])
            if idx >= 0:
                self.resolution.setCurrentIndex(idx)
        if "fps" in s:
            idx = self.fps.findText(str(s["fps"]))
            if idx >= 0:
                self.fps.setCurrentIndex(idx)


class ScreenSettingsForm(QWidget):
    """QScreenCapture exposes essentially no configurable properties.
    Cursor visibility / crop / FPS cap are NOT backed by Qt Multimedia and
    are intentionally omitted here rather than shown as fake controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        form = QFormLayout(self)
        self.screen_label = QLabel("-")
        form.addRow(_("Screen"), self.screen_label)
        note = QLabel(PlatformCapabilities.screen_capture_note())
        note.setStyleSheet("color: gray; font-size: 11px;")
        note.setWordWrap(True)
        form.addRow(note)

    def load_screen(self, screen) -> None:
        self.screen_label.setText(f"{screen.name()} ({screen.geometry().width()}x{screen.geometry().height()})")

    def to_settings(self) -> dict:
        return {"screen_name": self.screen_label.text()}

    def from_settings(self, s: dict) -> None:
        if "screen_name" in s:
            self.screen_label.setText(s["screen_name"])


class WindowSettingsForm(QWidget):
    """Same limitation as ScreenSettingsForm - QWindowCapture has no crop,
    no cursor toggle, no FPS control in the public API."""

    def __init__(self, parent=None):
        super().__init__(parent)
        form = QFormLayout(self)
        self.window_label = QLabel("-")
        form.addRow(_("Window"), self.window_label)
        note = QLabel(PlatformCapabilities.window_capture_note())
        note.setStyleSheet("color: gray; font-size: 11px;")
        note.setWordWrap(True)
        form.addRow(note)

    def load_window(self, win) -> None:
        self.window_label.setText(win.description())

    def to_settings(self) -> dict:
        return {}

    def from_settings(self, s: dict) -> None:
        pass

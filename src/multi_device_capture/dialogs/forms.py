"""Per-media-type settings forms used by page 2 of the Source wizard and by
the Settings tab's global-defaults panel.

Every field here maps directly onto an option the active
media_core.av_capture backend actually passes to ffmpeg (see
backends/*.build_input()) - nothing is shown that the current
platform/device can't back. Monitor/Window capture now expose real
"Capture cursor" and frame-rate controls (gdigrab's draw_mouse/framerate,
x11grab's draw_mouse/framerate, avfoundation's capture_cursor/framerate),
which is a genuine capability gain over the previous QtMultimedia-based
QScreenCapture/QWindowCapture, which exposed neither.
"""
from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QLabel, QSpinBox, QWidget

from media_core.av_capture.capabilities import CaptureCapabilities
from media_core.av_capture.models import CaptureDevice


class AudioSettingsForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        form = QFormLayout(self)
        self.sample_rate = QComboBox()
        self.sample_rate.setAccessibleName(_("Sample rate"))
        self.sample_rate.addItems(["44100", "48000", "96000"])
        self.sample_rate.setCurrentText("48000")
        self.channels = QComboBox()
        self.channels.setAccessibleName(_("Channels"))
        self.channels.addItems([_("Mono"), _("Stereo")])
        self.channels.setCurrentIndex(1)
        self.volume = QSpinBox()
        self.volume.setRange(0, 100)
        self.volume.setValue(100)
        self.volume.setSuffix(" %")
        form.addRow(_("Sample rate (Hz)"), self.sample_rate)
        form.addRow(_("Channels"), self.channels)
        form.addRow(_("Volume"), self.volume)

    def load_device_defaults(self, device: CaptureDevice) -> None:
        # ffmpeg's device-listing mechanisms (dshow/pulse/avfoundation) don't
        # report a single "preferred" format the way QAudioDevice did - the
        # dshow -list_options probe *does* enumerate exact supported
        # (rate, channels) pairs, but doing that on every wizard page visit
        # means spinning up an extra ffmpeg process per device; the sane
        # default (48kHz stereo) covers virtually every capture device, and
        # the fields stay user-editable exactly as before.
        pass

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

    def load_device_formats(self, capabilities: CaptureCapabilities, device: CaptureDevice) -> None:
        self.resolution.clear()
        self._formats = capabilities.camera_formats(device)
        seen = set()
        for fmt in self._formats:
            if fmt.resolution in seen:
                continue
            seen.add(fmt.resolution)
            self.resolution.addItem(fmt.resolution, fmt.resolution)
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
            if fmt.resolution != target:
                continue
            fps_value = round(fmt.fps) if fmt.fps else 0
            if not fps_value or fps_value in seen:
                continue
            seen.add(fps_value)
            self.fps.addItem(str(fps_value), fps_value)

    def to_settings(self) -> dict:
        resolution = self.resolution.currentData()
        settings = {"resolution": resolution or "", "fps": self.fps.currentData() or 0}
        matching = [f for f in self._formats if f.resolution == resolution and round(f.fps or 0) == settings["fps"]]
        if matching:
            settings["pixel_format"] = matching[0].pixel_format
            settings["codec"] = matching[0].codec
        return settings

    def from_settings(self, s: dict) -> None:
        if "resolution" in s:
            idx = self.resolution.findText(s["resolution"])
            if idx >= 0:
                self.resolution.setCurrentIndex(idx)
        if "fps" in s:
            idx = self.fps.findText(str(s["fps"]))
            if idx >= 0:
                self.fps.setCurrentIndex(idx)


class _FrameCaptureSettingsForm(QWidget):
    """Shared by Monitor/Window: both are gdigrab/x11grab/avfoundation
    inputs with the same real, ffmpeg-backed knobs - a frame-rate cap and a
    cursor-visibility toggle (draw_mouse / capture_cursor)."""

    _LABEL_ROW = ""

    def __init__(self, parent=None):
        super().__init__(parent)
        form = QFormLayout(self)
        self.device_label = QLabel("-")
        form.addRow(self._LABEL_ROW, self.device_label)
        self.fps = QSpinBox()
        self.fps.setRange(1, 60)
        self.fps.setValue(30)
        form.addRow(_("Frame rate"), self.fps)
        self.capture_cursor = QCheckBox(_("Capture mouse cursor"))
        self.capture_cursor.setChecked(True)
        form.addRow(self.capture_cursor)
        self._note_label = QLabel("")
        self._note_label.setStyleSheet("color: gray; font-size: 11px;")
        self._note_label.setWordWrap(True)
        form.addRow(self._note_label)

    def set_note(self, text: str) -> None:
        self._note_label.setText(text)
        self._note_label.setVisible(bool(text))

    def to_settings(self) -> dict:
        return {"fps": self.fps.value(), "capture_cursor": self.capture_cursor.isChecked()}

    def from_settings(self, s: dict) -> None:
        if "fps" in s and s["fps"]:
            self.fps.setValue(int(s["fps"]))
        if "capture_cursor" in s:
            self.capture_cursor.setChecked(bool(s["capture_cursor"]))


class ScreenSettingsForm(_FrameCaptureSettingsForm):
    _LABEL_ROW = _("Screen")

    def load_screen(self, device: CaptureDevice, capabilities: CaptureCapabilities) -> None:
        self.device_label.setText(device.name)
        self.set_note(capabilities.screen_capture_note())

    def to_settings(self) -> dict:
        settings = super().to_settings()
        settings["screen_name"] = self.device_label.text()
        return settings


class WindowSettingsForm(_FrameCaptureSettingsForm):
    _LABEL_ROW = _("Window")

    def load_window(self, device: CaptureDevice, capabilities: CaptureCapabilities) -> None:
        self.device_label.setText(device.name)
        self.set_note(capabilities.window_capture_note())

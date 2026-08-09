from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QListWidget,
    QSpinBox,
    QStackedWidget,
    QWidget,
)

from ..dialogs.forms import AudioSettingsForm
from ..settings import MultiDeviceCaptureSettings


class SettingsTab(QWidget):
    """Global audio/video defaults a session falls back to unless it defines
    its own settings_override. Persisted to
    data/multi_device_capture_settings.json (see settings.py)."""

    def __init__(self, settings: MultiDeviceCaptureSettings, parent=None):
        super().__init__(parent)
        self.settings = settings

        layout = QHBoxLayout(self)

        self.category_list = QListWidget()
        self.category_list.addItems([_("Audio"), _("Video")])
        self.category_list.setMaximumWidth(140)
        layout.addWidget(self.category_list)

        self.stack = QStackedWidget()
        self.audio_defaults = AudioSettingsForm()
        self.video_defaults_box, self.res_cap, self.fps, self.cursor = self._build_video_defaults()
        self.stack.addWidget(self.audio_defaults)
        self.stack.addWidget(self.video_defaults_box)
        layout.addWidget(self.stack, 1)

        self.category_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.category_list.setCurrentRow(0)

        self._load_from_settings()

        self.audio_defaults.sample_rate.currentIndexChanged.connect(self._save_audio)
        self.audio_defaults.channels.currentIndexChanged.connect(self._save_audio)
        self.audio_defaults.volume.valueChanged.connect(self._save_audio)
        self.res_cap.currentIndexChanged.connect(self._save_video)
        self.fps.valueChanged.connect(self._save_video)
        self.cursor.toggled.connect(self._save_video)

    def _build_video_defaults(self):
        w = QWidget()
        form = QFormLayout(w)
        res_cap = QComboBox()
        res_cap.addItems(["Passthrough", "1920x1080", "1280x720"])
        fps = QSpinBox()
        fps.setRange(1, 240)
        fps.setValue(30)
        cursor = QCheckBox(_("Capture cursor (applied in post-process, not Qt-native)"))
        form.addRow(_("Resolution cap"), res_cap)
        form.addRow(_("Frame rate"), fps)
        form.addRow(cursor)
        return w, res_cap, fps, cursor

    def _load_from_settings(self) -> None:
        audio = self.settings.get_audio()
        self.audio_defaults.from_settings(audio)

        video = self.settings.get_video()
        idx = self.res_cap.findText(video.get("resolution_cap", "Passthrough"))
        if idx >= 0:
            self.res_cap.setCurrentIndex(idx)
        self.fps.setValue(video.get("fps", 30))
        self.cursor.setChecked(video.get("capture_cursor", False))

    def _save_audio(self) -> None:
        self.settings.set_audio(self.audio_defaults.to_settings())

    def _save_video(self) -> None:
        self.settings.set_video({
            "resolution_cap": self.res_cap.currentText(),
            "fps": self.fps.value(),
            "capture_cursor": self.cursor.isChecked(),
        })

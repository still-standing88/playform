from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..dialogs.forms import AudioSettingsForm
from ..models import default_capture_directory
from ..settings import MultiDeviceCaptureSettings


class SettingsDialog(QDialog):
    def __init__(self, settings: MultiDeviceCaptureSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Multi Device Capture Settings"))
        self.settings = settings
        self.resize(520, 360)

        layout = QVBoxLayout(self)

        body = QHBoxLayout()
        self.category_list = QListWidget()
        self.category_list.addItems([_("General"), _("Audio defaults"), _("Video defaults")])
        self.category_list.setMaximumWidth(140)
        body.addWidget(self.category_list)

        self.stack = QStackedWidget()
        self.general_page = self._build_general_page()
        self.audio_defaults = AudioSettingsForm()
        self.video_defaults_page, self.res_cap, self.fps, self.cursor = self._build_video_page()
        self.stack.addWidget(self.general_page)
        self.stack.addWidget(self.audio_defaults)
        self.stack.addWidget(self.video_defaults_page)
        body.addWidget(self.stack, 1)
        layout.addLayout(body)

        self.category_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.category_list.setCurrentRow(0)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self._load_from_settings()

        self.output_dir_edit.editingFinished.connect(self._save_general)
        self.container_combo.currentIndexChanged.connect(self._save_general)
        self.notify_checkbox.toggled.connect(self._save_general)
        self.audio_defaults.sample_rate.currentIndexChanged.connect(self._save_audio)
        self.audio_defaults.channels.currentIndexChanged.connect(self._save_audio)
        self.audio_defaults.volume.valueChanged.connect(self._save_audio)
        self.res_cap.currentIndexChanged.connect(self._save_video)
        self.fps.valueChanged.connect(self._save_video)
        self.cursor.toggled.connect(self._save_video)

    def _build_general_page(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self.output_dir_edit = QLineEdit()
        browse_row = QHBoxLayout()
        browse_row.addWidget(self.output_dir_edit)
        browse_btn = QPushButton(_("Browse"))
        browse_btn.clicked.connect(self._browse_output_dir)
        browse_row.addWidget(browse_btn)
        form.addRow(_("Default output directory"), browse_row)

        self.container_combo = QComboBox()
        self.container_combo.addItems(["mkv", "mp4", "mov"])
        form.addRow(_("Default container format"), self.container_combo)

        self.notify_checkbox = QCheckBox(_("Notify (system tray) when a capture finishes"))
        form.addRow(self.notify_checkbox)

        return w

    def _build_video_page(self):
        w = QWidget()
        form = QFormLayout(w)
        res_cap = QComboBox()
        # Labels are translated; the setting keeps the untranslated value.
        res_cap.addItem(_("Passthrough"), "Passthrough")
        for value in ("1920x1080", "1280x720"):
            res_cap.addItem(value, value)
        fps = QSpinBox()
        fps.setRange(1, 240)
        fps.setValue(30)
        cursor = QCheckBox(_("Capture cursor by default (each Monitor/Window source can still override this)"))
        form.addRow(_("Resolution cap"), res_cap)
        form.addRow(_("Frame rate"), fps)
        form.addRow(cursor)
        return w, res_cap, fps, cursor

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, _("Select default output directory"))
        if path:
            self.output_dir_edit.setText(path)

    def _load_from_settings(self) -> None:
        self.output_dir_edit.setText(self.settings.get("default_output_dir", ""))
        self.output_dir_edit.setPlaceholderText(default_capture_directory())
        self.container_combo.setCurrentText(self.settings.get("default_container", "mkv"))
        self.notify_checkbox.setChecked(bool(self.settings.get("notify_on_finish", True)))

        audio = self.settings.get_audio()
        self.audio_defaults.from_settings(audio)

        video = self.settings.get_video()
        idx = self.res_cap.findData(video.get("resolution_cap", "Passthrough"))
        if idx >= 0:
            self.res_cap.setCurrentIndex(idx)
        self.fps.setValue(video.get("fps", 30))
        self.cursor.setChecked(video.get("capture_cursor", False))

    def _save_general(self) -> None:
        self.settings.set("default_output_dir", self.output_dir_edit.text())
        self.settings.set("default_container", self.container_combo.currentText())
        self.settings.set("notify_on_finish", self.notify_checkbox.isChecked())

    def _save_audio(self) -> None:
        self.settings.set_audio(self.audio_defaults.to_settings())

    def _save_video(self) -> None:
        self.settings.set_video({
            "resolution_cap": self.res_cap.currentData(),
            "fps": self.fps.value(),
            "capture_cursor": self.cursor.isChecked(),
        })

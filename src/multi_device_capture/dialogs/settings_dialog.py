"""Shared/general settings dialog - device-agnostic knobs that apply across
every source rather than one device's own wizard page:

- Default output directory / container - prefilled into the "New session"
  dialog, not retroactively applied to existing sessions.
- Default audio/video prefill (sample rate/channels/volume, fps/cursor) -
  seeded into the Add Source wizard's Settings page for a *new* source of
  that kind; editing an existing source doesn't re-read these.
- Notify on finish - posts through the app's tray icon
  (QApplication.instance()._tray_icon), same pattern as
  tools.ffmpeg.batch_converter's progress dialog.
- Keep segment files after a paused session - session_runner.py normally
  deletes per-segment files once they're concatenated into the final
  output; this keeps them as a safety net.

Was the Settings tab; now a modal dialog opened from a button instead of a
third tab, since the panel is a single consolidated view now (see
views/configure_view.py).
"""
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
        self.keep_segments_checkbox.toggled.connect(self._save_general)
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

        self.keep_segments_checkbox = QCheckBox(_("Keep intermediate segment files after a paused session"))
        self.keep_segments_checkbox.setToolTip(
            _("Pausing splits a recording into segments that are joined into one file on Stop. "
              "Enable this to keep the individual segment files as a backup instead of deleting them.")
        )
        form.addRow(self.keep_segments_checkbox)
        return w

    def _build_video_page(self):
        w = QWidget()
        form = QFormLayout(w)
        res_cap = QComboBox()
        res_cap.addItems(["Passthrough", "1920x1080", "1280x720"])
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
        self.container_combo.setCurrentText(self.settings.get("default_container", "mkv"))
        self.notify_checkbox.setChecked(bool(self.settings.get("notify_on_finish", True)))
        self.keep_segments_checkbox.setChecked(bool(self.settings.get("keep_segments_after_pause", False)))

        audio = self.settings.get_audio()
        self.audio_defaults.from_settings(audio)

        video = self.settings.get_video()
        idx = self.res_cap.findText(video.get("resolution_cap", "Passthrough"))
        if idx >= 0:
            self.res_cap.setCurrentIndex(idx)
        self.fps.setValue(video.get("fps", 30))
        self.cursor.setChecked(video.get("capture_cursor", False))

    def _save_general(self) -> None:
        self.settings.set("default_output_dir", self.output_dir_edit.text())
        self.settings.set("default_container", self.container_combo.currentText())
        self.settings.set("notify_on_finish", self.notify_checkbox.isChecked())
        self.settings.set("keep_segments_after_pause", self.keep_segments_checkbox.isChecked())

    def _save_audio(self) -> None:
        self.settings.set_audio(self.audio_defaults.to_settings())

    def _save_video(self) -> None:
        self.settings.set_video({
            "resolution_cap": self.res_cap.currentText(),
            "fps": self.fps.value(),
            "capture_cursor": self.cursor.isChecked(),
        })

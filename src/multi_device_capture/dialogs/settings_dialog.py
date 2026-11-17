from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLineEdit, QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from media_core.av_capture.models import AUDIO_CONTAINERS, VIDEO_CONTAINERS

from ..models import default_capture_directory
from ..settings import MultiDeviceCaptureSettings
from .forms import AudioSettingsForm, VideoSettingsForm


class SettingsDialog(QDialog):
    def __init__(self, settings: MultiDeviceCaptureSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Multi Device Capture Settings"))
        self.settings = settings
        self.resize(520, 360)

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        general = QWidget()
        form = QFormLayout(general)
        self.output_dir_edit = QLineEdit(settings.get("default_output_dir", ""))
        self.output_dir_edit.setPlaceholderText(default_capture_directory())
        browse_row = QHBoxLayout()
        browse_row.addWidget(self.output_dir_edit)
        browse_button = QPushButton(_("Browse…"))
        browse_button.clicked.connect(self._browse_output_dir)
        browse_row.addWidget(browse_button)
        form.addRow(_("Default output folder"), browse_row)

        formats = settings.get_output_formats()
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(AUDIO_CONTAINERS)
        self.audio_format_combo.setCurrentText(formats["audio_format"])
        form.addRow(_("Default audio-only format"), self.audio_format_combo)

        self.video_format_combo = QComboBox()
        self.video_format_combo.addItems(VIDEO_CONTAINERS)
        self.video_format_combo.setCurrentText(formats["video_format"])
        form.addRow(_("Default video format"), self.video_format_combo)

        self.notify_checkbox = QCheckBox(_("Notify when capture finishes"))
        self.notify_checkbox.setChecked(settings.get("notify_on_finish", True))
        form.addRow(self.notify_checkbox)
        tabs.addTab(general, _("General"))

        self.audio_defaults = AudioSettingsForm()
        self.audio_defaults.from_settings(settings.get_audio())
        tabs.addTab(self.audio_defaults, _("Audio defaults"))

        self.video_defaults = VideoSettingsForm()
        self.video_defaults.from_settings(settings.get_video())
        tabs.addTab(self.video_defaults, _("Video defaults"))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_output_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, _("Select default output folder"), self.output_dir_edit.text().strip() or default_capture_directory(),
        )
        if path:
            self.output_dir_edit.setText(path)

    def accept(self):
        if self.settings.update({
            "default_output_dir": self.output_dir_edit.text().strip(),
            "audio_format": self.audio_format_combo.currentText(),
            "video_format": self.video_format_combo.currentText(),
            "notify_on_finish": self.notify_checkbox.isChecked(),
            "audio": self.audio_defaults.to_settings(),
            "video": self.video_defaults.to_settings(),
        }):
            super().accept()
        else:
            QMessageBox.warning(self, _("Capture settings"), _("Could not save capture settings."))

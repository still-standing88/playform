from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLineEdit, QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from media_core.av_capture.mediacap import AUDIO_CONTAINERS, VIDEO_CONTAINERS

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

        self.container_combo = QComboBox()
        self.container_combo.addItems(VIDEO_CONTAINERS + AUDIO_CONTAINERS)
        container = settings.get("default_container", "mkv")
        self.container_combo.setCurrentText("mp4" if container == "mov" else container)
        form.addRow(_("Default output format"), self.container_combo)

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
            "default_container": self.container_combo.currentText(),
            "notify_on_finish": self.notify_checkbox.isChecked(),
            "audio": self.audio_defaults.to_settings(),
            "video": self.video_defaults.to_settings(),
        }):
            super().accept()
        else:
            QMessageBox.warning(self, _("Capture settings"), _("Could not save capture settings."))

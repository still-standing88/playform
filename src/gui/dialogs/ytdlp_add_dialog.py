"""Add-download prompt for the yt-dlp Download Manager: a URL and a save
location. URL classification (video/playlist/channel/other) happens in
the manager dialog after this accepts."""

import os

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPushButton, QFileDialog, QDialogButtonBox, QMessageBox


class YtDlpAddDialog(QDialog):
    def __init__(self, default_destination: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Add yt-dlp Download"))
        self.setMinimumWidth(480)
        self._default_destination = default_destination
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.url_edit = QLineEdit(self)
        self.url_edit.setAccessibleName(_("Video or playlist URL"))
        self.url_edit.setPlaceholderText(_("https://..."))
        form.addRow(_("URL:"), self.url_edit)

        location_row = QHBoxLayout()
        self.location_edit = QLineEdit(self.location_value())
        self.location_edit.setAccessibleName(_("Save location"))
        browse_button = QPushButton(_("Browse..."), self)
        browse_button.clicked.connect(self._browse)
        location_row.addWidget(self.location_edit)
        location_row.addWidget(browse_button)
        form.addRow(_("Location:"), location_row)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def location_value() -> str:
        from .ytdlp_downloader_dialog import default_ytdlp_destination
        return default_ytdlp_destination()

    def _browse(self):
        directory = QFileDialog.getExistingDirectory(
            self, _("Select Save Location"), self.location_edit.text() or self._default_destination)
        if directory:
            self.location_edit.setText(directory)

    def _on_accept(self):
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.information(self, _("No URL"), _("Enter a video or playlist URL."))
            return
        if not os.path.isdir(self.location_edit.text().strip()):
            QMessageBox.information(self, _("No Location"), _("Choose an existing save location."))
            return
        self.accept()

    def values(self) -> tuple:
        return self.url_edit.text().strip(), self.location_edit.text().strip()

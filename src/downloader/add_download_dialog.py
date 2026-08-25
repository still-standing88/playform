import os
from urllib.parse import urlparse

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton,
                               QHBoxLayout, QDialogButtonBox, QLabel)
from PySide6.QtCore import QUrl

from app_config import prefs
from utilities.formats import formats as media_formats

SUPPORTED_EXTENSIONS = set(media_formats["audio"]) | set(media_formats["video"])


class AddDownloadDialog(QDialog):
    """Add-download dialog accepting only URLs pointing at formats the
    app/player supports (direct URLs; yt-dlp sites are not downloadable)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Add Download"))
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.url_edit = QLineEdit(self)
        self.url_edit.setPlaceholderText(_("https://example.com/file.mp3"))
        form.addRow(_("URL:"), self.url_edit)

        dest_row = QHBoxLayout()
        self.dest_edit = QLineEdit(self)
        default_dir = prefs.prefs.get("download_dir", "")
        self.dest_edit.setText(default_dir)
        browse_btn = QPushButton(_("Browse..."), self)
        browse_btn.clicked.connect(self._browse)
        dest_row.addWidget(self.dest_edit)
        dest_row.addWidget(browse_btn)
        form.addRow(_("Destination:"), dest_row)

        self.filename_edit = QLineEdit(self)
        self.filename_edit.setPlaceholderText(_("Automatic from URL"))
        form.addRow(_("Filename:"), self.filename_edit)

        layout.addLayout(form)

        self.error_label = QLabel(self)
        self.error_label.setStyleSheet("color: #ff6b6b;")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self):
        from PySide6.QtWidgets import QFileDialog
        chosen = QFileDialog.getExistingDirectory(self, _("Select Folder"), self.dest_edit.text() or "")
        if chosen:
            self.dest_edit.setText(chosen)

    def _on_accept(self):
        error = self.validate()
        if error:
            self.error_label.setText(error)
            self.error_label.show()
            return
        self.accept()

    def validate(self):
        url = self.url_edit.text().strip()
        if not url:
            return _("Enter a URL.")
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return _("Enter a valid http(s) URL.")
        # Non-media URLs are allowed through: main_window routes them to
        # the yt-dlp downloader instead of the direct downloader.
        return ""

    def get_values(self):
        url = self.url_edit.text().strip()
        parsed = urlparse(url)
        filename = self.filename_edit.text().strip() or os.path.basename(parsed.path)
        return url, self.dest_edit.text().strip(), filename

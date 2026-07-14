from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QCheckBox, QPushButton, QLabel, QMessageBox

from utilities.formats import formats as media_formats


class DatabasePanel(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self._main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.catalog_audio_cb = QCheckBox(_("Catalog audio files"))
        self.catalog_video_cb = QCheckBox(_("Catalog video files"))
        form.addRow(self.catalog_audio_cb)
        form.addRow(self.catalog_video_cb)
        layout.addLayout(form)

        info_label = QLabel(_(
            "Controls which file types are added to the media database "
            "when a folder is cataloged for search."
        ))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addStretch()

        self.rebuild_button = QPushButton(_("Clear && Rebuild Catalog..."))
        self.rebuild_button.clicked.connect(self._on_rebuild_clicked)
        layout.addWidget(self.rebuild_button)

    def load_settings(self, prefs):
        extensions = set(prefs.get("catalog_extensions", []))
        self.catalog_audio_cb.setChecked(any(ext in extensions for ext in media_formats["audio"]))
        self.catalog_video_cb.setChecked(any(ext in extensions for ext in media_formats["video"]))

    def save_settings(self, prefs):
        extensions = []
        if self.catalog_audio_cb.isChecked():
            extensions.extend(media_formats["audio"])
        if self.catalog_video_cb.isChecked():
            extensions.extend(media_formats["video"])
        prefs["catalog_extensions"] = extensions

    def _on_rebuild_clicked(self):
        if self._main_window is None:
            return
        reply = QMessageBox.question(
            self,
            _("Clear & Rebuild Catalog"),
            _("This clears the entire media database and re-scans every "
              "previously cataloged folder. Continue?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._main_window.rebuild_catalog()

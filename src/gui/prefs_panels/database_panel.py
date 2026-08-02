from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QCheckBox, QPushButton, QLabel,
    QGroupBox
)

from utilities.formats import formats as media_formats


class DatabasePanel(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self._main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        catalog_group = QGroupBox(_("Cataloging"))
        catalog_layout = QVBoxLayout(catalog_group)

        form = QFormLayout()
        self.catalog_audio_cb = QCheckBox(_("Catalog audio files"))
        self.catalog_video_cb = QCheckBox(_("Catalog video files"))
        form.addRow(self.catalog_audio_cb)
        form.addRow(self.catalog_video_cb)
        catalog_layout.addLayout(form)

        info_label = QLabel(_(
            "Controls which file types are added to the media database "
            "when a folder is cataloged for search."
        ))
        info_label.setWordWrap(True)
        catalog_layout.addWidget(info_label)

        layout.addWidget(catalog_group)

        history_group = QGroupBox(_("Search History"))
        history_layout = QVBoxLayout(history_group)

        self.store_search_history_cb = QCheckBox(_("Remember Explorer search history"))
        history_layout.addWidget(self.store_search_history_cb)

        self.clear_history_button = QPushButton(_("Clear Search History"))
        self.clear_history_button.clicked.connect(self._on_clear_history_clicked)
        history_layout.addWidget(self.clear_history_button)

        layout.addWidget(history_group)

        layout.addStretch()

    def load_settings(self, prefs):
        extensions = set(prefs.get("catalog_extensions", []))
        self.catalog_audio_cb.setChecked(any(ext in extensions for ext in media_formats["audio"]))
        self.catalog_video_cb.setChecked(any(ext in extensions for ext in media_formats["video"]))
        self.store_search_history_cb.setChecked(prefs.get("store_search_history", True))

    def save_settings(self, prefs):
        extensions = []
        if self.catalog_audio_cb.isChecked():
            extensions.extend(media_formats["audio"])
        if self.catalog_video_cb.isChecked():
            extensions.extend(media_formats["video"])
        prefs["catalog_extensions"] = extensions
        prefs["store_search_history"] = self.store_search_history_cb.isChecked()

    def _on_clear_history_clicked(self):
        if self._main_window is not None:
            self._main_window.clear_explorer_search_history()

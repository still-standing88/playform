from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, QSpinBox

_IMAGE_FORMATS = {
    "PNG": "png",
    "JPEG": "mjpeg",
    "BMP": "bmp",
    "WebP": "webp",
    "TIFF": "tiff",
}
_IMAGE_EXTENSIONS = {
    "PNG": "png",
    "JPEG": "jpg",
    "BMP": "bmp",
    "WebP": "webp",
    "TIFF": "tiff",
}


class ImageExtractPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.mode_combo = QComboBox(self)
        self.mode_combo.addItems([
            _("Extract All Frames"), _("Extract Range"), _("Extract N Images Per Second"), _("Extract Single Frame")
        ])
        form.addRow(_("Extraction Mode"), self.mode_combo)

        self.format_combo = QComboBox(self)
        self.format_combo.addItems(list(_IMAGE_FORMATS.keys()))
        form.addRow(_("Image Format"), self.format_combo)

        self.quality_spin = QSpinBox(self)
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(90)
        form.addRow(_("Quality (JPEG/WebP)"), self.quality_spin)

        self.rate_spin = QSpinBox(self)
        self.rate_spin.setRange(1, 60)
        self.rate_spin.setValue(1)
        form.addRow(_("Images Per Second"), self.rate_spin)

        self.start_time_edit = QLineEdit("00:00:00", self)
        form.addRow(_("Start Time (HH:MM:SS)"), self.start_time_edit)

        self.duration_edit = QLineEdit("5", self)
        form.addRow(_("Duration (s) / Timestamp"), self.duration_edit)

        layout.addStretch()

    def selected_options(self) -> dict:
        format_label = self.format_combo.currentText()
        return {
            "mode": self.mode_combo.currentIndex(),
            "codec": _IMAGE_FORMATS[format_label],
            "extension": _IMAGE_EXTENSIONS[format_label],
            "quality": self.quality_spin.value(),
            "rate": self.rate_spin.value(),
            "start_time": self.start_time_edit.text().strip(),
            "duration": self.duration_edit.text().strip(),
        }

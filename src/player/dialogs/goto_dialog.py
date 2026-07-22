from typing import Optional

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDialogButtonBox
from PySide6.QtCore import Qt


class GoToDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Go to Timestamp"))
        self.setModal(True)
        self.resize(300, 100)

        layout = QVBoxLayout(self)

        field_layout = QHBoxLayout()
        field_layout.addWidget(QLabel(_("Time (hh:mm:ss or mm:ss):"), self))
        self.time_edit = QLineEdit(self)
        self.time_edit.setPlaceholderText("00:00")
        self.time_edit.setAccessibleName(_("Timestamp to jump to"))
        field_layout.addWidget(self.time_edit)
        layout.addLayout(field_layout)

        self.error_label = QLabel(self)
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._seconds: Optional[float] = None

    def _on_accept(self):
        seconds = self._parse_time(self.time_edit.text())
        if seconds is None:
            self.error_label.setText(_("Enter a valid time, e.g. 1:23 or 01:02:03."))
            self.error_label.setVisible(True)
            return
        self._seconds = seconds
        self.accept()

    def get_seconds(self) -> Optional[float]:
        return self._seconds

    @staticmethod
    def _parse_time(text: str) -> Optional[float]:
        text = text.strip()
        if not text:
            return None
        parts = text.split(":")
        if len(parts) > 3:
            return None
        try:
            parts = [float(p) for p in parts]
        except ValueError:
            return None
        if any(p < 0 for p in parts):
            return None

        seconds = 0.0
        for part in parts:
            seconds = seconds * 60 + part
        return seconds

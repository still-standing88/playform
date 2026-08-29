from PySide6.QtWidgets import QPushButton, QColorDialog
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal


class ColorButton(QPushButton):
    """Colour picker that round-trips mpv's "#AARRGGBB" strings.

    Qt's own #AARRGGBB parsing/formatting matches mpv's, but QColor.name()
    drops alpha by default, so the format is requested explicitly.
    """

    colorChanged = Signal(str)

    def __init__(self, label: str, color: str = "#FFFFFFFF", parent=None):
        super().__init__(parent)
        self._label = label
        self._color = QColor("#FFFFFFFF")
        self.setAccessibleName(label)
        self.set_color(color)
        self.clicked.connect(self._pick_color)

    def color(self) -> str:
        return self._color.name(QColor.NameFormat.HexArgb).upper()

    def set_color(self, color: str):
        parsed = QColor(color)
        if not parsed.isValid():
            return
        self._color = parsed
        text = self.color()
        self.setText(text)
        # Screen readers read the accessible description, not the swatch.
        self.setAccessibleDescription(
            _("{label}: {value}, alpha {alpha} of 255").format(
                label=self._label, value=text, alpha=parsed.alpha()
            )
        )
        self.setStyleSheet(
            f"background-color: rgba({parsed.red()}, {parsed.green()}, "
            f"{parsed.blue()}, {parsed.alpha()});"
        )

    def _pick_color(self):
        chosen = QColorDialog.getColor(
            self._color, self, self._label,
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if not chosen.isValid():
            return
        self.set_color(chosen.name(QColor.NameFormat.HexArgb))
        self.colorChanged.emit(self.color())

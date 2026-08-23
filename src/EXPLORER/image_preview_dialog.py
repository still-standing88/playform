from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout
from PySide6.QtGui import QPixmap, QKeySequence, QShortcut
from PySide6.QtCore import Qt


class ImagePreviewDialog(QDialog):
    """Top-level overlay-style preview showing an image file fully
    displayed. Closes on Enter, Escape, or click."""

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Image Preview"))
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)

        screen = self.screen() or (parent.screen() if parent else None)
        if screen is None:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
        available = screen.availableGeometry()

        pixmap = QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                available.width() - 40,
                available.height() - 40,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        else:
            scaled = QPixmap()

        label = QLabel(self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not scaled.isNull():
            label.setPixmap(scaled)
        else:
            label.setText(_("Could not load image"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)

        close_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        close_shortcut.activated.connect(self.close)
        escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        escape_shortcut.activated.connect(self.close)

        width = max(scaled.width(), 200) + 20 if not scaled.isNull() else 300
        height = max(scaled.height(), 150) + 20 if not scaled.isNull() else 200
        x = available.x() + (available.width() - width) // 2
        y = available.y() + (available.height() - height) // 2
        self.setGeometry(x, y, width, height)

    def mousePressEvent(self, event):
        self.close()
        super().mousePressEvent(event)

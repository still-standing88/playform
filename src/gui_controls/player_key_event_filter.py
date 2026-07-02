from PySide6.QtWidgets import QSpinBox, QSlider, QListWidget, QPushButton, QToolButton
from PySide6.QtCore import QObject, QEvent, Qt


class KeyEventFilter(QObject):


    def __init__(self, parent=None):
        super().__init__(parent)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.ShortcutOverride:
            key = event.key()

            if isinstance(watched, (QSpinBox, QSlider, QListWidget)):
                if key in [Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right]:
                    event.accept()
                    return True

            if isinstance(watched, (QPushButton, QToolButton)):
                if key in (Qt.Key.Key_Space, Qt.Key.Key_Enter, Qt.Key.Key_Return):
                    event.accept()
                    return True

            return False

        return False
    
    def install_on_widgets(self, widgets):
        for widget in widgets:
            widget.installEventFilter(self)
    
    def remove_from_widgets(self, widgets):
        for widget in widgets:
            widget.removeEventFilter(self)
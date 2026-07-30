# this will become the default key filter in the future.
from PySide6.QtWidgets import QSpinBox, QDoubleSpinBox, QSlider, QListWidget, QTreeWidget, QPushButton, QToolButton, QComboBox, QCheckBox
from PySide6.QtCore import QObject, QEvent, Qt


class KeyEventFilter(QObject):


    def __init__(self, parent=None):
        super().__init__(parent)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.ShortcutOverride:
            key = event.key()

            if isinstance(watched, (QSpinBox, QDoubleSpinBox, QSlider, QComboBox)):
                if key in [Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right]:
                    event.accept()
                    return True

            # A horizontally-flowing QListWidget (e.g. ListTabCtrl's checkbox
            # tab strip) navigates with Left/Right, not Up/Down -- the
            # opposite of a normal top-to-bottom list.
            if isinstance(watched, QListWidget) and watched.flow() == QListWidget.LeftToRight:
                if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                    event.accept()
                    return True

            if isinstance(watched, (QListWidget, QTreeWidget)):
                if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                    event.accept()
                    return True

            # QTreeWidget natively uses Left/Right to collapse/expand nodes;
            # a flat, top-to-bottom QListWidget does nothing with them, so
            # they're left free to reach widget-level shortcuts (e.g.
            # Explorer's Forward/Backward). Horizontally-flowing QListWidgets
            # are handled above instead, since for them Left/Right *are* the
            # navigation keys.
            if isinstance(watched, QTreeWidget):
                if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                    event.accept()
                    return True

            if isinstance(watched, (QListWidget, QTreeWidget)):
                if key in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
                    event.accept()
                    return True

            if isinstance(watched, (QPushButton, QToolButton, QCheckBox)):
                if key in (Qt.Key.Key_Space, Qt.Key.Key_Enter, Qt.Key.Key_Return):
                    event.accept()
                    return True

            # Space toggles a checkbox item (e.g. ListTabCtrl's tab strip) --
            # only steal it when there's actually a checkbox to toggle.
            # Plain, non-checkable QListWidgets that also need Space to
            # reach a widget-level QShortcut instead (e.g. Explorer's
            # Play/Pause) should not have this filter installed on them at
            # all - see explorer_widget.py's _install_key_event_filter().
            if isinstance(watched, QListWidget) and key == Qt.Key.Key_Space:
                current = watched.currentItem()
                if current is not None and bool(current.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                    event.accept()
                    return True

            return False

        return False

    def install_on_widgets(self, widgets):
        for widget in widgets:
            if widget is None:
                continue
            if not widget.isEnabled():
                continue
            widget.installEventFilter(self)

    def remove_from_widgets(self, widgets):
        for widget in widgets:
            widget.removeEventFilter(self)
from PySide6.QtWidgets import QDockWidget


class FloatableDockWidget(QDockWidget):
    """Shared base for docks that can be floated into their own window.

    Closing that floated window (its close button, Alt+F4, etc.) must
    never destroy the dock - visibility is only meant to be controlled
    through the View menu / Panels toolbar toggle. Closing instead re-docks
    and hides it.
    """

    def closeEvent(self, event):
        if self.isFloating():
            self.setFloating(False)
        self.hide()
        event.accept()

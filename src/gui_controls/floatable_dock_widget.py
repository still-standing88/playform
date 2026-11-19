from PySide6.QtWidgets import QDockWidget, QFrame, QLayout, QScrollArea


class FloatableDockWidget(QDockWidget):
    """Shared base for docks that can be floated into their own window.

    Closing that floated window (its close button, Alt+F4, etc.) must
    never destroy the dock - visibility is only meant to be controlled
    through the View menu / Panels toolbar toggle. Closing instead re-docks
    and hides it.
    """

    def set_scrollable_widget(self, widget):
        """Keep dock minima bounded while preserving access to all content.

        Qt combines the minimum sizes of tabified docks, including inactive
        tabs. A dense browser must scroll rather than force adjacent docks
        outside the main window. This also covers narrow floating windows.
        """
        scroll = self.widget()
        if not isinstance(scroll, QScrollArea):
            scroll = QScrollArea(self)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidgetResizable(True)
            self.setWidget(scroll)
        if widget.layout() is not None:
            widget.layout().setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        scroll.setWidget(widget)

    def closeEvent(self, event):
        if self.isFloating():
            self.setFloating(False)
        self.hide()
        event.accept()

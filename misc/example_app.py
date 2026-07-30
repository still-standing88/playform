"""
Minimal runnable PySide6 example app using QToolBox.

This is the real widget the test_toolbox.py tests are written against
(previously the test file built its own throwaway toolbox inline).

Run it directly to see the app:
    QT_QPA_PLATFORM=offscreen python3 example_app.py   # headless check
    python3 example_app.py                              # normal run
"""
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QToolBox, QWidget, QLabel,
    QVBoxLayout, QLineEdit, QCheckBox, QComboBox, QPushButton,
    QAbstractButton
)


class SettingsToolBox(QToolBox):
    """
    A QToolBox with three settings pages: General, Advanced, Debug.

    Keeps Python references to each page widget on self, avoiding the
    shiboken GC gotcha where QToolBox.addItem() doesn't reliably transfer
    C++ ownership (confirmed while testing: pages can silently disappear
    on removeItem() if nothing in Python still references them).

    ACCESSIBILITY FIX: Qt's internal QToolBox page-header buttons are
    created with focusPolicy == Qt.NoFocus, so by default Tab can never
    reach them - a keyboard-only user can click a page open with a mouse
    but has no way to switch pages, or even discover other pages exist,
    using only the keyboard. This is a long-standing Qt limitation, not
    a bug in this code (see QTBUG-175, open since the Qt 4 era). We patch
    it below by finding those header buttons and giving them TabFocus.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pages = []
        self._build_general_page()
        self._build_advanced_page()
        self._build_debug_page()
        self._fix_header_keyboard_focus()

    def _fix_header_keyboard_focus(self):
        """Make the page-header buttons reachable and operable via keyboard."""
        header_texts = {self.itemText(i) for i in range(self.count())}
        headers = [
            b for b in self.findChildren(QAbstractButton)
            if b.text() in header_texts
        ]
        for button in headers:
            button.setFocusPolicy(Qt.TabFocus)
            # QToolBox headers already respond to Space/Enter once focusable;
            # nothing further needed for activation.

    def _build_general_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Display name:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        self.autosave_checkbox = QCheckBox("Enable autosave")
        self.autosave_checkbox.setChecked(True)
        layout.addWidget(self.autosave_checkbox)
        layout.addStretch()
        self.addItem(page, "General")
        self._pages.append(page)

    def _build_advanced_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Rendering backend:"))
        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["OpenGL", "Software", "Vulkan"])
        layout.addWidget(self.backend_combo)
        layout.addStretch()
        self.addItem(page, "Advanced")
        self._pages.append(page)

    def _build_debug_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Diagnostics:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["Info", "Warning", "Debug", "Trace"])
        layout.addWidget(self.log_level_combo)
        self.clear_logs_button = QPushButton("Clear log files")
        layout.addWidget(self.clear_logs_button)
        layout.addStretch()
        self.addItem(page, "Debug")
        self._pages.append(page)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QToolBox Example")
        self.toolbox = SettingsToolBox()
        self.setCentralWidget(self.toolbox)
        self.resize(360, 420)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

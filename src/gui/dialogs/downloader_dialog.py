"""
Downloader dialog – wraps DownloaderWidget in a non-modal top-level dialog.

Singleton management is handled by the host (MainWindow).  When the user
clicks "Minimize", the dialog is hidden and the main-window shows a
status-bar button to bring it back – exactly like ToolDialog.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QKeyEvent

from app_constance.styles import TITLE_LABEL_STYLE
from downloader.downloader_widget import DownloaderWidget
from downloader.downloader import Downloader


class DownloaderDialog(QDialog):
    """Non-modal dialog that hosts the DownloaderWidget.

    Signals
    -------
    dialog_hidden : emitted when the user clicks Minimize.
    dialog_closed : emitted when the dialog is actually closed / destroyed.
    """

    dialog_hidden = Signal()
    dialog_closed = Signal()

    def __init__(self, downloader: Downloader, parent=None):
        super().__init__(parent)
        self._downloader = downloader

        self.setWindowTitle("Download Manager")
        # Non-modal so the user can keep using the app
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(700, 450)
        self.resize(860, 560)

        # Remove the native close button – we provide our own
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        self._build_ui()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        # ── Title bar ──────────────────────────────────────────────
        title_bar = QHBoxLayout()
        title_label = QLabel("Download Manager")
        title_label.setStyleSheet(TITLE_LABEL_STYLE)
        title_bar.addWidget(title_label)
        title_bar.addStretch()

        minimize_btn = QPushButton("Minimize")
        minimize_btn.setFixedSize(75, 25)
        minimize_btn.setToolTip("Hide to status bar")
        minimize_btn.clicked.connect(self._on_minimize)
        title_bar.addWidget(minimize_btn)

        close_btn = QPushButton("Close")
        close_btn.setFixedSize(60, 25)
        close_btn.setToolTip("Close the download manager")
        close_btn.clicked.connect(self._on_close_requested)
        title_bar.addWidget(close_btn)

        layout.addLayout(title_bar)

        # ── Downloader widget ──────────────────────────────────────
        self._widget = DownloaderWidget(downloader=self._downloader)
        # The widget has its own Minimize / Close buttons; rewire them
        # so they delegate to the dialog, then hide the redundant title bar
        # buttons from the widget itself (keep the dialog's title bar only).
        if hasattr(self._widget, "minimize_btn"):
            self._widget.minimize_btn.clicked.disconnect()
            self._widget.minimize_btn.clicked.connect(self._on_minimize)
        if hasattr(self._widget, "close_btn"):
            self._widget.close_btn.clicked.disconnect()
            self._widget.close_btn.clicked.connect(self._on_close_requested)
        layout.addWidget(self._widget)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    @property
    def downloader(self) -> Downloader:
        return self._downloader

    @property
    def widget(self) -> DownloaderWidget:
        return self._widget

    def add_download(self, url: str, destination=None, filename=None):
        """Convenience passthrough to DownloaderWidget.add_download."""
        return self._widget.add_download(url, destination, filename)

    @Slot()
    def show_dialog(self):
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.show()
        self.raise_()
        self.activateWindow()

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------
    @Slot()
    def _on_minimize(self):
        self.hide()
        self.dialog_hidden.emit()

    @Slot()
    def _on_close_requested(self):
        """Same confirmation logic as DownloaderWidget.close_with_confirmation."""
        active = self._downloader.get_all_downloads()["active"]
        if active:
            box = QMessageBox(self)
            box.setWindowTitle("Downloads in Progress")
            box.setText(f"{len(active)} download(s) are still in progress.")
            box.setInformativeText("Close anyway and abort all downloads?")
            abort_btn = box.addButton("Abort & Close", QMessageBox.ButtonRole.DestructiveRole)
            cancel_btn = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(cancel_btn)
            box.exec()
            if box.clickedButton() != abort_btn:
                return
            for item in list(active):
                self._downloader.cancel_download(item)

        self.accept()

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent):
        # Don't let Escape close the dialog accidentally
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        """Intercept the native close event and use our own logic."""
        self.dialog_closed.emit()
        event.accept()

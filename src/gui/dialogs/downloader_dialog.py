from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QKeyEvent

from app_constance.styles import TITLE_LABEL_STYLE
from downloader.downloader_widget import DownloaderWidget
from downloader.downloader import Downloader


class DownloaderDialog(QDialog):
    dialog_hidden = Signal()
    dialog_closed = Signal()

    def __init__(self, downloader: Downloader, parent=None):
        super().__init__(parent)
        self._downloader = downloader

        self.setWindowTitle(_("Download Manager"))
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(700, 450)
        self.resize(860, 560)


        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        self.ui()

    def ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)


        title_bar = QHBoxLayout()
        title_label = QLabel(_("Download Manager"))
        title_label.setStyleSheet(TITLE_LABEL_STYLE)
        title_bar.addWidget(title_label)
        title_bar.addStretch()

        minimize_btn = QPushButton(_("Minimize"))
        minimize_btn.setFixedSize(75, 25)
        minimize_btn.setToolTip(_("Hide to status bar"))
        minimize_btn.clicked.connect(self._on_minimize)
        title_bar.addWidget(minimize_btn)

        close_btn = QPushButton(_("Close"))
        close_btn.setFixedSize(60, 25)
        close_btn.clicked.connect(self._on_close_requested)
        title_bar.addWidget(close_btn)

        layout.addLayout(title_bar)


        self._widget = DownloaderWidget(downloader=self._downloader)
        layout.addWidget(self._widget)

    @property
    def downloader(self) -> Downloader:
        return self._downloader

    @property
    def widget(self) -> DownloaderWidget:
        return self._widget

    def add_download(self, url: str, destination=None, filename=None):
        return self._widget.add_download(url, destination, filename)

    @Slot()
    def show_dialog(self):
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.show()
        self.raise_()
        self.activateWindow()

    @Slot()
    def _on_minimize(self):
        self.hide()
        self.dialog_hidden.emit()

    @Slot()
    def _on_close_requested(self):
        # DownloaderWidget owns the confirmation logic now -- this dialog
        # only owns the chrome (title bar, minimize/close buttons), not a
        # second copy of the same prompt.
        if not self._widget.close_with_confirmation():
            return
        self.accept()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.dialog_closed.emit()
        event.accept()

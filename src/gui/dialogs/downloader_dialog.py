from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
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

        if hasattr(self._widget, "minimize_btn"):
            self._widget.minimize_btn.clicked.disconnect()
            self._widget.minimize_btn.clicked.connect(self._on_minimize)
        if hasattr(self._widget, "close_btn"):
            self._widget.close_btn.clicked.disconnect()
            self._widget.close_btn.clicked.connect(self._on_close_requested)
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
        active = self._downloader.get_all_downloads()["active"]
        if active:
            box = QMessageBox(self)
            box.setWindowTitle(_("Downloads in Progress"))
            box.setText(
                _("{count} download(s) are still in progress.").format(count=len(active))
            )
            box.setInformativeText(_("Close anyway and abort all downloads?"))
            abort_btn = box.addButton(_("Abort & Close"), QMessageBox.ButtonRole.DestructiveRole)
            cancel_btn = box.addButton(_("Cancel"), QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(cancel_btn)
            box.exec()
            if box.clickedButton() != abort_btn:
                return
            for item in list(active):
                self._downloader.cancel_download(item)

        self.accept()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.dialog_closed.emit()
        event.accept()

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QKeyEvent

from app_constance.styles import TITLE_LABEL_STYLE
from app_db.catalog_worker import CatalogWorker


class CatalogProgressDialog(QDialog):
    dialog_hidden = Signal()
    dialog_closed = Signal()

    def __init__(self, worker: CatalogWorker, parent=None):
        super().__init__(parent)
        self._worker = worker

        self.setWindowTitle(_("Database Cataloging"))
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(420, 220)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        self.ui()
        self._connect_worker()

    def ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title_bar = QHBoxLayout()
        title_label = QLabel(_("Database Cataloging"))
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

        self.folder_label = QLabel(_("No folder being scanned"))
        self.folder_label.setWordWrap(True)
        layout.addWidget(self.folder_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)

        self.stats_label = QLabel("")
        layout.addWidget(self.stats_label)

        layout.addStretch()

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.cancel_button = QPushButton(_("Cancel Current Folder"))
        self.cancel_button.clicked.connect(self._worker.cancel_current)
        button_row.addWidget(self.cancel_button)
        layout.addLayout(button_row)

    def _connect_worker(self):
        self._worker.folder_started.connect(self._on_folder_started)
        self._worker.progress.connect(self._on_progress)
        self._worker.folder_finished.connect(self._on_folder_finished)
        self._worker.error.connect(self._on_error)

    @Slot(str)
    def _on_folder_started(self, path):
        self.folder_label.setText(_("Scanning: {path}").format(path=path))
        self.stats_label.setText("")

    @Slot(str, int, int, int)
    def _on_progress(self, path, seen, added, skipped):
        self.stats_label.setText(_("{added} added, {skipped} skipped").format(added=added, skipped=skipped))

    @Slot(str, int, int)
    def _on_folder_finished(self, path, added, skipped):
        self.folder_label.setText(_("Finished: {path}").format(path=path))
        self.stats_label.setText(_("{added} added, {skipped} skipped").format(added=added, skipped=skipped))

    @Slot(str, str)
    def _on_error(self, path, message):
        self.folder_label.setText(_("Error scanning {path}").format(path=path))
        self.stats_label.setText(message)

    def is_busy(self) -> bool:
        return self._worker.isRunning()

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
        if self.is_busy():
            box = QMessageBox(self)
            box.setWindowTitle(_("Cataloging in Progress"))
            box.setText(_("A folder is still being cataloged."))
            box.setInformativeText(_("Close anyway? Cataloging will continue in the background."))
            close_btn = box.addButton(_("Close"), QMessageBox.ButtonRole.AcceptRole)
            cancel_btn = box.addButton(_("Cancel"), QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(cancel_btn)
            box.exec()
            if box.clickedButton() != close_btn:
                return
        # accept() hides without firing closeEvent, which would leave
        # dialog_closed never emitted and the singleton dialog stuck
        # "closed but not reset" - close() triggers closeEvent properly.
        self.close()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.dialog_closed.emit()
        event.accept()

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
        self._sync_initial_state()

    def ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title_bar = QHBoxLayout()
        title_label = QLabel(_("Database Cataloging"))
        title_label.setStyleSheet(TITLE_LABEL_STYLE)
        title_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
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
        self.folder_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        layout.addWidget(self.folder_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)

        self.stats_label = QLabel("")
        self.stats_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        layout.addWidget(self.stats_label)

        layout.addStretch()

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.pause_button = QPushButton(_("Pause"))
        self.pause_button.clicked.connect(self._on_pause_clicked)
        button_row.addWidget(self.pause_button)
        layout.addLayout(button_row)

    def _connect_worker(self):
        self._worker.folder_started.connect(self._on_folder_started)
        self._worker.progress.connect(self._on_progress)
        self._worker.folder_finished.connect(self._on_folder_finished)
        self._worker.error.connect(self._on_error)
        self._worker.paused_changed.connect(self._on_paused_changed)

    def _sync_initial_state(self):
        """Cross-thread signals are queued - if the worker was already
        started (and had already emitted folder_started/progress) before
        this dialog existed to connect to it, those specific emissions are
        lost. Read the worker's own current-state snapshot directly instead
        of assuming a signal will arrive to set it."""
        worker = self._worker
        if worker.current_folder is None:
            return
        if worker.current_error is not None:
            self._on_error(worker.current_folder, worker.current_error)
        elif worker.current_finished:
            self._on_folder_finished(worker.current_folder, worker.current_added, worker.current_skipped)
        else:
            self._on_folder_started(worker.current_folder)
            self._on_progress(worker.current_folder, worker.current_seen, worker.current_added, worker.current_skipped)
        self._on_paused_changed(worker.is_paused())

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

    @Slot(bool)
    def _on_paused_changed(self, paused):
        self.pause_button.setText(_("Resume") if paused else _("Pause"))

    @Slot()
    def _on_pause_clicked(self):
        if self._worker.is_paused():
            self._worker.resume()
        else:
            self._worker.pause()

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
            box.setInformativeText(_("Would you like to terminate the current scan and close?"))
            terminate_btn = box.addButton(_("Terminate"), QMessageBox.ButtonRole.AcceptRole)
            keep_going_btn = box.addButton(_("Keep Scanning"), QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(keep_going_btn)
            box.exec()
            if box.clickedButton() != terminate_btn:
                return
            self._worker.cancel_all()
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

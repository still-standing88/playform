from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel,
    QPlainTextEdit, QProgressBar, QPushButton, QComboBox
)
from PySide6.QtCore import Qt, Signal

NOTIFY_SILENT = "silent"
NOTIFY_SYSTEM = "system"


class JobProgressDialog(QDialog):
    """Generic run-progress dialog: Progress/Live-Log tabs, pause/cancel, notify-on-finish.

    Shared by any long-running background job driven through the
    `on_overall_progress`/`on_file_progress`/`on_file_completed`/`on_log_line` callback
    shape used by `media_core.ffmpeg.conversion_job.ConversionRunner` and
    `media_core.m4b_tools`' runners. Pass `total_files=0` for an indeterminate progress
    bar (single-outcome jobs like Bind/Slide that don't have a meaningful file count) and
    `supports_pause=False` to hide the Pause button for jobs that can't be paused mid-run.
    """

    cancel_requested = Signal()
    pause_toggled = Signal(bool)

    def __init__(self, total_files: int = 0, parent=None, title: str = None, supports_pause: bool = True):
        super().__init__(parent)
        self.setWindowTitle(title or _("Job Progress"))
        self.setMinimumSize(560, 420)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self._paused = False
        self._total_files = total_files
        self._build_ui(supports_pause)

    def _build_ui(self, supports_pause: bool):
        layout = QVBoxLayout(self)

        self.current_file_label = QLabel(_("Preparing..."), self)
        layout.addWidget(self.current_file_label)

        self.progress_bar = QProgressBar(self)
        if self._total_files > 0:
            self.progress_bar.setRange(0, self._total_files)
        else:
            self.progress_bar.setRange(0, 0)
        self.progress_bar.setAccessibleName(_("Overall progress"))
        layout.addWidget(self.progress_bar)

        self.tabs = QTabWidget(self)

        progress_tab = QWidget(self)
        progress_layout = QVBoxLayout(progress_tab)
        self.file_log = QPlainTextEdit(progress_tab)
        self.file_log.setReadOnly(True)
        self.file_log.setAccessibleName(_("Per-file results"))
        self.file_log.setAccessibleDescription(_("A running log of each completed, skipped, or failed file."))
        progress_layout.addWidget(self.file_log)
        self.tabs.addTab(progress_tab, _("Progress"))

        live_log_tab = QWidget(self)
        live_log_layout = QVBoxLayout(live_log_tab)
        self.live_log = QPlainTextEdit(live_log_tab)
        self.live_log.setReadOnly(True)
        self.live_log.setMaximumBlockCount(5000)
        self.live_log.setAccessibleName(_("Live log output"))
        self.live_log.setAccessibleDescription(_("Raw ffmpeg output streamed live as the job runs."))
        live_log_layout.addWidget(self.live_log)
        self.tabs.addTab(live_log_tab, _("Live Log"))

        layout.addWidget(self.tabs, stretch=1)

        button_row = QHBoxLayout()
        notify_label = QLabel(_("When finished:"), self)
        button_row.addWidget(notify_label)
        self.notify_combo = QComboBox(self)
        self.notify_combo.addItem(_("Show System Notification"), NOTIFY_SYSTEM)
        self.notify_combo.addItem(_("Stay Silent"), NOTIFY_SILENT)
        notify_label.setBuddy(self.notify_combo)
        button_row.addWidget(self.notify_combo)
        button_row.addStretch()

        self.pause_button = QPushButton(_("Pause"), self)
        self.pause_button.clicked.connect(self._on_pause_clicked)
        self.pause_button.setVisible(supports_pause)
        button_row.addWidget(self.pause_button)

        self.cancel_button = QPushButton(_("Cancel"), self)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        button_row.addWidget(self.cancel_button)

        layout.addLayout(button_row)

    def _on_pause_clicked(self):
        self._paused = not self._paused
        self.pause_button.setText(_("Resume") if self._paused else _("Pause"))
        self.pause_toggled.emit(self._paused)
        if self._paused:
            self.current_file_label.setText(_("Paused — {label}").format(label=self.current_file_label.text()))

    def _on_cancel_clicked(self):
        self.cancel_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.current_file_label.setText(_("Cancelling..."))
        self.cancel_requested.emit()

    def notify_preference(self) -> str:
        return self.notify_combo.currentData()

    def set_overall_progress(self, current: int, total: int, filename: str):
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(current)
        if filename:
            self.current_file_label.setText(
                _("Processing file {current} of {total}: {filename}").format(
                    current=current + 1, total=total, filename=filename
                )
            )

    def set_file_progress_detail(self, text: str):
        base = self.current_file_label.text().split(" — ")[0]
        self.current_file_label.setText(f"{base} — {text}")

    def append_file_result(self, message: str):
        self.file_log.appendPlainText(message)

    def append_live_log(self, line: str):
        self.live_log.appendPlainText(line)

    def mark_finished(self, completed: bool = True):
        self.pause_button.setEnabled(False)
        self.cancel_button.setText(_("Close"))
        self.cancel_button.setEnabled(True)
        try:
            self.cancel_button.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        self.cancel_button.clicked.connect(self.accept)
        self.current_file_label.setText(_("Done.") if completed else _("Cancelled."))

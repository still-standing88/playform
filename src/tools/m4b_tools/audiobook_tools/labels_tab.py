import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QLabel
)

from gui_controls.job_progress_dialog import JobProgressDialog
from tools.ffmpeg_handler import FFmpegHandler
from media_core.m4b_tools.labels import read_label_file, write_label_file, apply_segments_to_book
from media_core.m4b_tools.finders import find_chapters
from tools.m4b_tools.audiobook_tools.job import SimpleM4BTask
from utilities import signal_manager


def _export_chapters(book_path, labels_path, ffprobe_executable="ffprobe", on_log_line=None):
    on_log_line = on_log_line or (lambda line: None)
    segments = find_chapters(book_path, ffprobe_executable=ffprobe_executable)
    if not segments:
        on_log_line("Error: No chapters found in the source file.")
        return False
    write_label_file(labels_path, segments)
    on_log_line(f"Wrote {len(segments)} labels to {labels_path}")
    return True


def _import_labels(book_path, labels_path, ffmpeg_executable="ffmpeg", ffprobe_executable="ffprobe", on_log_line=None):
    segments = read_label_file(labels_path)
    if not segments:
        (on_log_line or (lambda line: None))("Error: No labels found in the label file.")
        return False
    return apply_segments_to_book(
        segments, book_path, ffmpeg_executable=ffmpeg_executable,
        ffprobe_executable=ffprobe_executable, on_log_line=on_log_line,
    )


class LabelsTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.job: SimpleM4BTask | None = None
        self.progress_dialog: JobProgressDialog | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        note = QLabel(
            _("Exchange chapter markers with an Audacity label-track text file — export an "
              "audiobook's existing chapters to labels for editing, or import an edited label "
              "file back as the book's new chapters."),
            self
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        source_group = QGroupBox(_("Audiobook File"), self)
        source_row = QHBoxLayout(source_group)
        self.book_path_edit = QLineEdit(self)
        self.book_browse_button = QPushButton(_("Browse..."), self)
        source_row.addWidget(self.book_path_edit)
        source_row.addWidget(self.book_browse_button)
        layout.addWidget(source_group)

        labels_group = QGroupBox(_("Label File (Audacity format)"), self)
        labels_row = QHBoxLayout(labels_group)
        self.labels_path_edit = QLineEdit(self)
        self.labels_browse_button = QPushButton(_("Browse..."), self)
        labels_row.addWidget(self.labels_path_edit)
        labels_row.addWidget(self.labels_browse_button)
        layout.addWidget(labels_group)

        button_row = QHBoxLayout()
        self.export_button = QPushButton(_("Export Chapters → Labels"), self)
        self.import_button = QPushButton(_("Import Labels → Chapters"), self)
        button_row.addWidget(self.export_button)
        button_row.addWidget(self.import_button)
        layout.addLayout(button_row)
        layout.addStretch()

        self.book_browse_button.clicked.connect(self._browse_book)
        self.labels_browse_button.clicked.connect(self._browse_labels_existing)
        self.export_button.clicked.connect(self._on_export)
        self.import_button.clicked.connect(self._on_import)

    def _browse_book(self):
        path, _filter = QFileDialog.getOpenFileName(self, _("Select Audiobook File"))
        if path:
            self.book_path_edit.setText(path)

    def _browse_labels_existing(self):
        path, _filter = QFileDialog.getOpenFileName(self, _("Select Label File"), "", "Text Files (*.txt)")
        if path:
            self.labels_path_edit.setText(path)

    def _validate_book(self) -> str:
        book_path = self.book_path_edit.text().strip()
        if not book_path or not os.path.exists(book_path):
            QMessageBox.warning(self, _("Invalid Source"), _("Choose a valid audiobook file."))
            return ""
        return book_path

    def _on_export(self):
        book_path = self._validate_book()
        if not book_path:
            return

        labels_path, _filter = QFileDialog.getSaveFileName(self, _("Save Label File"), "", "Text Files (*.txt)")
        if not labels_path:
            return

        _unused_ffmpeg_path, ffprobe_path = FFmpegHandler.get_ffmpeg_binary()
        self._run_task(
            _export_chapters, book_path, labels_path,
            ffprobe_executable=str(ffprobe_path) if ffprobe_path else "ffprobe",
        )

    def _on_import(self):
        book_path = self._validate_book()
        if not book_path:
            return

        labels_path = self.labels_path_edit.text().strip()
        if not labels_path or not os.path.exists(labels_path):
            QMessageBox.warning(self, _("Invalid Label File"), _("Choose a valid label file."))
            return

        confirm = QMessageBox.question(
            self, _("Confirm"),
            _("This rewrites '{path}' in place. Continue?").format(path=os.path.basename(book_path)),
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        ffmpeg_path, ffprobe_path = FFmpegHandler.get_ffmpeg_binary()
        self._run_task(
            _import_labels, book_path, labels_path,
            ffmpeg_executable=str(ffmpeg_path),
            ffprobe_executable=str(ffprobe_path) if ffprobe_path else "ffprobe",
        )

    def _run_task(self, func, *args, **kwargs):
        self.job = SimpleM4BTask(func, *args, **kwargs)
        self.job.log_line.connect(self._on_log_line)
        self.job.finished_job.connect(self._on_finished)

        self.progress_dialog = JobProgressDialog(0, self, title=_("Working..."), supports_pause=False)
        self.progress_dialog.cancel_requested.connect(self.progress_dialog.accept)

        self.export_button.setEnabled(False)
        self.import_button.setEnabled(False)
        self.job.start()
        self.progress_dialog.show()

    def _on_log_line(self, line: str):
        if self.progress_dialog:
            self.progress_dialog.append_live_log(line)

    def _on_finished(self, success: bool, error: str):
        self.export_button.setEnabled(True)
        self.import_button.setEnabled(True)
        if self.progress_dialog:
            self.progress_dialog.append_file_result(
                _("OK.") if success else _("FAILED: {error}").format(error=error)
            )
            self.progress_dialog.mark_finished(success)
        signal_manager.statusbar_message.emit(_("Done") if success else _("Labels operation failed"))

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit, QPushButton,
    QFileDialog, QMessageBox, QLabel
)

from gui_controls.job_progress_dialog import JobProgressDialog
from tools.ffmpeg_handler import FFmpegHandler
from media_core.m4b_tools.cover import extract_cover, add_cover
from tools.m4b_tools.audiobook_tools.job import SimpleM4BTask
from utilities import signal_manager


class CoverTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.job: SimpleM4BTask | None = None
        self.progress_dialog: JobProgressDialog | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        source_group = QGroupBox(_("Audiobook File"), self)
        source_row = QHBoxLayout(source_group)
        self.book_path_edit = QLineEdit(self)
        self.book_browse_button = QPushButton(_("Browse..."), self)
        source_row.addWidget(self.book_path_edit)
        source_row.addWidget(self.book_browse_button)
        layout.addWidget(source_group)

        extract_group = QGroupBox(_("Extract Cover"), self)
        extract_layout = QVBoxLayout(extract_group)
        extract_row = QHBoxLayout()
        self.extract_output_edit = QLineEdit(self)
        self.extract_browse_button = QPushButton(_("Browse..."), self)
        extract_row.addWidget(self.extract_output_edit)
        extract_row.addWidget(self.extract_browse_button)
        extract_layout.addLayout(extract_row)
        self.extract_button = QPushButton(_("Extract Cover Image"), self)
        extract_layout.addWidget(self.extract_button)
        layout.addWidget(extract_group)

        apply_group = QGroupBox(_("Apply Cover"), self)
        apply_layout = QVBoxLayout(apply_group)
        cover_row = QHBoxLayout()
        self.cover_image_edit = QLineEdit(self)
        self.cover_browse_button = QPushButton(_("Browse..."), self)
        cover_row.addWidget(self.cover_image_edit)
        cover_row.addWidget(self.cover_browse_button)
        apply_layout.addLayout(cover_row)

        apply_output_row = QHBoxLayout()
        self.apply_output_edit = QLineEdit(self)
        self.apply_output_browse_button = QPushButton(_("Browse..."), self)
        apply_output_row.addWidget(self.apply_output_edit)
        apply_output_row.addWidget(self.apply_output_browse_button)
        apply_layout.addLayout(apply_output_row)

        apply_note = QLabel(_("Output must be a different file from the source."), self)
        apply_layout.addWidget(apply_note)
        self.apply_button = QPushButton(_("Apply Cover Image"), self)
        apply_layout.addWidget(self.apply_button)
        layout.addWidget(apply_group)
        layout.addStretch()

        self.book_browse_button.clicked.connect(self._browse_book)
        self.extract_browse_button.clicked.connect(self._browse_extract_output)
        self.cover_browse_button.clicked.connect(self._browse_cover_image)
        self.apply_output_browse_button.clicked.connect(self._browse_apply_output)
        self.extract_button.clicked.connect(self._on_extract)
        self.apply_button.clicked.connect(self._on_apply)

    def _browse_book(self):
        path, _filter = QFileDialog.getOpenFileName(self, _("Select Audiobook File"))
        if path:
            self.book_path_edit.setText(path)

    def _browse_extract_output(self):
        path, _filter = QFileDialog.getSaveFileName(self, _("Save Cover As"), "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.extract_output_edit.setText(path)

    def _browse_cover_image(self):
        path, _filter = QFileDialog.getOpenFileName(self, _("Select Cover Image"), "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.cover_image_edit.setText(path)

    def _browse_apply_output(self):
        path, _filter = QFileDialog.getSaveFileName(self, _("Save Audiobook As"), "", "M4B Audiobook (*.m4b)")
        if path:
            self.apply_output_edit.setText(path)

    def _validate_book(self) -> str:
        book_path = self.book_path_edit.text().strip()
        if not book_path or not os.path.exists(book_path):
            QMessageBox.warning(self, _("Invalid Source"), _("Choose a valid audiobook file."))
            return ""
        return book_path

    def _on_extract(self):
        book_path = self._validate_book()
        if not book_path:
            return
        output_path = self.extract_output_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, _("No Output"), _("Choose where to save the cover image."))
            return

        ffmpeg_path, _unused_ffprobe_path = FFmpegHandler.get_ffmpeg_binary()
        self._run_task(extract_cover, book_path, output_path, ffmpeg_executable=str(ffmpeg_path))

    def _on_apply(self):
        book_path = self._validate_book()
        if not book_path:
            return
        cover_path = self.cover_image_edit.text().strip()
        if not cover_path or not os.path.exists(cover_path):
            QMessageBox.warning(self, _("Invalid Cover"), _("Choose a valid cover image."))
            return
        output_path = self.apply_output_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, _("No Output"), _("Choose an output audiobook path."))
            return
        if os.path.normcase(os.path.normpath(output_path)) == os.path.normcase(os.path.normpath(book_path)):
            QMessageBox.warning(self, _("Invalid Output"), _("Output must be a different file from the source."))
            return

        ffmpeg_path, _unused_ffprobe_path = FFmpegHandler.get_ffmpeg_binary()

        def _apply(*, on_log_line=None):
            add_cover(book_path, cover_path, output_path, ffmpeg_executable=str(ffmpeg_path))
            return True

        self._run_task(_apply)

    def _run_task(self, func, *args, **kwargs):
        self.job = SimpleM4BTask(func, *args, **kwargs)
        self.job.log_line.connect(self._on_log_line)
        self.job.finished_job.connect(self._on_finished)

        self.progress_dialog = JobProgressDialog(0, self, title=_("Working..."), supports_pause=False)
        self.progress_dialog.cancel_requested.connect(self.progress_dialog.accept)

        self.extract_button.setEnabled(False)
        self.apply_button.setEnabled(False)
        self.job.start()
        self.progress_dialog.show()

    def _on_log_line(self, line: str):
        if self.progress_dialog:
            self.progress_dialog.append_live_log(line)

    def _on_finished(self, success: bool, error: str):
        self.extract_button.setEnabled(True)
        self.apply_button.setEnabled(True)
        if self.progress_dialog:
            self.progress_dialog.append_file_result(
                _("OK.") if success else _("FAILED: {error}").format(error=error or _("Unknown error"))
            )
            self.progress_dialog.mark_finished(success)
        signal_manager.statusbar_message.emit(_("Done") if success else _("Cover operation failed"))

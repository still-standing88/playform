import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QRadioButton,
    QButtonGroup, QStackedWidget, QLineEdit, QPushButton, QCheckBox, QComboBox,
    QFileDialog, QMessageBox
)

from gui_controls.ordered_file_list import OrderedFileListWidget
from gui_controls.job_progress_dialog import JobProgressDialog
from tools.ffmpeg_handler import FFmpegHandler
from tools.m4b_tools.audiobook_tools.job import BindJob
from utilities import signal_manager

_BITRATES = ["32k", "48k", "64k", "96k", "128k", "160k", "192k", "256k", "320k"]


class BindTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.job: BindJob | None = None
        self.progress_dialog: JobProgressDialog | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        source_group = QGroupBox(_("Source"), self)
        source_layout = QVBoxLayout(source_group)

        mode_row = QHBoxLayout()
        self.folder_radio = QRadioButton(_("From Folder (one chapter per file, sorted)"), self)
        self.filelist_radio = QRadioButton(_("From File List (manual order)"), self)
        self.folder_radio.setChecked(True)
        self.source_mode_group = QButtonGroup(self)
        self.source_mode_group.addButton(self.folder_radio, 0)
        self.source_mode_group.addButton(self.filelist_radio, 1)
        mode_row.addWidget(self.folder_radio)
        mode_row.addWidget(self.filelist_radio)
        mode_row.addStretch()
        source_layout.addLayout(mode_row)

        self.source_stack = QStackedWidget(self)

        folder_widget = QWidget(self)
        folder_row = QHBoxLayout(folder_widget)
        folder_row.setContentsMargins(0, 0, 0, 0)
        self.folder_path_edit = QLineEdit(self)
        self.folder_path_edit.setAccessibleName(_("Source folder"))
        self.folder_browse_button = QPushButton(_("Browse..."), self)
        folder_row.addWidget(self.folder_path_edit)
        folder_row.addWidget(self.folder_browse_button)
        self.source_stack.addWidget(folder_widget)

        self.file_list = OrderedFileListWidget(self)
        self.source_stack.addWidget(self.file_list)

        source_layout.addWidget(self.source_stack)
        layout.addWidget(source_group)

        options_group = QGroupBox(_("Options"), self)
        options_layout = QVBoxLayout(options_group)
        self.use_filenames_check = QCheckBox(_("Use filenames as chapter titles"), self)
        self.decode_durations_check = QCheckBox(_("Decode durations (slower, more accurate)"), self)
        self.keep_temp_check = QCheckBox(_("Keep temporary files (debugging)"), self)
        options_layout.addWidget(self.use_filenames_check)
        options_layout.addWidget(self.decode_durations_check)
        options_layout.addWidget(self.keep_temp_check)
        layout.addWidget(options_group)

        metadata_group = QGroupBox(_("Audiobook Metadata"), self)
        metadata_form = QFormLayout(metadata_group)
        self.author_edit = QLineEdit(self)
        self.title_edit = QLineEdit(self)
        self.date_edit = QLineEdit(self)
        self.date_edit.setPlaceholderText(_("YYYY-MM-DD"))
        self.bitrate_combo = QComboBox(self)
        self.bitrate_combo.addItems(_BITRATES)
        self.bitrate_combo.setCurrentText("128k")

        cover_row = QHBoxLayout()
        self.cover_path_edit = QLineEdit(self)
        self.cover_path_edit.setAccessibleName(_("Cover image path"))
        self.cover_browse_button = QPushButton(_("Browse..."), self)
        cover_row.addWidget(self.cover_path_edit)
        cover_row.addWidget(self.cover_browse_button)

        metadata_form.addRow(_("Author"), self.author_edit)
        metadata_form.addRow(_("Title"), self.title_edit)
        metadata_form.addRow(_("Date"), self.date_edit)
        metadata_form.addRow(_("Bitrate"), self.bitrate_combo)
        metadata_form.addRow(_("Cover Image"), cover_row)
        layout.addWidget(metadata_group)

        output_group = QGroupBox(_("Output"), self)
        output_row = QHBoxLayout(output_group)
        self.output_path_edit = QLineEdit(self)
        self.output_path_edit.setAccessibleName(_("Output .m4b file path"))
        self.output_browse_button = QPushButton(_("Browse..."), self)
        output_row.addWidget(self.output_path_edit)
        output_row.addWidget(self.output_browse_button)
        layout.addWidget(output_group)

        self.begin_button = QPushButton(_("Bind Audiobook"), self)
        layout.addWidget(self.begin_button)
        layout.addStretch()

        self.folder_radio.toggled.connect(lambda checked: checked and self.source_stack.setCurrentIndex(0))
        self.filelist_radio.toggled.connect(lambda checked: checked and self.source_stack.setCurrentIndex(1))
        self.folder_browse_button.clicked.connect(self._browse_folder)
        self.cover_browse_button.clicked.connect(self._browse_cover)
        self.output_browse_button.clicked.connect(self._browse_output)
        self.begin_button.clicked.connect(self._on_begin)

    def _browse_folder(self):
        directory = QFileDialog.getExistingDirectory(self, _("Select Source Folder"), self.folder_path_edit.text())
        if directory:
            self.folder_path_edit.setText(directory)

    def _browse_cover(self):
        path, _filter = QFileDialog.getOpenFileName(self, _("Select Cover Image"), "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.cover_path_edit.setText(path)

    def _browse_output(self):
        path, _filter = QFileDialog.getSaveFileName(self, _("Save Audiobook As"), "", "M4B Audiobook (*.m4b)")
        if path:
            self.output_path_edit.setText(path)

    def _on_begin(self):
        output_path = self.output_path_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, _("No Output"), _("Choose an output .m4b file path."))
            return

        kwargs = {
            "output_path": output_path,
            "author": self.author_edit.text().strip() or None,
            "title": self.title_edit.text().strip() or None,
            "date": self.date_edit.text().strip() or None,
            "bitrate": self.bitrate_combo.currentText(),
            "cover": self.cover_path_edit.text().strip() or None,
            "use_filenames": self.use_filenames_check.isChecked(),
            "decode_durations": self.decode_durations_check.isChecked(),
            "keep_temp_files": self.keep_temp_check.isChecked(),
        }

        if self.folder_radio.isChecked():
            folder = self.folder_path_edit.text().strip()
            if not folder or not os.path.isdir(folder):
                QMessageBox.warning(self, _("Invalid Folder"), _("Choose a valid source folder."))
                return
            kwargs["input_dir"] = folder
        else:
            if self.file_list.is_empty():
                QMessageBox.warning(self, _("No Files"), _("Add at least one file to bind."))
                return
            kwargs["input_files"] = self.file_list.file_paths()

        ffmpeg_path, ffprobe_path = FFmpegHandler.get_ffmpeg_binary()
        kwargs["ffmpeg_executable"] = str(ffmpeg_path)
        kwargs["ffprobe_executable"] = str(ffprobe_path) if ffprobe_path else "ffprobe"

        self.job = BindJob(**kwargs)
        self.job.file_progress.connect(self._on_file_progress)
        self.job.log_line.connect(self._on_log_line)
        self.job.finished_job.connect(self._on_finished)

        self.progress_dialog = JobProgressDialog(0, self, title=_("Binding Audiobook"))
        self.progress_dialog.cancel_requested.connect(self._on_cancel)
        self.progress_dialog.pause_toggled.connect(self._on_pause_toggled)

        self.begin_button.setEnabled(False)
        self.job.start()
        self.progress_dialog.show()
        signal_manager.statusbar_message.emit(_("Binding audiobook..."))

    def _on_cancel(self):
        if self.job:
            self.job.stop()

    def _on_pause_toggled(self, paused: bool):
        if not self.job:
            return
        self.job.pause() if paused else self.job.resume()

    def _on_file_progress(self, text: str):
        if self.progress_dialog:
            self.progress_dialog.set_file_progress_detail(text)

    def _on_log_line(self, line: str):
        if self.progress_dialog:
            self.progress_dialog.append_live_log(line)

    def _on_finished(self, success: bool):
        self.begin_button.setEnabled(True)
        if self.progress_dialog:
            self.progress_dialog.append_file_result(_("OK: bind completed.") if success else _("FAILED: bind did not complete."))
            self.progress_dialog.mark_finished(success)
        signal_manager.statusbar_message.emit(
            _("Audiobook bound successfully") if success else _("Audiobook bind failed or was cancelled")
        )

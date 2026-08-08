import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QRadioButton,
    QButtonGroup, QStackedWidget, QLineEdit, QPushButton, QCheckBox, QComboBox,
    QFileDialog, QMessageBox
)

from gui_controls.ordered_file_list import OrderedFileListWidget
from gui_controls.job_progress_dialog import JobProgressDialog
from tools.ffmpeg_handler import FFmpegHandler
from tools.m4b_tools.combiner.job import CombineJob
from utilities import signal_manager

_BITRATES = ["32k", "48k", "64k", "96k", "128k", "160k", "192k", "256k"]


class CombineTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.job: CombineJob | None = None
        self.progress_dialog: JobProgressDialog | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        source_group = QGroupBox(_("Source"), self)
        source_layout = QVBoxLayout(source_group)

        mode_row = QHBoxLayout()
        self.csv_radio = QRadioButton(_("CSV File"), self)
        self.glob_radio = QRadioButton(_("Glob Pattern"), self)
        self.filelist_radio = QRadioButton(_("File List (manual order)"), self)
        self.csv_radio.setChecked(True)
        self.source_mode_group = QButtonGroup(self)
        for index, radio in enumerate((self.csv_radio, self.glob_radio, self.filelist_radio)):
            self.source_mode_group.addButton(radio, index)
            mode_row.addWidget(radio)
        mode_row.addStretch()
        source_layout.addLayout(mode_row)

        self.source_stack = QStackedWidget(self)

        csv_widget = QWidget(self)
        csv_row = QHBoxLayout(csv_widget)
        csv_row.setContentsMargins(0, 0, 0, 0)
        self.csv_path_edit = QLineEdit(self)
        self.csv_path_edit.setAccessibleName(_("Combine CSV file path"))
        self.csv_browse_button = QPushButton(_("Browse..."), self)
        csv_row.addWidget(self.csv_path_edit)
        csv_row.addWidget(self.csv_browse_button)
        self.source_stack.addWidget(csv_widget)

        glob_widget = QWidget(self)
        glob_row = QHBoxLayout(glob_widget)
        glob_row.setContentsMargins(0, 0, 0, 0)
        self.glob_pattern_edit = QLineEdit(self)
        self.glob_pattern_edit.setPlaceholderText(_("e.g. C:\\Books\\*.m4b"))
        self.glob_pattern_edit.setAccessibleName(_("Glob pattern"))
        glob_row.addWidget(self.glob_pattern_edit)
        self.source_stack.addWidget(glob_widget)

        self.file_list = OrderedFileListWidget(self, file_dialog_filter="Audiobook Files (*.m4b *.m4a);;All Files (*.*)")
        self.source_stack.addWidget(self.file_list)

        source_layout.addWidget(self.source_stack)
        layout.addWidget(source_group)

        metadata_group = QGroupBox(_("Combined Audiobook Metadata (overrides CSV, optional)"), self)
        metadata_form = QFormLayout(metadata_group)
        self.title_edit = QLineEdit(self)
        self.author_edit = QLineEdit(self)
        self.narrator_edit = QLineEdit(self)
        self.genre_edit = QLineEdit(self)
        self.year_edit = QLineEdit(self)
        self.description_edit = QLineEdit(self)

        cover_row = QHBoxLayout()
        self.cover_edit = QLineEdit(self)
        self.cover_edit.setPlaceholderText(_("File path or http(s):// URL"))
        self.cover_edit.setAccessibleName(_("Cover image path or URL"))
        self.cover_browse_button = QPushButton(_("Browse..."), self)
        cover_row.addWidget(self.cover_edit)
        cover_row.addWidget(self.cover_browse_button)

        metadata_form.addRow(_("Title"), self.title_edit)
        metadata_form.addRow(_("Author"), self.author_edit)
        metadata_form.addRow(_("Narrator"), self.narrator_edit)
        metadata_form.addRow(_("Genre"), self.genre_edit)
        metadata_form.addRow(_("Year"), self.year_edit)
        metadata_form.addRow(_("Description"), self.description_edit)
        metadata_form.addRow(_("Cover"), cover_row)
        layout.addWidget(metadata_group)

        options_group = QGroupBox(_("Options"), self)
        options_form = QFormLayout(options_group)
        self.preserve_chapters_check = QCheckBox(_("Preserve each source file's existing chapters"), self)
        self.bitrate_combo = QComboBox(self)
        self.bitrate_combo.addItems(_BITRATES)
        self.bitrate_combo.setCurrentText("64k")
        self.keep_temp_check = QCheckBox(_("Keep temporary files (debugging)"), self)
        options_form.addRow("", self.preserve_chapters_check)
        options_form.addRow(_("Bitrate"), self.bitrate_combo)
        options_form.addRow("", self.keep_temp_check)
        layout.addWidget(options_group)

        output_group = QGroupBox(_("Output"), self)
        output_row = QHBoxLayout(output_group)
        self.output_path_edit = QLineEdit(self)
        self.output_path_edit.setPlaceholderText(_("Optional if the CSV specifies output_path"))
        self.output_path_edit.setAccessibleName(_("Output audiobook file path"))
        self.output_browse_button = QPushButton(_("Browse..."), self)
        output_row.addWidget(self.output_path_edit)
        output_row.addWidget(self.output_browse_button)
        layout.addWidget(output_group)

        self.begin_button = QPushButton(_("Combine Audiobooks"), self)
        layout.addWidget(self.begin_button)
        layout.addStretch()

        self.csv_radio.toggled.connect(lambda checked: checked and self.source_stack.setCurrentIndex(0))
        self.glob_radio.toggled.connect(lambda checked: checked and self.source_stack.setCurrentIndex(1))
        self.filelist_radio.toggled.connect(lambda checked: checked and self.source_stack.setCurrentIndex(2))
        self.csv_browse_button.clicked.connect(self._browse_csv)
        self.cover_browse_button.clicked.connect(self._browse_cover)
        self.output_browse_button.clicked.connect(self._browse_output)
        self.begin_button.clicked.connect(self._on_begin)

    def _browse_csv(self):
        path, _filter = QFileDialog.getOpenFileName(self, _("Select Combine CSV"), "", "CSV Files (*.csv)")
        if path:
            self.csv_path_edit.setText(path)

    def _browse_cover(self):
        path, _filter = QFileDialog.getOpenFileName(self, _("Select Cover Image"), "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.cover_edit.setText(path)

    def _browse_output(self):
        path, _filter = QFileDialog.getSaveFileName(self, _("Save Combined Audiobook As"), "", "M4B Audiobook (*.m4b)")
        if path:
            self.output_path_edit.setText(path)

    def _on_begin(self):
        kwargs = {
            "output_file": self.output_path_edit.text().strip() or None,
            "title": self.title_edit.text().strip() or None,
            "author": self.author_edit.text().strip() or None,
            "narrator": self.narrator_edit.text().strip() or None,
            "genre": self.genre_edit.text().strip() or None,
            "year": self.year_edit.text().strip() or None,
            "description": self.description_edit.text().strip() or None,
            "cover": self.cover_edit.text().strip() or None,
            "preserve_existing_chapters": self.preserve_chapters_check.isChecked(),
            "bitrate": self.bitrate_combo.currentText(),
            "keep_temp_files": self.keep_temp_check.isChecked(),
        }

        if self.csv_radio.isChecked():
            csv_path = self.csv_path_edit.text().strip()
            if not csv_path or not os.path.exists(csv_path):
                QMessageBox.warning(self, _("Invalid CSV"), _("Choose a valid combine CSV file."))
                return
            kwargs["csv_file"] = csv_path
        elif self.glob_radio.isChecked():
            pattern = self.glob_pattern_edit.text().strip()
            if not pattern:
                QMessageBox.warning(self, _("No Pattern"), _("Enter a glob pattern."))
                return
            kwargs["input_pattern"] = pattern
        else:
            if self.file_list.is_empty():
                QMessageBox.warning(self, _("No Files"), _("Add at least one file to combine."))
                return
            kwargs["input_files"] = self.file_list.file_paths()

        if not kwargs["output_file"] and not self.csv_radio.isChecked():
            QMessageBox.warning(self, _("No Destination"), _("Choose an output file."))
            return

        ffmpeg_path, ffprobe_path = FFmpegHandler.get_ffmpeg_binary()
        kwargs["ffmpeg_executable"] = str(ffmpeg_path)
        kwargs["ffprobe_executable"] = str(ffprobe_path) if ffprobe_path else "ffprobe"

        self.job = CombineJob(**kwargs)
        self.job.overall_progress.connect(self._on_overall_progress)
        self.job.log_line.connect(self._on_log_line)
        self.job.finished_job.connect(self._on_finished)

        self.progress_dialog = JobProgressDialog(0, self, title=_("Combining Audiobooks"))
        self.progress_dialog.cancel_requested.connect(self._on_cancel)
        self.progress_dialog.pause_toggled.connect(self._on_pause_toggled)

        self.begin_button.setEnabled(False)
        self.job.start()
        self.progress_dialog.show()
        signal_manager.statusbar_message.emit(_("Combining audiobooks..."))

    def _on_cancel(self):
        if self.job:
            self.job.stop()

    def _on_pause_toggled(self, paused: bool):
        if not self.job:
            return
        self.job.pause() if paused else self.job.resume()

    def _on_overall_progress(self, current: int, total: int, filename: str):
        if self.progress_dialog:
            self.progress_dialog.set_overall_progress(current, total, os.path.basename(filename) if filename else "")

    def _on_log_line(self, line: str):
        if self.progress_dialog:
            self.progress_dialog.append_live_log(line)

    def _on_finished(self, success: bool):
        self.begin_button.setEnabled(True)
        if self.progress_dialog:
            self.progress_dialog.append_file_result(
                _("OK: combine completed.") if success else _("FAILED: combine did not complete.")
            )
            self.progress_dialog.mark_finished(success)
        signal_manager.statusbar_message.emit(
            _("Audiobooks combined successfully") if success else _("Combine failed or was cancelled")
        )

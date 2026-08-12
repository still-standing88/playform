import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit, QPushButton,
    QFileDialog, QMessageBox
)

from gui_controls.path_tree_widget import PathTreeWidget
from gui_controls.job_progress_dialog import JobProgressDialog
from tools.ffmpeg_handler import FFmpegHandler
from tools.m4b_tools.combiner.job import MetadataDumpJob
from utilities import signal_manager
from utilities.announcement_categories import AnnouncementCategory


def _announce(text):
    signal_manager.announce(text, AnnouncementCategory.TOOLS)


class MetadataDumpTab(QWidget):
    """Probes audiobook/audio files and exports one CSV row per chapter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.job: MetadataDumpJob | None = None
        self.progress_dialog: JobProgressDialog | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        source_group = QGroupBox(_("Source Files"), self)
        source_layout = QVBoxLayout(source_group)
        self.tree = PathTreeWidget(self)
        source_layout.addWidget(self.tree)

        button_row = QHBoxLayout()
        self.add_files_button = QPushButton(_("Add Files..."), self)
        self.add_folder_button = QPushButton(_("Add Folder..."), self)
        self.clear_button = QPushButton(_("Clear All"), self)
        button_row.addWidget(self.add_files_button)
        button_row.addWidget(self.add_folder_button)
        button_row.addStretch()
        button_row.addWidget(self.clear_button)
        source_layout.addLayout(button_row)
        layout.addWidget(source_group)

        output_group = QGroupBox(_("Output CSV"), self)
        output_row = QHBoxLayout(output_group)
        self.output_path_edit = QLineEdit(self)
        self.output_path_edit.setAccessibleName(_("Output CSV file path"))
        self.output_browse_button = QPushButton(_("Browse..."), self)
        output_row.addWidget(self.output_path_edit)
        output_row.addWidget(self.output_browse_button)
        layout.addWidget(output_group)

        self.begin_button = QPushButton(_("Dump Metadata to CSV"), self)
        layout.addWidget(self.begin_button)

        self.add_files_button.clicked.connect(self.tree.add_file_dialog)
        self.add_folder_button.clicked.connect(self.tree.add_folder_dialog)
        self.clear_button.clicked.connect(self.tree.clear_paths)
        self.output_browse_button.clicked.connect(self._browse_output)
        self.begin_button.clicked.connect(self._on_begin)

    def _browse_output(self):
        path, _filter = QFileDialog.getSaveFileName(self, _("Save Metadata CSV As"), "", "CSV Files (*.csv)")
        if path:
            self.output_path_edit.setText(path)

    def _resolve_files(self) -> list:
        files = []
        for path, entry_type, entry_formats in self.tree.iter_entries():
            if entry_type == "file":
                files.append(path)
            elif entry_type == "folder":
                extensions = set(entry_formats or [])
                try:
                    for item in sorted(os.listdir(path)):
                        full_path = os.path.join(path, item)
                        if not os.path.isfile(full_path):
                            continue
                        ext = os.path.splitext(item)[1].lstrip(".").lower()
                        if not extensions or ext in extensions:
                            files.append(full_path)
                except OSError:
                    continue
        return files

    def _on_begin(self):
        files = self._resolve_files()
        if not files:
            QMessageBox.warning(self, _("No Sources"), _("Add at least one file or folder."))
            return

        output_csv = self.output_path_edit.text().strip()
        if not output_csv:
            QMessageBox.warning(self, _("No Output"), _("Choose an output CSV path."))
            return

        _ffmpeg_path, ffprobe_path = FFmpegHandler.get_ffmpeg_binary()

        self.job = MetadataDumpJob(files, output_csv, str(ffprobe_path) if ffprobe_path else "ffprobe")
        self.job.overall_progress.connect(self._on_overall_progress)
        self.job.log_line.connect(self._on_log_line)
        self.job.finished_job.connect(self._on_finished)

        self.progress_dialog = JobProgressDialog(len(files), self, title=_("Dumping Metadata"), supports_pause=False)
        self.progress_dialog.cancel_requested.connect(self._on_cancel)

        self.begin_button.setEnabled(False)
        self.job.start()
        self.progress_dialog.show()
        _announce(_("Dumping audiobook metadata..."))

    def _on_cancel(self):
        if self.job:
            self.job.stop()

    def _on_overall_progress(self, current: int, total: int, filename: str):
        if self.progress_dialog:
            self.progress_dialog.set_overall_progress(current, total, os.path.basename(filename) if filename else "")

    def _on_log_line(self, line: str):
        if self.progress_dialog:
            self.progress_dialog.append_live_log(line)

    def _on_finished(self, success: bool, row_count: int):
        self.begin_button.setEnabled(True)
        if self.progress_dialog:
            self.progress_dialog.append_file_result(
                _("OK: wrote {count} row(s).").format(count=row_count) if success else _("FAILED or cancelled.")
            )
            self.progress_dialog.mark_finished(success)
        _announce(
            _("Metadata dump finished ({count} rows)").format(count=row_count) if success else _("Metadata dump failed")
        )

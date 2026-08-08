import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLineEdit,
    QPushButton, QDoubleSpinBox, QComboBox, QCheckBox, QFileDialog, QMessageBox, QLabel
)

from gui_controls.job_progress_dialog import JobProgressDialog
from tools.ffmpeg_handler import FFmpegHandler
from media_core.m4b_tools.slide import run_slide
from tools.m4b_tools.audiobook_tools.job import SimpleM4BTask
from utilities import signal_manager

_BITRATES = ["32k", "48k", "64k", "96k", "128k", "160k", "192k", "256k", "320k"]


class SlideTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.job: SimpleM4BTask | None = None
        self.progress_dialog: JobProgressDialog | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        note = QLabel(
            _("Shifts an existing audiobook's chapters in time and rewrites the file in place."),
            self
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        source_group = QGroupBox(_("Source (modified in place)"), self)
        source_row = QHBoxLayout(source_group)
        self.input_path_edit = QLineEdit(self)
        self.input_path_edit.setAccessibleName(_("Source audiobook file path"))
        self.input_browse_button = QPushButton(_("Browse..."), self)
        source_row.addWidget(self.input_path_edit)
        source_row.addWidget(self.input_browse_button)
        layout.addWidget(source_group)

        options_group = QGroupBox(_("Slide Options"), self)
        form = QFormLayout(options_group)
        self.duration_spin = QDoubleSpinBox(self)
        self.duration_spin.setRange(-36000.0, 36000.0)
        self.duration_spin.setSuffix(" s")
        self.duration_spin.setToolTip(_("Positive delays chapters, negative pulls them earlier."))
        self.trim_start_check = QCheckBox(_("Trim from start"), self)
        self.trim_start_spin = QDoubleSpinBox(self)
        self.trim_start_spin.setRange(0.0, 36000.0)
        self.trim_start_spin.setSuffix(" s")
        self.trim_start_spin.setEnabled(False)
        self.bitrate_combo = QComboBox(self)
        self.bitrate_combo.addItems(_BITRATES)
        self.bitrate_combo.setCurrentText("128k")

        trim_row = QHBoxLayout()
        trim_row.addWidget(self.trim_start_check)
        trim_row.addWidget(self.trim_start_spin)

        form.addRow(_("Slide Duration"), self.duration_spin)
        form.addRow(_("Trim Start"), trim_row)
        form.addRow(_("Re-encode Bitrate"), self.bitrate_combo)
        layout.addWidget(options_group)

        self.begin_button = QPushButton(_("Apply Slide"), self)
        layout.addWidget(self.begin_button)
        layout.addStretch()

        self.input_browse_button.clicked.connect(self._browse_input)
        self.trim_start_check.toggled.connect(self.trim_start_spin.setEnabled)
        self.begin_button.clicked.connect(self._on_begin)

    def _browse_input(self):
        path, _filter = QFileDialog.getOpenFileName(self, _("Select Audiobook File"))
        if path:
            self.input_path_edit.setText(path)

    def _on_begin(self):
        input_path = self.input_path_edit.text().strip()
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, _("Invalid Source"), _("Choose a valid source file."))
            return

        confirm = QMessageBox.question(
            self, _("Confirm"),
            _("This rewrites '{path}' in place. Continue?").format(path=os.path.basename(input_path)),
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        ffmpeg_path, ffprobe_path = FFmpegHandler.get_ffmpeg_binary()
        self.job = SimpleM4BTask(
            run_slide,
            input_path=input_path,
            duration=self.duration_spin.value(),
            trim_start=self.trim_start_spin.value() if self.trim_start_check.isChecked() else None,
            bitrate=self.bitrate_combo.currentText(),
            ffmpeg_executable=str(ffmpeg_path),
            ffprobe_executable=str(ffprobe_path) if ffprobe_path else "ffprobe",
        )
        self.job.log_line.connect(self._on_log_line)
        self.job.finished_job.connect(self._on_finished)

        self.progress_dialog = JobProgressDialog(0, self, title=_("Sliding Chapters"), supports_pause=False)
        self.progress_dialog.cancel_requested.connect(self.progress_dialog.accept)

        self.begin_button.setEnabled(False)
        self.job.start()
        self.progress_dialog.show()
        signal_manager.statusbar_message.emit(_("Sliding audiobook chapters..."))

    def _on_log_line(self, line: str):
        if self.progress_dialog:
            self.progress_dialog.append_live_log(line)

    def _on_finished(self, success: bool, error: str):
        self.begin_button.setEnabled(True)
        if self.progress_dialog:
            self.progress_dialog.append_file_result(
                _("OK: chapters shifted.") if success else _("FAILED: {error}").format(error=error)
            )
            self.progress_dialog.mark_finished(success)
        signal_manager.statusbar_message.emit(
            _("Chapters shifted successfully") if success else _("Slide failed")
        )

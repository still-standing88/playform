import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QRadioButton,
    QButtonGroup, QLineEdit, QPushButton, QCheckBox, QDoubleSpinBox, QSpinBox,
    QFileDialog, QMessageBox, QLabel
)

from tools.ffmpeg.batch_converter.convert_tab import AudioConvertPanel
from gui_controls.job_progress_dialog import JobProgressDialog
from tools.ffmpeg_handler import FFmpegHandler
from media_core.m4b_tools.naming import DEFAULT_CHAPTER_TEMPLATE
from tools.m4b_tools.audiobook_tools.job import SplitJob
from utilities import signal_manager
from utilities.announcement_categories import AnnouncementCategory


def _announce(text):
    signal_manager.announce(text, AnnouncementCategory.TOOLS)

_TEMPLATE_HELP = (
    "{book_title} {chapter_num} {chapter_title} {author} {narrator} {genre} {year} "
    "{ext} {original_filename} {duration} {duration_formatted}"
)


class SplitTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.job: SplitJob | None = None
        self.progress_dialog: JobProgressDialog | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        source_group = QGroupBox(_("Source"), self)
        source_row = QHBoxLayout(source_group)
        self.input_path_edit = QLineEdit(self)
        self.input_path_edit.setAccessibleName(_("Source audiobook file path"))
        self.input_browse_button = QPushButton(_("Browse..."), self)
        source_row.addWidget(self.input_path_edit)
        source_row.addWidget(self.input_browse_button)
        layout.addWidget(source_group)

        mode_group = QGroupBox(_("Split Mode"), self)
        mode_layout = QVBoxLayout(mode_group)
        mode_row = QHBoxLayout()
        self.chapters_radio = QRadioButton(_("By Embedded Chapters"), self)
        self.silence_radio = QRadioButton(_("By Detected Silence"), self)
        self.chapters_radio.setChecked(True)
        self.mode_button_group = QButtonGroup(self)
        self.mode_button_group.addButton(self.chapters_radio, 0)
        self.mode_button_group.addButton(self.silence_radio, 1)
        mode_row.addWidget(self.chapters_radio)
        mode_row.addWidget(self.silence_radio)
        mode_row.addStretch()
        mode_layout.addLayout(mode_row)

        self.silence_options_group = QGroupBox(_("Silence Detection Options"), self)
        silence_form = QFormLayout(self.silence_options_group)
        self.silence_duration_spin = QDoubleSpinBox(self)
        self.silence_duration_spin.setRange(0.1, 60.0)
        self.silence_duration_spin.setValue(3.0)
        self.silence_duration_spin.setSuffix(" s")
        self.silence_threshold_spin = QSpinBox(self)
        self.silence_threshold_spin.setRange(-90, 0)
        self.silence_threshold_spin.setValue(-35)
        self.silence_threshold_spin.setSuffix(" dB")
        self.trim_silence_check = QCheckBox(_("Trim silence from segment edges"), self)
        silence_form.addRow(_("Minimum Silence Duration"), self.silence_duration_spin)
        silence_form.addRow(_("Silence Threshold"), self.silence_threshold_spin)
        silence_form.addRow("", self.trim_silence_check)
        mode_layout.addWidget(self.silence_options_group)
        layout.addWidget(mode_group)

        window_group = QGroupBox(_("Time Window && Segment Filtering"), self)
        window_form = QFormLayout(window_group)
        self.start_time_edit = QLineEdit(self)
        self.start_time_edit.setPlaceholderText(_("seconds, optional"))
        self.end_time_edit = QLineEdit(self)
        self.end_time_edit.setPlaceholderText(_("seconds, optional"))
        self.min_segment_spin = QDoubleSpinBox(self)
        self.min_segment_spin.setRange(0.0, 3600.0)
        self.min_segment_spin.setValue(1.0)
        self.min_segment_spin.setSuffix(" s")
        self.padding_spin = QDoubleSpinBox(self)
        self.padding_spin.setRange(0.0, 30.0)
        self.padding_spin.setSuffix(" s")
        window_form.addRow(_("Start Time"), self.start_time_edit)
        window_form.addRow(_("End Time"), self.end_time_edit)
        window_form.addRow(_("Minimum Segment Length"), self.min_segment_spin)
        window_form.addRow(_("End Padding (silence)"), self.padding_spin)
        layout.addWidget(window_group)

        format_group = QGroupBox(_("Output Format"), self)
        format_layout = QVBoxLayout(format_group)
        self.format_panel = AudioConvertPanel(self)
        format_layout.addWidget(self.format_panel)
        layout.addWidget(format_group)

        naming_group = QGroupBox(_("Naming && Destination"), self)
        naming_form = QFormLayout(naming_group)
        self.template_edit = QLineEdit(DEFAULT_CHAPTER_TEMPLATE, self)
        template_help = QLabel(_("Available: {vars}").format(vars=_TEMPLATE_HELP), self)
        template_help.setWordWrap(True)
        self.include_cover_check = QCheckBox(_("Include cover art in each segment"), self)
        self.include_cover_check.setChecked(True)

        output_row = QHBoxLayout()
        self.output_dir_edit = QLineEdit(self)
        self.output_dir_edit.setAccessibleName(_("Output folder path"))
        self.output_browse_button = QPushButton(_("Browse..."), self)
        output_row.addWidget(self.output_dir_edit)
        output_row.addWidget(self.output_browse_button)

        naming_form.addRow(_("Naming Template"), self.template_edit)
        naming_form.addRow("", template_help)
        naming_form.addRow("", self.include_cover_check)
        naming_form.addRow(_("Output Folder"), output_row)
        layout.addWidget(naming_group)

        self.begin_button = QPushButton(_("Split Audiobook"), self)
        layout.addWidget(self.begin_button)

        self.input_browse_button.clicked.connect(self._browse_input)
        self.output_browse_button.clicked.connect(self._browse_output)
        self.silence_radio.toggled.connect(self.silence_options_group.setEnabled)
        self.begin_button.clicked.connect(self._on_begin)
        self.silence_options_group.setEnabled(False)

    def _browse_input(self):
        path, _filter = QFileDialog.getOpenFileName(self, _("Select Audiobook File"))
        if path:
            self.input_path_edit.setText(path)

    def _browse_output(self):
        directory = QFileDialog.getExistingDirectory(self, _("Select Output Folder"), self.output_dir_edit.text())
        if directory:
            self.output_dir_edit.setText(directory)

    def _on_begin(self):
        input_path = self.input_path_edit.text().strip()
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, _("Invalid Source"), _("Choose a valid source file."))
            return

        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            QMessageBox.warning(self, _("No Destination"), _("Choose an output folder."))
            return

        format_options = self.format_panel.selected_options()
        ffmpeg_path, ffprobe_path = FFmpegHandler.get_ffmpeg_binary()

        kwargs = {
            "input_path": input_path,
            "output_dir": output_dir,
            "mode": "silence" if self.silence_radio.isChecked() else "chapters",
            "output_format": format_options["format_id"],
            "template": self.template_edit.text().strip() or DEFAULT_CHAPTER_TEMPLATE,
            "start_time": float(self.start_time_edit.text()) if self.start_time_edit.text().strip() else None,
            "end_time": float(self.end_time_edit.text()) if self.end_time_edit.text().strip() else None,
            "minimum_segment_time": self.min_segment_spin.value(),
            "silence_duration": self.silence_duration_spin.value(),
            "silence_threshold": self.silence_threshold_spin.value(),
            "trim_silence": self.trim_silence_check.isChecked(),
            "padding": self.padding_spin.value(),
            "include_cover": self.include_cover_check.isChecked(),
            "sample_rate": format_options["sample_rate"],
            "bit_depth": format_options["bit_depth"],
            "bitrate_kbps": format_options["bit_rate_kbps"],
            "vbr_quality": format_options["vbr_quality"],
            "codec_option_values": format_options["codec_option_values"],
            "ffmpeg_executable": str(ffmpeg_path),
            "ffprobe_executable": str(ffprobe_path) if ffprobe_path else "ffprobe",
        }

        self.job = SplitJob(**kwargs)
        self.job.overall_progress.connect(self._on_overall_progress)
        self.job.file_completed.connect(self._on_file_completed)
        self.job.log_line.connect(self._on_log_line)
        self.job.finished_job.connect(self._on_finished)

        self.progress_dialog = JobProgressDialog(0, self, title=_("Splitting Audiobook"))
        self.progress_dialog.cancel_requested.connect(self._on_cancel)
        self.progress_dialog.pause_toggled.connect(self._on_pause_toggled)

        self.begin_button.setEnabled(False)
        self.job.start()
        self.progress_dialog.show()
        _announce(_("Splitting audiobook..."))

    def _on_cancel(self):
        if self.job:
            self.job.stop()

    def _on_pause_toggled(self, paused: bool):
        if not self.job:
            return
        self.job.pause() if paused else self.job.resume()

    def _on_overall_progress(self, current: int, total: int, filename: str):
        if self.progress_dialog:
            self.progress_dialog.set_overall_progress(current, total, filename)

    def _on_file_completed(self, path: str, success: bool, message: str):
        if self.progress_dialog:
            status = "OK" if success else "FAILED"
            self.progress_dialog.append_file_result(f"{status}: {os.path.basename(path)} — {message}")

    def _on_log_line(self, line: str):
        if self.progress_dialog:
            self.progress_dialog.append_live_log(line)

    def _on_finished(self, success: bool):
        self.begin_button.setEnabled(True)
        if self.progress_dialog:
            self.progress_dialog.mark_finished(success)
        _announce(
            _("Audiobook split finished") if success else _("Audiobook split failed, incomplete, or cancelled")
        )

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QFileDialog, QRadioButton, QButtonGroup, QStackedWidget, QCheckBox,
    QProgressDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal

from tools.ffmpeg_handler import FFmpegHandler
from media_core.ffmpeg import FFmpegError, Progress
from tools.ffmpeg.batch_converter.convert_tab import AudioConvertPanel, VideoConvertPanel
from media_core.ffmpeg.format_capabilities import build_ffmpeg_output_options
from tools.ffmpeg.media_extractor.image_panel import ImageExtractPanel
from utilities import signal_manager


class ExtractionThread(QThread):
    progress = Signal(Progress)
    stderr = Signal(str)
    finished_ok = Signal()
    error = Signal(str)

    def __init__(self, ffmpeg_instance):
        super().__init__()
        self.ffmpeg = ffmpeg_instance

    def run(self):
        try:
            @self.ffmpeg.on("progress")
            def _on_progress(prog: Progress):
                self.progress.emit(prog)

            @self.ffmpeg.on("stderr")
            def _on_stderr(line: str):
                self.stderr.emit(line)

            self.ffmpeg.execute()
            self.finished_ok.emit()
        except FFmpegError as error:
            self.error.emit(error.message)
        except Exception as error:
            self.error.emit(str(error))


class ExtractorUI(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread: ExtractionThread | None = None
        self.progress_dialog: QProgressDialog | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        input_row = QHBoxLayout()
        self.input_path_edit = QLineEdit(self)
        self.input_path_edit.textChanged.connect(self._update_button_state)
        self.browse_button = QPushButton(_("Browse..."), self)
        self.browse_button.clicked.connect(self._browse_input)
        input_row.addWidget(QLabel(_("Source File:")))
        input_row.addWidget(self.input_path_edit)
        input_row.addWidget(self.browse_button)
        layout.addLayout(input_row)

        mode_row = QHBoxLayout()
        self.audio_radio = QRadioButton(_("Audio"), self)
        self.video_radio = QRadioButton(_("Video"), self)
        self.image_radio = QRadioButton(_("Images"), self)
        self.audio_radio.setChecked(True)
        self.mode_group = QButtonGroup(self)
        for index, radio in enumerate((self.audio_radio, self.video_radio, self.image_radio)):
            self.mode_group.addButton(radio, index)
            mode_row.addWidget(radio)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        self.stack = QStackedWidget(self)
        self.audio_panel = AudioConvertPanel(self)
        self.video_panel = VideoConvertPanel(self)
        self.image_panel = ImageExtractPanel(self)
        self.stack.addWidget(self.audio_panel)
        self.stack.addWidget(self.video_panel)
        self.stack.addWidget(self.image_panel)
        layout.addWidget(self.stack)

        self.copy_video_stream_check = QCheckBox(_("Copy video stream without re-encoding (fast, no quality loss)"), self)
        self.copy_video_stream_check.setChecked(True)
        self.copy_video_stream_check.toggled.connect(lambda checked: self.video_panel.setEnabled(not checked))
        layout.addWidget(self.copy_video_stream_check)

        trim_row = QHBoxLayout()
        self.start_time_edit = QLineEdit("00:00:00", self)
        self.end_time_edit = QLineEdit(self)
        self.end_time_edit.setPlaceholderText(_("e.g. 00:01:30 or 90 (optional)"))
        trim_row.addWidget(QLabel(_("Start Time:")))
        trim_row.addWidget(self.start_time_edit)
        trim_row.addWidget(QLabel(_("End Time / Duration:")))
        trim_row.addWidget(self.end_time_edit)
        layout.addLayout(trim_row)

        self.extract_button = QPushButton(_("Extract"), self)
        self.extract_button.setEnabled(False)
        self.extract_button.clicked.connect(self._on_extract)
        layout.addWidget(self.extract_button)

        self.audio_radio.toggled.connect(self._on_mode_changed)
        self.video_radio.toggled.connect(self._on_mode_changed)
        self.image_radio.toggled.connect(self._on_mode_changed)
        self._on_mode_changed()

    def _on_mode_changed(self):
        if self.audio_radio.isChecked():
            self.stack.setCurrentIndex(0)
            self.copy_video_stream_check.setVisible(False)
        elif self.video_radio.isChecked():
            self.stack.setCurrentIndex(1)
            self.copy_video_stream_check.setVisible(True)
        else:
            self.stack.setCurrentIndex(2)
            self.copy_video_stream_check.setVisible(False)

    def _browse_input(self):
        path, _filter = QFileDialog.getOpenFileName(self, _("Select Source File"))
        if path:
            self.input_path_edit.setText(path)

    def _update_button_state(self):
        path = self.input_path_edit.text().strip()
        self.extract_button.setEnabled(bool(path) and os.path.exists(path))

    def _on_extract(self):
        input_path = self.input_path_edit.text().strip()
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, _("Warning"), _("Please select a valid source file."))
            return

        output_dir = QFileDialog.getExistingDirectory(self, _("Select Output Directory"))
        if not output_dir:
            return

        ffmpeg = FFmpegHandler.create_ffmpeg_instance().option("y")
        input_options = {}
        start_time = self.start_time_edit.text().strip()
        if start_time and start_time != "00:00:00":
            input_options["ss"] = start_time

        base_name = os.path.splitext(os.path.basename(input_path))[0]

        if self.audio_radio.isChecked():
            options = self.audio_panel.selected_options()
            output_kwargs = build_ffmpeg_output_options(
                options["format_id"], sample_rate=options["sample_rate"], bit_depth=options["bit_depth"],
                bitrate_kbps=options["bit_rate_kbps"], vbr_quality=options["vbr_quality"],
                codec_option_values=options["codec_option_values"],
            )
            output_kwargs["vn"] = None
            self._apply_end_time(output_kwargs)
            from media_core.ffmpeg.format_capabilities import get_format
            extension = get_format(options["format_id"]).extension
            output_path = os.path.join(output_dir, f"{base_name}_audio.{extension}")

        elif self.video_radio.isChecked():
            output_kwargs = {"an": None}
            if self.copy_video_stream_check.isChecked():
                output_kwargs["c:v"] = "copy"
                extension = os.path.splitext(input_path)[1] or ".mp4"
            else:
                video_options = self.video_panel.selected_options()
                output_kwargs["c:v"] = video_options["codec"]
                if video_options["resolution"]:
                    output_kwargs["s"] = video_options["resolution"]
                if video_options["video_bit_rate"]:
                    output_kwargs["b:v"] = video_options["video_bit_rate"]
                if video_options["framerate"]:
                    output_kwargs["r"] = video_options["framerate"]
                from tools.utils import get_container_from_format
                extension = get_container_from_format(video_options["format_label"]) or ".mp4"
            self._apply_end_time(output_kwargs)
            output_path = os.path.join(output_dir, f"{base_name}_video{extension}")

        else:
            options = self.image_panel.selected_options()
            output_kwargs = {"c:v": options["codec"]}
            if options["codec"] == "mjpeg":
                output_kwargs["qscale:v"] = max(1, round((100 - options["quality"]) / 3))

            if options["mode"] == 0:
                pass
            elif options["mode"] == 1:
                input_options["ss"] = options["start_time"]
                output_kwargs["t"] = options["duration"]
            elif options["mode"] == 2:
                output_kwargs["vf"] = f"fps={options['rate']}"
            elif options["mode"] == 3:
                input_options["ss"] = options["start_time"]
                output_kwargs["frames:v"] = 1

            pattern = "frame.%s" % options["extension"] if options["mode"] == 3 else f"frame-%04d.{options['extension']}"
            output_path = os.path.join(output_dir, pattern)

        ffmpeg.input(input_path, **input_options).output(output_path, **output_kwargs)
        self._run_task(ffmpeg, _("Extracting..."))
        signal_manager.statusbar_message.emit(_("Starting extraction"))

    def _apply_end_time(self, output_kwargs: dict):
        end_time = self.end_time_edit.text().strip()
        if not end_time:
            return
        if ":" in end_time:
            output_kwargs["to"] = end_time
        else:
            output_kwargs["t"] = end_time

    def _run_task(self, ffmpeg_instance, title: str):
        self.progress_dialog = QProgressDialog(title, _("Cancel"), 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)

        self.thread = ExtractionThread(ffmpeg_instance)
        self.thread.progress.connect(self._on_progress)
        self.thread.stderr.connect(self._on_stderr)
        self.thread.finished_ok.connect(self._on_finished)
        self.thread.error.connect(self._on_error)
        self.progress_dialog.canceled.connect(self.thread.terminate)
        self.thread.start()
        self.progress_dialog.show()

    def _on_progress(self, progress: Progress):
        if self.progress_dialog:
            self.progress_dialog.setLabelText(
                _("Time: {time} | Speed: {speed:.2f}x").format(time=progress.time, speed=progress.speed)
            )

    def _on_stderr(self, line: str):
        if self.progress_dialog and "frame=" not in self.progress_dialog.labelText():
            self.progress_dialog.setLabelText(line)

    def _on_finished(self):
        if self.progress_dialog and not self.progress_dialog.wasCanceled():
            self.progress_dialog.close()
            QMessageBox.information(self, _("Success"), _("Extraction completed successfully."))
            signal_manager.statusbar_message.emit(_("Extraction completed successfully"))

    def _on_error(self, message: str):
        if self.progress_dialog and not self.progress_dialog.wasCanceled():
            self.progress_dialog.close()
            QMessageBox.critical(self, _("Error"), _("An error occurred: {message}").format(message=message))
            signal_manager.statusbar_message.emit(_("Extraction failed"))

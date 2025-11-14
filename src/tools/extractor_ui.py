import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QFileDialog, QComboBox, QProgressDialog, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, QThread, Signal
from .ffmpeg_handler import FFmpegHandler
from ffmpeg import FFmpegError, Progress
from .utils import get_audio_formats_map, get_container_from_format
from utilities import signal_manager

class FFmpegTaskThread(QThread):
    progress = Signal(Progress)
    stderr = Signal(str)
    finished = Signal(bytes)
    error = Signal(str)

    def __init__(self, ffmpeg_instance):
        super().__init__()
        self.ffmpeg = ffmpeg_instance

    def run(self):
        try:
            @self.ffmpeg.on("progress")
            def on_progress(prog: Progress):
                self.progress.emit(prog)
            
            @self.ffmpeg.on("stderr")
            def on_stderr(line: str):
                self.stderr.emit(line)

            output = self.ffmpeg.execute()
            self.finished.emit(output)
        except FFmpegError as e:
            self.error.emit(e.message)
        except Exception as e:
            self.error.emit(str(e))

class ExtractorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.thread: FFmpegTaskThread | None = None
        self.progress_dialog: QProgressDialog | None = None

        self.main_layout = QVBoxLayout(self)

        self.input_path = QLineEdit()
        self.input_path.setAccessibleName("Video file for extraction")
        self.input_path.textChanged.connect(self.update_action_buttons)
        self.browse_button = QPushButton("Browse Video")
        self.browse_button.clicked.connect(self.browse_video)
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Video File:"))
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(self.browse_button)
        self.main_layout.addLayout(input_layout)

        self.setup_audio_extraction_group()
        self.setup_image_extraction_group()

        self.main_layout.addStretch()
        self.update_action_buttons()

    def setup_audio_extraction_group(self):
        audio_group = QGroupBox("Audio Extraction")
        audio_layout = QVBoxLayout()

        self.audio_format_combo = QComboBox()
        self.audio_format_combo.setAccessibleName("Audio output format")
        self.audio_formats = get_audio_formats_map()
        self.audio_format_combo.addItems(list(self.audio_formats.keys()))
        audio_layout.addWidget(QLabel("Output Format:"))
        audio_layout.addWidget(self.audio_format_combo)

        time_layout = QHBoxLayout()
        self.audio_start_time = QLineEdit("00:00:00")
        self.audio_start_time.setAccessibleName("Audio extraction start time")
        self.audio_end_time = QLineEdit()
        self.audio_end_time.setPlaceholderText("e.g., 00:01:30 or 90")
        self.audio_end_time.setAccessibleName("Audio extraction end time or duration")
        time_layout.addWidget(QLabel("Start Time (HH:MM:SS):"))
        time_layout.addWidget(self.audio_start_time)
        time_layout.addWidget(QLabel("End Time or Duration (optional):"))
        time_layout.addWidget(self.audio_end_time)
        audio_layout.addLayout(time_layout)

        self.extract_audio_button = QPushButton("Extract Audio")
        self.extract_audio_button.setEnabled(False)
        self.extract_audio_button.clicked.connect(self.extract_audio)
        audio_layout.addWidget(self.extract_audio_button)
        
        audio_group.setLayout(audio_layout)
        self.main_layout.addWidget(audio_group)

    def setup_image_extraction_group(self):
        image_group = QGroupBox("Image Extraction")
        image_layout = QVBoxLayout()

        self.image_mode_combo = QComboBox()
        self.image_mode_combo.setAccessibleName("Image extraction mode")
        self.image_mode_combo.addItems(["Extract All Frames", "Extract Range", "Extract 1 Image Per Second"])
        image_layout.addWidget(QLabel("Extraction Mode:"))
        image_layout.addWidget(self.image_mode_combo)

        time_layout = QHBoxLayout()
        self.image_start_time = QLineEdit("00:00:00")
        self.image_start_time.setAccessibleName("Image extraction start time")
        self.image_duration = QLineEdit("5")
        self.image_duration.setAccessibleName("Image extraction duration in seconds")
        time_layout.addWidget(QLabel("Start Time (HH:MM:SS):"))
        time_layout.addWidget(self.image_start_time)
        time_layout.addWidget(QLabel("Duration (seconds):"))
        time_layout.addWidget(self.image_duration)
        image_layout.addLayout(time_layout)

        self.extract_images_button = QPushButton("Extract Images")
        self.extract_images_button.setEnabled(False)
        self.extract_images_button.clicked.connect(self.extract_images)
        image_layout.addWidget(self.extract_images_button)

        image_group.setLayout(image_layout)
        self.main_layout.addWidget(image_group)

    def browse_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File")
        if file_path:
            self.input_path.setText(file_path)
            self.update_action_buttons()

    def run_ffmpeg_task(self, ffmpeg_instance, title):
        self.progress_dialog = QProgressDialog(title, "Cancel", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)

        self.thread = FFmpegTaskThread(ffmpeg_instance)
        self.thread.progress.connect(self.update_progress)
        self.thread.stderr.connect(self.update_stderr)
        self.thread.finished.connect(self.on_finished)
        self.thread.error.connect(self.on_error)
        self.progress_dialog.canceled.connect(self.thread.terminate)
        self.thread.start()
        self.progress_dialog.show()

    def extract_audio(self):
        input_video = self.input_path.text()
        if not input_video or not os.path.exists(input_video):
            QMessageBox.warning(self, "Warning", "Please select a valid input video file.")
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return

        format_name = self.audio_format_combo.currentText()
        codec = self.audio_formats[format_name]
        extension = get_container_from_format(format_name)
        output_path = os.path.join(output_dir, f"extracted_audio{extension}")

        ffmpeg = FFmpegHandler.create_ffmpeg_instance().option("y")
        
        input_options = {}
        start_time = self.audio_start_time.text()
        if start_time and start_time != "00:00:00":
            input_options['ss'] = start_time
        
        output_options = {'codec:a': codec, 'vn': None}
        end_time_or_duration = self.audio_end_time.text()
        if end_time_or_duration:
            if ':' in end_time_or_duration:
                output_options['to'] = end_time_or_duration
            else:
                output_options['t'] = end_time_or_duration

        ffmpeg.input(input_video, **input_options).output(output_path, **output_options)
        self.run_ffmpeg_task(ffmpeg, "Extracting Audio...")
        signal_manager.statusbar_message.emit("Starting audio extraction")

    def extract_images(self):
        input_video = self.input_path.text()
        if not input_video or not os.path.exists(input_video):
            QMessageBox.warning(self, "Warning", "Please select a valid input video file.")
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory for Images")
        if not output_dir:
            return

        ffmpeg = FFmpegHandler.create_ffmpeg_instance().option("y")
        mode = self.image_mode_combo.currentIndex()
        output_pattern = os.path.join(output_dir, "frame-%04d.png")

        input_options = {}
        output_options = {}

        if mode == 0:
            ffmpeg.input(input_video).output(output_pattern, **output_options)
        elif mode == 1:
            start = self.image_start_time.text()
            duration = self.image_duration.text()
            input_options['ss'] = start
            output_options['t'] = duration
            ffmpeg.input(input_video, **input_options).output(output_pattern, **output_options)
        elif mode == 2:
            output_options['vf'] = 'fps=1'
            ffmpeg.input(input_video).output(output_pattern, **output_options)

        self.run_ffmpeg_task(ffmpeg, "Extracting Images...")
        signal_manager.statusbar_message.emit("Starting image extraction")

    def update_progress(self, progress: Progress):
        if self.progress_dialog:
            progress_text = (
                f"Frame: {progress.frame} | "
                f"Time: {progress.time} | "
                f"Bitrate: {progress.bitrate:.2f} kbps | "
                f"Speed: {progress.speed:.2f}x"
            )
            self.progress_dialog.setLabelText(progress_text)
    
    def update_stderr(self, line: str):
        if self.progress_dialog and "frame=" not in self.progress_dialog.labelText():
             self.progress_dialog.setLabelText(line)

    def on_finished(self, output):
        if self.progress_dialog and not self.progress_dialog.wasCanceled():
            self.progress_dialog.close()
            QMessageBox.information(self, "Success", "Extraction completed successfully.")
            signal_manager.statusbar_message.emit("Extraction completed successfully")

    def on_error(self, message):
        if self.progress_dialog and not self.progress_dialog.wasCanceled():
            self.progress_dialog.close()
            QMessageBox.critical(self, "Error", f"An error occurred: {message}")
            signal_manager.statusbar_message.emit("Extraction failed")

    def update_action_buttons(self):
        path = self.input_path.text()
        enabled = bool(path) and os.path.exists(path)
        self.extract_audio_button.setEnabled(enabled)
        self.extract_images_button.setEnabled(enabled)
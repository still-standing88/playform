import os
from gettext import gettext as _
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QFileDialog, QComboBox, QProgressDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from .ffmpeg_handler import FFmpegHandler
from media_core.ffmpeg import FFmpegError, Progress
from utilities import signal_manager

class FFmpegTaskThread(QThread):
    progress = Signal(Progress)
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

            output = self.ffmpeg.execute()
            self.finished.emit(output)
        except FFmpegError as e:
            self.error.emit(e.message)
        except Exception as e:
            self.error.emit(str(e))

class ThumbnailGeneratorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.thread: FFmpegTaskThread | None = None
        self.progress_dialog: QProgressDialog | None = None
        
        self.main_layout = QVBoxLayout(self)

        self.input_path = QLineEdit()
        self.input_path.setAccessibleName(_("Video file input path"))
        self.input_path.textChanged.connect(self.update_action_buttons)
        self.browse_button = QPushButton(_("Browse Video"))
        self.browse_button.clicked.connect(self.browse_video)
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel(_("Video File:")))
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(self.browse_button)
        self.main_layout.addLayout(input_layout)

        self.mode_combo = QComboBox()
        self.mode_combo.setAccessibleName(_("Thumbnail generation mode"))
        self.mode_combo.addItems([
            _("Manual Frame Selection"),
            _("Automatic Thumbnail Filter"),
            _("Select from Scene Changes")
        ])
        self.mode_combo.currentIndexChanged.connect(self.update_options)
        self.main_layout.addWidget(QLabel(_("Generation Mode:")))
        self.main_layout.addWidget(self.mode_combo)

        self.manual_options_widget = QWidget()
        manual_layout = QVBoxLayout(self.manual_options_widget)
        manual_layout.setContentsMargins(0,0,0,0)
        manual_layout.addWidget(QLabel(_("Timestamp (HH:MM:SS):")))
        self.timestamp_edit = QLineEdit("00:00:15")
        self.timestamp_edit.setAccessibleName(_("Timestamp for manual frame selection"))
        manual_layout.addWidget(self.timestamp_edit)
        self.main_layout.addWidget(self.manual_options_widget)

        self.scene_options_widget = QWidget()
        scene_layout = QVBoxLayout(self.scene_options_widget)
        scene_layout.setContentsMargins(0,0,0,0)
        scene_layout.addWidget(QLabel(_("Number of Images to Generate:")))
        self.num_frames_edit = QLineEdit("5")
        self.num_frames_edit.setAccessibleName(_("Number of images to generate from scene changes"))
        scene_layout.addWidget(self.num_frames_edit)
        scene_layout.addWidget(QLabel(_("Scene Change Threshold (0.0-1.0):")))
        self.scene_threshold_edit = QLineEdit("0.4")
        self.scene_threshold_edit.setAccessibleName(_("Scene change detection threshold"))
        scene_layout.addWidget(self.scene_threshold_edit)
        self.main_layout.addWidget(self.scene_options_widget)

        self.generate_button = QPushButton(_("Generate Thumbnail(s)"))
        self.generate_button.setEnabled(False)
        self.generate_button.clicked.connect(self.generate_thumbnail)
        self.main_layout.addWidget(self.generate_button)

        self.main_layout.addStretch()

        self.update_options(0)
        self.update_action_buttons()

    def browse_video(self):
        file_path, selected_filter = QFileDialog.getOpenFileName(self, _("Select Video File"))
        if file_path:
            self.input_path.setText(file_path)
            self.update_action_buttons()

    def update_options(self, index):
        self.manual_options_widget.setVisible(index == 0)
        self.scene_options_widget.setVisible(index == 2)

    def generate_thumbnail(self):
        input_video = self.input_path.text()
        if not input_video or not os.path.exists(input_video):
            QMessageBox.warning(self, _("Warning"), _("Please select a valid input video file."))
            return

        output_dir = QFileDialog.getExistingDirectory(self, _("Select Output Directory"))
        if not output_dir:
            return

        ffmpeg = FFmpegHandler.create_ffmpeg_instance()
        ffmpeg.option("y")

        mode = self.mode_combo.currentIndex()
        
        try:
            output_options = {}
            if mode == 0:
                timestamp = self.timestamp_edit.text()
                output_path = os.path.join(output_dir, "thumbnail.png")
                output_options['frames:v'] = 1
                ffmpeg.input(input_video, ss=timestamp).output(output_path, **output_options)
            elif mode == 1:
                output_path = os.path.join(output_dir, "thumbnail_auto.png")
                output_options['vf'] = "thumbnail"
                output_options['frames:v'] = 1
                ffmpeg.input(input_video).output(output_path, **output_options)
            elif mode == 2:
                num_frames = self.num_frames_edit.text()
                threshold = self.scene_threshold_edit.text()
                output_pattern = os.path.join(output_dir, "scene-%02d.png")
                output_options['vf'] = f"select=gt(scene\\,{threshold})"
                output_options['vsync'] = "vfr"
                output_options['frames:v'] = int(num_frames)
                ffmpeg.input(input_video).output(output_pattern, **output_options)

            self.progress_dialog = QProgressDialog(_("Starting generation..."), _("Cancel"), 0, 0, self)
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            
            self.thread = FFmpegTaskThread(ffmpeg)
            self.thread.progress.connect(self.update_progress)
            self.thread.finished.connect(self.on_finished)
            self.thread.error.connect(self.on_error)
            self.progress_dialog.canceled.connect(self.thread.terminate)
            self.thread.start()
            self.progress_dialog.show()
            signal_manager.statusbar_message.emit(_("Starting thumbnail generation"))

        except Exception as e:
            QMessageBox.critical(self, _("Error"), _("Failed to start process: {error}").format(error=e))
            signal_manager.statusbar_message.emit(_("Failed to start thumbnail generation"))

    def update_progress(self, progress: Progress):
        if self.progress_dialog:
            progress_text = (
                f"Frame: {progress.frame} | "
                f"Time: {progress.time} | "
                f"Bitrate: {progress.bitrate:.2f} kbps | "
                f"Speed: {progress.speed:.2f}x"
            )
            self.progress_dialog.setLabelText(progress_text)

    def on_finished(self, output):
        if self.progress_dialog and not self.progress_dialog.wasCanceled():
            self.progress_dialog.close()
            QMessageBox.information(self, _("Success"), _("Thumbnail generation completed successfully."))
            signal_manager.statusbar_message.emit(_("Thumbnail generation completed"))

    def on_error(self, message):
        if self.progress_dialog and not self.progress_dialog.wasCanceled():
            self.progress_dialog.close()
            QMessageBox.critical(self, _("Error"), _("An error occurred: {message}").format(message=message))
            signal_manager.statusbar_message.emit(_("Thumbnail generation failed"))
    
    def update_action_buttons(self):
        path = self.input_path.text()
        enabled = bool(path) and os.path.exists(path)
        self.generate_button.setEnabled(enabled)

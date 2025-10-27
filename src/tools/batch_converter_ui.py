import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QComboBox, QProgressDialog, QMessageBox, QListWidget,
    QGroupBox
)
from PySide6.QtCore import Qt, QThread, Signal
from .ffmpeg_handler import FFmpegHandler
from ffmpeg import FFmpegError, Progress
from .utils import (
    get_common_sample_rates, get_common_audio_bitrates, get_common_video_bitrates,
    get_audio_formats_map, get_video_formats_map, get_container_from_format
)

class FFmpegBatchThread(QThread):
    file_progress = Signal(str)
    overall_progress = Signal(int, int, str)
    finished = Signal()
    error = Signal(str, str)

    def __init__(self, files, output_dir, conversion_options):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.options = conversion_options
        self._is_running = True

    def run(self):
        total_files = len(self.files)
        for i, input_file in enumerate(self.files):
            if not self._is_running:
                break
            
            try:
                base_name = os.path.splitext(os.path.basename(input_file))[0]
                self.overall_progress.emit(i, total_files, base_name)
                
                codec = self.options['codec']
                extension = self.options['extension']
                output_file = os.path.join(self.output_dir, f"{base_name}{extension}")

                ffmpeg = FFmpegHandler.create_ffmpeg_instance().option("y")
                
                output_opts = {}
                if self.options['type'] == 'video':
                    output_opts['codec:v'] = codec
                else:
                    output_opts['codec:a'] = codec
                    if self.options.get('sample_rate'):
                        output_opts['ar'] = self.options['sample_rate']
                
                if self.options.get('bitrate'):
                    bitrate_key = 'b:v' if self.options['type'] == 'video' else 'b:a'
                    output_opts[bitrate_key] = self.options['bitrate']

                ffmpeg.input(input_file).output(output_file, **output_opts)

                @ffmpeg.on("progress")
                def on_progress(progress: Progress):
                    self.file_progress.emit(f"Time: {progress.time}, Speed: {progress.speed:.2f}x")

                ffmpeg.execute()
            except FFmpegError as e:
                self.error.emit(input_file, e.message)
                continue
            except Exception as e:
                self.error.emit(input_file, str(e))
                continue
        
        if self._is_running:
            self.overall_progress.emit(total_files, total_files, "Done")
            self.finished.emit()

    def stop(self):
        self._is_running = False


class BatchConverterUI(QWidget):
    def __init__(self):
        super().__init__()
        self.thread: FFmpegBatchThread | None = None
        self.progress_dialog: QProgressDialog | None = None
        
        self.main_layout = QVBoxLayout(self)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.main_layout.addWidget(self.file_list)

        button_layout = QHBoxLayout()
        self.add_files_button = QPushButton("Add Files")
        self.add_files_button.clicked.connect(self.add_files)
        self.remove_files_button = QPushButton("Remove Selected")
        self.remove_files_button.clicked.connect(self.remove_files)
        button_layout.addWidget(self.add_files_button)
        button_layout.addWidget(self.remove_files_button)
        self.main_layout.addLayout(button_layout)

        self.setup_conversion_options()

        self.start_button = QPushButton("Start Batch Conversion")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_conversion)
        self.main_layout.addWidget(self.start_button)
        
        self.update_buttons_state()

    def setup_conversion_options(self):
        options_group = QGroupBox("Conversion Options")
        options_layout = QVBoxLayout()

        self.type_combo = QComboBox()
        self.type_combo.setAccessibleName("Conversion type (audio or video)")
        self.type_combo.addItems(["Audio", "Video"])
        self.type_combo.currentIndexChanged.connect(self.update_format_combo)
        options_layout.addWidget(QLabel("Conversion Type:"))
        options_layout.addWidget(self.type_combo)

        self.format_combo = QComboBox()
        self.format_combo.setAccessibleName("Target format")
        options_layout.addWidget(QLabel("Target Format:"))
        options_layout.addWidget(self.format_combo)

        self.samplerate_combo = QComboBox()
        self.samplerate_combo.setAccessibleName("Audio sample rate")
        self.samplerate_combo.setEditable(True)
        self.samplerate_combo.addItems(get_common_sample_rates())
        self.samplerate_combo.setCurrentText("44100")
        options_layout.addWidget(QLabel("Sample Rate (Audio):"))
        options_layout.addWidget(self.samplerate_combo)

        self.bitrate_combo = QComboBox()
        self.bitrate_combo.setAccessibleName("Target bitrate")
        self.bitrate_combo.setEditable(True)
        options_layout.addWidget(QLabel("Bitrate:"))
        options_layout.addWidget(self.bitrate_combo)
        
        options_group.setLayout(options_layout)
        self.main_layout.addWidget(options_group)
        self.update_format_combo(0)

    def update_format_combo(self, index):
        self.format_combo.clear()
        self.bitrate_combo.clear()
        if index == 0:
            self.audio_formats = get_audio_formats_map()
            self.format_combo.addItems(list(self.audio_formats.keys()))
            self.bitrate_combo.addItems(get_common_audio_bitrates())
            self.bitrate_combo.setCurrentText("192k")
            self.samplerate_combo.setEnabled(True)
        else:
            self.video_formats = get_video_formats_map()
            self.format_combo.addItems(list(self.video_formats.keys()))
            self.bitrate_combo.addItems(get_common_video_bitrates())
            self.bitrate_combo.setCurrentText("4000k")
            self.samplerate_combo.setEnabled(False)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select files to convert")
        self.file_list.addItems(files)
        self.update_buttons_state()

    def remove_files(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))
        self.update_buttons_state()

    def start_conversion(self):
        files = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        if not files:
            QMessageBox.warning(self, "Warning", "No files to convert.")
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return

        conv_type = self.type_combo.currentText().lower()
        format_name = self.format_combo.currentText()
        
        options = {'type': conv_type}
        if conv_type == 'audio':
            options['codec'] = self.audio_formats[format_name]
            options['sample_rate'] = self.samplerate_combo.currentText()
            options['bitrate'] = self.bitrate_combo.currentText()
        else:
            options['codec'] = self.video_formats[format_name]
            options['bitrate'] = self.bitrate_combo.currentText()
        options['extension'] = get_container_from_format(format_name)

        self.progress_dialog = QProgressDialog("Batch Converting...", "Cancel", 0, len(files), self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)

        self.thread = FFmpegBatchThread(files, output_dir, options)
        self.thread.overall_progress.connect(self.update_progress)
        self.thread.file_progress.connect(self.update_file_progress)
        self.thread.finished.connect(self.on_finished)
        self.thread.error.connect(self.on_error)
        self.progress_dialog.canceled.connect(self.thread.stop)
        self.thread.start()
        self.progress_dialog.show()

    def update_buttons_state(self):
        has_files = self.file_list.count() > 0
        self.start_button.setEnabled(has_files)

    def update_progress(self, value, total, filename):
        if self.progress_dialog:
            self.progress_dialog.setLabelText(f"Converting file {value+1} of {total}: {filename}")
            self.progress_dialog.setValue(value)

    def update_file_progress(self, progress_str):
        if self.progress_dialog:
            current_text = self.progress_dialog.labelText()
            base_text = current_text.split("...")[0]
            self.progress_dialog.setLabelText(f"{base_text}... {progress_str}")

    def on_finished(self):
        if self.progress_dialog and not self.progress_dialog.wasCanceled():
            self.progress_dialog.setValue(self.progress_dialog.maximum())
            QMessageBox.information(self, "Success", "Batch conversion completed.")
            self.progress_dialog.close()

    def on_error(self, filename, message):
        error_msg = f"Failed to convert {os.path.basename(filename)}:\n{message}"
        QMessageBox.warning(self, "Conversion Error", error_msg)
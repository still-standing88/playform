import os
from gettext import gettext as _
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QComboBox, QCheckBox, QPushButton, QListWidget, QFileDialog,
    QListWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from .handler import detect_encoding, convert_and_clean_subtitles
from utilities import signal_manager

COMMON_ENCODINGS = ['utf-8', 'utf-16', 'windows-1252', 'latin-1', 'iso-8859-1', 'gbk', 'shift_jis']

class SubtitleConverterThread(QThread):
    progress = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, file_paths, output_dir, options):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir
        self.options = options
        self._is_running = True

    def run(self):
        if not self._is_running:
            return
        
        self.progress.emit(_("Starting conversion..."))
        result = convert_and_clean_subtitles(self.file_paths, self.output_dir, self.options)
        
        if result.startswith("Success"):
            self.progress.emit(result)
            self.finished.emit()
        else:
            self.error.emit(result)

    def stop(self):
        self._is_running = False

class SubtitleConverterUI(QWidget):
    def __init__(self):
        super().__init__()
        self.file_paths = []
        self.thread: SubtitleConverterThread | None = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        file_group = QGroupBox(_("Files for Conversion (Batch)"))
        file_layout = QVBoxLayout()
        self.file_list_widget = QListWidget()
        file_buttons_layout = QHBoxLayout()
        add_files_button = QPushButton(_("Add Files"))
        add_files_button.clicked.connect(self.add_files)
        clear_files_button = QPushButton(_("Clear"))
        clear_files_button.clicked.connect(self.clear_files)
        file_buttons_layout.addWidget(add_files_button)
        file_buttons_layout.addWidget(clear_files_button)
        file_layout.addWidget(self.file_list_widget)
        file_layout.addLayout(file_buttons_layout)
        file_group.setLayout(file_layout)

        options_group = QGroupBox(_("Conversion Options"))
        options_layout = QFormLayout()
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(["srt", "ass", "ssa", "microdvd", "json", "mpl2", "tmp", "vtt"])
        self.input_encoding_combo = QComboBox()
        self.input_encoding_combo.setEditable(True)
        self.input_encoding_combo.addItems(COMMON_ENCODINGS)
        self.input_encoding_combo.setCurrentText("utf-8")
        self.output_encoding_combo = QComboBox()
        self.output_encoding_combo.setEditable(True)
        self.output_encoding_combo.addItems(COMMON_ENCODINGS)
        self.output_encoding_combo.setCurrentText("utf-8")
        self.clean_checkbox = QCheckBox(_("Remove miscellaneous events"))
        options_layout.addRow(_("Output Format:"), self.output_format_combo)
        options_layout.addRow(_("Input Encoding:"), self.input_encoding_combo)
        options_layout.addRow(_("Output Encoding:"), self.output_encoding_combo)
        options_layout.addRow(self.clean_checkbox)
        options_group.setLayout(options_layout)

        advanced_group = QGroupBox(_("Advanced Format Options"))
        advanced_group.setCheckable(True)
        advanced_group.setChecked(False)
        advanced_layout = QVBoxLayout()
        srt_group = QGroupBox(_("SRT"))
        srt_layout = QFormLayout()
        self.srt_keep_unknown_html_tags_check = QCheckBox(_("Keep unknown HTML tags (input)"))
        self.srt_keep_html_tags_check = QCheckBox(_("Keep all HTML tags (input)"))
        self.srt_keep_ssa_tags_check = QCheckBox(_("Keep SSA tags (output)"))
        srt_layout.addRow(self.srt_keep_unknown_html_tags_check)
        srt_layout.addRow(self.srt_keep_html_tags_check)
        srt_layout.addRow(self.srt_keep_ssa_tags_check)
        srt_group.setLayout(srt_layout)
        microdvd_group = QGroupBox(_("MicroDVD"))
        microdvd_layout = QFormLayout()
        self.sub_no_write_fps_declaration_check = QCheckBox(_("Omit FPS declaration (output)"))
        microdvd_layout.addRow(self.sub_no_write_fps_declaration_check)
        microdvd_group.setLayout(microdvd_layout)
        advanced_layout.addWidget(srt_group)
        advanced_layout.addWidget(microdvd_group)
        advanced_group.setLayout(advanced_layout)

        action_layout = QHBoxLayout()
        self.convert_button = QPushButton(_("Convert"))
        self.convert_button.setEnabled(False)
        self.convert_button.clicked.connect(self.run_conversion)
        self.status_label = QLabel(_("Ready"))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        action_layout.addWidget(self.convert_button)
        action_layout.addWidget(self.status_label)
        
        main_layout.addWidget(file_group)
        main_layout.addWidget(options_group)
        main_layout.addWidget(advanced_group)
        main_layout.addLayout(action_layout)
        main_layout.addStretch()

    def add_files(self):
        file_filter = _("Subtitle Files (*.ass *.json *.sami *.smi *.srt *.ssa *.sub *.ttml *.txt *.vtt);;All Files (*)")
        files, selected_filter = QFileDialog.getOpenFileNames(self, _("Select Subtitle Files"), filter=file_filter)
        if files:
            detected_encoding = detect_encoding(files[0])
            self.input_encoding_combo.setCurrentText(detected_encoding)
            
            for file in files:
                if file not in self.file_paths:
                    self.file_paths.append(file)
                    self.file_list_widget.addItem(QListWidgetItem(os.path.basename(file)))
            
            self.convert_button.setEnabled(True)

    def clear_files(self):
        self.file_paths.clear()
        self.file_list_widget.clear()
        self.status_label.setText(_("Ready"))
        self.convert_button.setEnabled(False)

    def run_conversion(self):
        if not self.file_paths:
            self.status_label.setText(_("Error: No files selected."))
            return

        output_dir = QFileDialog.getExistingDirectory(self, _("Select Output Directory"))
        if not output_dir:
            return

        options = {
            "output_format": self.output_format_combo.currentText(),
            "input_encoding": self.input_encoding_combo.currentText(),
            "output_encoding": self.output_encoding_combo.currentText(),
            "clean_subtitles": self.clean_checkbox.isChecked(),
            "srt_keep_unknown_html_tags": self.srt_keep_unknown_html_tags_check.isChecked(),
            "srt_keep_html_tags": self.srt_keep_html_tags_check.isChecked(),
            "srt_keep_ssa_tags": self.srt_keep_ssa_tags_check.isChecked(),
            "sub_no_write_fps_declaration": self.sub_no_write_fps_declaration_check.isChecked()
        }
        
        self.status_label.setText(_("Processing..."))
        self.convert_button.setEnabled(False)
        
        self.thread = SubtitleConverterThread(self.file_paths, output_dir, options)
        self.thread.progress.connect(self.on_progress)
        self.thread.finished.connect(self.on_finished)
        self.thread.error.connect(self.on_error)
        self.thread.start()
        
        signal_manager.statusbar_message.emit(
            _("Converting {count} subtitle file(s)").format(count=len(self.file_paths))
        )

    def on_progress(self, message):
        self.status_label.setText(message)

    def on_finished(self):
        QMessageBox.information(self, _("Success"), _("Subtitle conversion completed successfully."))
        self.convert_button.setEnabled(True)
        signal_manager.statusbar_message.emit(_("Subtitle conversion completed"))

    def on_error(self, error_message):
        self.status_label.setText(_("Error occurred"))
        QMessageBox.warning(self, _("Conversion Error"), error_message)
        self.convert_button.setEnabled(True)
        signal_manager.statusbar_message.emit(_("Subtitle conversion failed"))

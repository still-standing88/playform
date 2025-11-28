from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QFormLayout, QLabel, QComboBox,
                             QCheckBox, QPushButton, QListWidget, QFileDialog,
                             QListWidgetItem)
from PySide6.QtCore import Qt
import subtitle_handler
import os

COMMON_ENCODINGS = ['utf-8', 'utf-16', 'windows-1252', 'latin-1', 'iso-8859-1', 'gbk', 'shift_jis']

class ConverterWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_paths = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        file_group = QGroupBox("Files for Conversion (Batch)")
        file_layout = QVBoxLayout()
        self.file_list_widget = QListWidget()
        file_buttons_layout = QHBoxLayout()
        add_files_button = QPushButton("Add Files")
        add_files_button.clicked.connect(self.add_files)
        clear_files_button = QPushButton("Clear")
        clear_files_button.clicked.connect(self.clear_files)
        file_buttons_layout.addWidget(add_files_button)
        file_buttons_layout.addWidget(clear_files_button)
        file_layout.addWidget(self.file_list_widget)
        file_layout.addLayout(file_buttons_layout)
        file_group.setLayout(file_layout)

        options_group = QGroupBox("Conversion Options")
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
        self.clean_checkbox = QCheckBox("Remove miscellaneous events")
        options_layout.addRow("Output Format:", self.output_format_combo)
        options_layout.addRow("Input Encoding:", self.input_encoding_combo)
        options_layout.addRow("Output Encoding:", self.output_encoding_combo)
        options_layout.addRow(self.clean_checkbox)
        options_group.setLayout(options_layout)

        advanced_group = QGroupBox("Advanced Format Options")
        advanced_group.setCheckable(True)
        advanced_group.setChecked(False)
        advanced_layout = QVBoxLayout()
        srt_group = QGroupBox("SRT")
        srt_layout = QFormLayout()
        self.srt_keep_unknown_html_tags_check = QCheckBox("Keep unknown HTML tags (input)")
        self.srt_keep_html_tags_check = QCheckBox("Keep all HTML tags (input)")
        self.srt_keep_ssa_tags_check = QCheckBox("Keep SSA tags (output)")
        srt_layout.addRow(self.srt_keep_unknown_html_tags_check)
        srt_layout.addRow(self.srt_keep_html_tags_check)
        srt_layout.addRow(self.srt_keep_ssa_tags_check)
        srt_group.setLayout(srt_layout)
        microdvd_group = QGroupBox("MicroDVD")
        microdvd_layout = QFormLayout()
        self.sub_no_write_fps_declaration_check = QCheckBox("Omit FPS declaration (output)")
        microdvd_layout.addRow(self.sub_no_write_fps_declaration_check)
        microdvd_group.setLayout(microdvd_layout)
        advanced_layout.addWidget(srt_group)
        advanced_layout.addWidget(microdvd_group)
        advanced_group.setLayout(advanced_layout)

        action_layout = QHBoxLayout()
        self.convert_button = QPushButton("Convert")
        self.convert_button.setEnabled(False)
        self.convert_button.clicked.connect(self.run_conversion)
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        action_layout.addWidget(self.convert_button)
        action_layout.addWidget(self.status_label)
        
        main_layout.addWidget(file_group)
        main_layout.addWidget(options_group)
        main_layout.addWidget(advanced_group)
        main_layout.addLayout(action_layout)
        main_layout.addStretch()

    def add_files(self):
        file_filter = "Subtitle Files (*.ass *.json *.sami *.smi *.srt *.ssa *.sub *.ttml *.txt *.vtt);;All Files (*)"
        files, _ = QFileDialog.getOpenFileNames(self, "Select Subtitle Files", filter=file_filter)
        if files:
            detected_encoding = subtitle_handler.detect_encoding(files[0])
            self.input_encoding_combo.setCurrentText(detected_encoding)
            
            for file in files:
                if file not in self.file_paths:
                    self.file_paths.append(file)
                    self.file_list_widget.addItem(QListWidgetItem(os.path.basename(file)))
            
            self.convert_button.setEnabled(True)

    def clear_files(self):
        self.file_paths.clear()
        self.file_list_widget.clear()
        self.status_label.setText("Ready")
        self.convert_button.setEnabled(False)

    def run_conversion(self):
        if not self.file_paths:
            self.status_label.setText("Error: No files selected.")
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
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
        
        self.status_label.setText("Processing...")
        result = subtitle_handler.convert_and_clean_subtitles(self.file_paths, output_dir, options)
        self.status_label.setText(result)
import os
from gettext import gettext as _
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, QFileDialog,
    QTabWidget, QRadioButton, QDoubleSpinBox, QStackedWidget,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView,
    QSplitter, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from .handler import detect_encoding, read_subtitle_file, process_subtitles
from utilities import signal_manager

COMMON_ENCODINGS = ['utf-8', 'utf-16', 'windows-1252', 'latin-1', 'iso-8859-1', 'gbk', 'shift_jis']

class SubtitleEditorThread(QThread):
    progress = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, file_path, output_dir, options):
        super().__init__()
        self.file_path = file_path
        self.output_dir = output_dir
        self.options = options
        self._is_running = True

    def run(self):
        if not self._is_running:
            return
        
        self.progress.emit(_("Processing subtitle file..."))
        result = process_subtitles([self.file_path], self.output_dir, self.options)
        
        if result.startswith("Success"):
            self.progress.emit(result)
            self.finished.emit()
        else:
            self.error.emit(result)

    def stop(self):
        self._is_running = False

class SubtitleEditorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.file_path = None
        self.original_events = []
        self.thread: SubtitleEditorThread | None = None
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        file_group = QGroupBox(_("Current File"))
        file_layout = QVBoxLayout()
        
        self.current_file_label = QLabel(_("No file loaded."))
        font = self.current_file_label.font()
        font.setBold(True)
        self.current_file_label.setFont(font)
        self.current_file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        file_buttons_layout = QHBoxLayout()
        add_file_button = QPushButton(_("Load File"))
        add_file_button.clicked.connect(self.add_file)
        clear_file_button = QPushButton(_("Clear"))
        clear_file_button.clicked.connect(self.clear_file)
        file_buttons_layout.addWidget(add_file_button)
        file_buttons_layout.addWidget(clear_file_button)
        
        file_layout.addWidget(self.current_file_label)
        file_layout.addLayout(file_buttons_layout)
        file_group.setLayout(file_layout)
        
        self.input_encoding_combo = QComboBox()
        self.input_encoding_combo.setEditable(True)
        self.input_encoding_combo.addItems(COMMON_ENCODINGS)
        self.input_encoding_combo.setCurrentText("utf-8")
        self.input_encoding_combo.currentTextChanged.connect(
            lambda: self.load_file_for_preview(None, None)
        )
        encoding_layout = QFormLayout()
        encoding_layout.addRow(_("Input File Encoding:"), self.input_encoding_combo)

        tabs = QTabWidget()
        timing_tab = self.create_timing_tab()
        text_tab = self.create_text_tab()
        tabs.addTab(timing_tab, _("Timing Editor"))
        tabs.addTab(text_tab, _("Text Editor"))

        left_layout.addWidget(file_group)
        left_layout.addLayout(encoding_layout)
        left_layout.addWidget(tabs)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        preview_group = QGroupBox(_("File Content Preview (Live)"))
        preview_layout = QVBoxLayout()
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels([_("No."), _("Start"), _("End"), _("Text")])
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setTabKeyNavigation(False)
        preview_layout.addWidget(self.preview_table)
        preview_group.setLayout(preview_layout)
        right_layout.addWidget(preview_group)

        action_layout = QHBoxLayout()
        self.apply_button = QPushButton(_("Apply Changes"))
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.run_processing)
        self.status_label = QLabel(_("Ready"))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        action_layout.addWidget(self.apply_button)
        action_layout.addWidget(self.status_label)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([350, 400])

        main_v_layout = QVBoxLayout()
        main_v_layout.addWidget(splitter)
        main_v_layout.addLayout(action_layout)
        main_layout.addLayout(main_v_layout)
    
    def create_timing_tab(self):
        tab = QWidget()
        layout = QFormLayout(tab)
        self.shift_edit = QLineEdit()
        self.shift_edit.setPlaceholderText(_("e.g., 1.5s or -1m10s"))
        layout.addRow(_("Shift Time:"), self.shift_edit)
        self.transform_fps_check = QCheckBox(_("Enable Framerate Transformation"))
        self.from_fps_spin = QDoubleSpinBox()
        self.to_fps_spin = QDoubleSpinBox()
        self.from_fps_spin.setRange(0.01, 1000.0)
        self.to_fps_spin.setRange(0.01, 1000.0)
        self.from_fps_spin.setValue(23.976)
        self.to_fps_spin.setValue(25.000)
        layout.addRow(self.transform_fps_check)
        layout.addRow(_("From FPS:"), self.from_fps_spin)
        layout.addRow(_("To FPS:"), self.to_fps_spin)
        return tab

    def create_text_tab(self):
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        op_group = QGroupBox(_("Text Operation"))
        op_layout = QHBoxLayout()
        self.op_none_radio = QRadioButton(_("None"))
        self.op_find_replace_radio = QRadioButton(_("Find and Replace"))
        self.op_prefix_suffix_radio = QRadioButton(_("Add Prefix/Suffix"))
        self.op_change_case_radio = QRadioButton(_("Change Case"))
        op_layout.addWidget(self.op_none_radio)
        op_layout.addWidget(self.op_find_replace_radio)
        op_layout.addWidget(self.op_prefix_suffix_radio)
        op_layout.addWidget(self.op_change_case_radio)
        op_group.setLayout(op_layout)
        self.op_none_radio.setChecked(True)
        self.op_stack = QStackedWidget()
        self.op_stack.addWidget(QWidget())
        fr_widget = QWidget()
        fr_layout = QFormLayout(fr_widget)
        self.find_edit = QLineEdit()
        self.replace_edit = QLineEdit()
        self.case_sensitive_check = QCheckBox(_("Case Sensitive"))
        fr_layout.addRow(_("Find:"), self.find_edit)
        fr_layout.addRow(_("Replace With:"), self.replace_edit)
        fr_layout.addRow(self.case_sensitive_check)
        self.op_stack.addWidget(fr_widget)
        ps_widget = QWidget()
        ps_layout = QFormLayout(ps_widget)
        self.prefix_edit = QLineEdit()
        self.suffix_edit = QLineEdit()
        ps_layout.addRow(_("Prefix:"), self.prefix_edit)
        ps_layout.addRow(_("Suffix:"), self.suffix_edit)
        self.op_stack.addWidget(ps_widget)
        cc_widget = QWidget()
        cc_layout = QFormLayout(cc_widget)
        self.case_style_combo = QComboBox()
        self.case_style_combo.addItems(["UPPERCASE", "lowercase", "Title Case"])
        cc_layout.addRow(_("Style:"), self.case_style_combo)
        self.op_stack.addWidget(cc_widget)
        
        for radio in [self.op_none_radio, self.op_find_replace_radio, self.op_prefix_suffix_radio, self.op_change_case_radio]:
            radio.toggled.connect(self.update_preview_with_text_edits)
        for editor in [self.find_edit, self.replace_edit, self.prefix_edit, self.suffix_edit]:
            editor.textChanged.connect(self.update_preview_with_text_edits)
        self.case_sensitive_check.stateChanged.connect(self.update_preview_with_text_edits)
        self.case_style_combo.currentTextChanged.connect(self.update_preview_with_text_edits)

        self.op_none_radio.toggled.connect(lambda checked: self.op_stack.setCurrentIndex(0) if checked else None)
        self.op_find_replace_radio.toggled.connect(lambda checked: self.op_stack.setCurrentIndex(1) if checked else None)
        self.op_prefix_suffix_radio.toggled.connect(lambda checked: self.op_stack.setCurrentIndex(2) if checked else None)
        self.op_change_case_radio.toggled.connect(lambda checked: self.op_stack.setCurrentIndex(3) if checked else None)
        
        main_layout.addWidget(op_group)
        main_layout.addWidget(self.op_stack)
        return tab

    def add_file(self):
        file_filter = _("Subtitle Files (*.ass *.json *.sami *.smi *.srt *.ssa *.sub *.ttml *.txt *.vtt);;All Files (*)")
        file, selected_filter = QFileDialog.getOpenFileName(self, _("Select Subtitle File"), filter=file_filter)
        if file:
            self.file_path = file
            self.current_file_label.setText(os.path.basename(file))
            detected_encoding = detect_encoding(file)
            self.input_encoding_combo.setCurrentText(detected_encoding)
            self.load_file_for_preview(None, None)
            self.apply_button.setEnabled(True)
            self.status_label.setText(_("File loaded successfully"))

    def clear_file(self):
        self.file_path = None
        self.current_file_label.setText(_("No file loaded."))
        self.original_events = []
        self.preview_table.setRowCount(0)
        self.status_label.setText(_("Ready"))
        self.apply_button.setEnabled(False)
        self.reset_editor_fields()

    def reset_editor_fields(self):
        self.shift_edit.clear()
        self.transform_fps_check.setChecked(False)
        self.from_fps_spin.setValue(23.976)
        self.to_fps_spin.setValue(25.000)
        self.op_none_radio.setChecked(True)
        self.find_edit.clear()
        self.replace_edit.clear()
        self.prefix_edit.clear()
        self.suffix_edit.clear()
        self.case_sensitive_check.setChecked(False)
        self.case_style_combo.setCurrentIndex(0)

    def load_file_for_preview(self, current_item, previous_item):
        if not self.file_path:
            return
        
        encoding = self.input_encoding_combo.currentText()
        events = read_subtitle_file(self.file_path, encoding)
        
        if isinstance(events, str):
            self.status_label.setText(events)
            return
        
        self.original_events = events
        self.update_preview_table(events)
        self.status_label.setText(_("Loaded {count} subtitle events").format(count=len(events)))

    def update_preview_with_text_edits(self):
        if not self.original_events:
            return
        
        import re
        modified_events = []
        for event in self.original_events:
            modified_event = event.copy()
            original_text = event["text"]
            modified_text = original_text
            
            if self.op_find_replace_radio.isChecked():
                find_text = self.find_edit.text()
                replace_text = self.replace_edit.text()
                if find_text:
                    if self.case_sensitive_check.isChecked():
                        modified_text = original_text.replace(find_text, replace_text)
                    else:
                        modified_text = re.sub(find_text, replace_text, original_text, flags=re.IGNORECASE)
            elif self.op_prefix_suffix_radio.isChecked():
                prefix = self.prefix_edit.text()
                suffix = self.suffix_edit.text()
                modified_text = f"{prefix}{original_text}{suffix}"
            elif self.op_change_case_radio.isChecked():
                style = self.case_style_combo.currentText()
                if style == "UPPERCASE":
                    modified_text = original_text.upper()
                elif style == "lowercase":
                    modified_text = original_text.lower()
                elif style == "Title Case":
                    modified_text = original_text.title()
            
            modified_event["text"] = modified_text
            modified_events.append(modified_event)
        
        self.update_preview_table(modified_events)

    def update_preview_table(self, events):
        self.preview_table.setRowCount(len(events))
        for row, event in enumerate(events):
            self.preview_table.setItem(row, 0, QTableWidgetItem(event["index"]))
            self.preview_table.setItem(row, 1, QTableWidgetItem(event["start"]))
            self.preview_table.setItem(row, 2, QTableWidgetItem(event["end"]))
            self.preview_table.setItem(row, 3, QTableWidgetItem(event["text"]))

    def run_processing(self):
        if not self.file_path:
            QMessageBox.warning(self, _("No File"), _("Please load a subtitle file first."))
            return

        output_dir = QFileDialog.getExistingDirectory(self, _("Select Output Directory"))
        if not output_dir:
            return

        text_op = "None"
        if self.op_find_replace_radio.isChecked():
            text_op = "Find and Replace"
        elif self.op_prefix_suffix_radio.isChecked():
            text_op = "Add Prefix/Suffix"
        elif self.op_change_case_radio.isChecked():
            text_op = "Change Case"

        options = {
            "input_encoding": self.input_encoding_combo.currentText(),
            "shift_time": self.shift_edit.text(),
            "transform_framerate": self.transform_fps_check.isChecked(),
            "from_fps": self.from_fps_spin.value(),
            "to_fps": self.to_fps_spin.value(),
            "text_operation": text_op,
            "find_text": self.find_edit.text(),
            "replace_text": self.replace_edit.text(),
            "case_sensitive": self.case_sensitive_check.isChecked(),
            "prefix": self.prefix_edit.text(),
            "suffix": self.suffix_edit.text(),
            "case_style": self.case_style_combo.currentText()
        }

        self.status_label.setText(_("Processing..."))
        self.apply_button.setEnabled(False)
        
        self.thread = SubtitleEditorThread(self.file_path, output_dir, options)
        self.thread.progress.connect(self.on_progress)
        self.thread.finished.connect(self.on_finished)
        self.thread.error.connect(self.on_error)
        self.thread.start()
        
        signal_manager.statusbar_message.emit(_("Processing subtitle file"))

    def on_progress(self, message):
        self.status_label.setText(message)

    def on_finished(self):
        QMessageBox.information(self, _("Success"), _("Subtitle processing completed successfully."))
        self.apply_button.setEnabled(True)
        signal_manager.statusbar_message.emit(_("Subtitle processing completed"))

    def on_error(self, error_message):
        self.status_label.setText(_("Error occurred"))
        QMessageBox.warning(self, _("Processing Error"), error_message)
        self.apply_button.setEnabled(True)
        signal_manager.statusbar_message.emit(_("Subtitle processing failed"))

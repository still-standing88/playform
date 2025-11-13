from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                               QWidget, QLabel, QComboBox, QSpinBox, QPushButton,
                               QFormLayout, QDialogButtonBox, QTextEdit, QCheckBox,
                               QFileDialog, QMessageBox, QLineEdit)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QKeyEvent
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_config import prefs
from app_constance.misc import screenshot_formats, app_languages
from utilities.functions import is_valid_vlc_args, parse_vlc_args

class PreferencesDialog(QDialog):
    preferences_saved = Signal(dict)
    
    def __init__(self, parent=None, audio_devices=None, audio_device_callback=None):
        super().__init__(parent)
        self.audio_devices = audio_devices or [[]]
        self.audio_device_callback = audio_device_callback
        self.setWindowTitle("Preferences")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumSize(500, 400)
        self.setup_ui()
        self.load_preferences()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        self.setup_general_tab()
        self.setup_media_tab()
        self.setup_vlc_tab()
        self.setup_ytdlp_tab()
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def setup_general_tab(self):
        general_widget = QWidget()
        layout = QFormLayout(general_widget)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(app_languages)
        layout.addRow("Language:", self.language_combo)
        
        self.screenshot_format_combo = QComboBox()
        self.screenshot_format_combo.addItems(screenshot_formats)
        layout.addRow("Screenshot Format:", self.screenshot_format_combo)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["system", "light", "dark"])
        layout.addRow("Theme:", self.theme_combo)
        
        self.auto_update_check = QCheckBox("Auto check for updates")
        layout.addRow("Auto Updates:", self.auto_update_check)
        
        self.tab_widget.addTab(general_widget, "General")
        
    def setup_media_tab(self):
        media_widget = QWidget()
        layout = QFormLayout(media_widget)
        
        self.volume_offset_spin = QSpinBox()
        self.volume_offset_spin.setRange(1, 20)
        layout.addRow("Volume Offset:", self.volume_offset_spin)
        
        self.seek_offset_spin = QSpinBox()
        self.seek_offset_spin.setRange(1, 60)
        layout.addRow("Seek Offset:", self.seek_offset_spin)
        
        self.audio_device_combo = QComboBox()
        self.audio_device_combo.addItems(self.audio_devices) # type: ignore
        layout.addRow("Audio Device:", self.audio_device_combo)
        
        self.tab_widget.addTab(media_widget, "Media")
        
    def setup_vlc_tab(self):
        vlc_widget = QWidget()
        layout = QFormLayout(vlc_widget)
        
        self.vlc_logging_check = QCheckBox("Enable VLC Logging")
        self.vlc_logging_check.toggled.connect(self.toggle_vlc_logging_options)
        layout.addRow("VLC Logging:", self.vlc_logging_check)
        
        self.debug_level_spin = QSpinBox()
        self.debug_level_spin.setRange(0, 2)
        self.debug_level_row = layout.rowCount()
        layout.addRow("Debug Level:", self.debug_level_spin)
        
        self.vlc_args_edit = QTextEdit()
        self.vlc_args_edit.setMaximumHeight(100)
        self.vlc_args_edit.setTabChangesFocus(True)
        
        original_focus_out = self.vlc_args_edit.focusOutEvent
        def custom_focus_out(event):
            self.validate_vlc_args()
            original_focus_out(event)
        self.vlc_args_edit.focusOutEvent = custom_focus_out # type: ignore
        
        layout.addRow("VLC Arguments:", self.vlc_args_edit)
        
        self.tab_widget.addTab(vlc_widget, "VLC")
        
    def setup_ytdlp_tab(self):
        ytdlp_widget = QWidget()
        self.ytdlp_layout = QFormLayout(ytdlp_widget)
        
        cookies_widget = QWidget()
        cookies_layout = QHBoxLayout(cookies_widget)
        cookies_layout.setContentsMargins(0, 0, 0, 0)
        self.youtube_cookies_edit = QLineEdit()
        self.youtube_cookies_edit.setReadOnly(True)
        self.cookies_browse_btn = QPushButton("Browse")
        self.cookies_browse_btn.clicked.connect(self.browse_cookies_file)
        cookies_layout.addWidget(self.youtube_cookies_edit)
        cookies_layout.addWidget(self.cookies_browse_btn)
        self.ytdlp_layout.addRow("Cookies File:", cookies_widget)
        
        ytdlp_widget_path = QWidget()
        ytdlp_layout_path = QHBoxLayout(ytdlp_widget_path)
        ytdlp_layout_path.setContentsMargins(0, 0, 0, 0)
        self.ytdlp_path_edit = QLineEdit()
        self.ytdlp_path_edit.setReadOnly(True)
        self.ytdlp_browse_btn = QPushButton("Browse")
        self.ytdlp_browse_btn.clicked.connect(self.browse_ytdlp_path)
        ytdlp_layout_path.addWidget(self.ytdlp_path_edit)
        ytdlp_layout_path.addWidget(self.ytdlp_browse_btn)
        self.ytdlp_layout.addRow("yt-dlp Path:", ytdlp_widget_path)
        
        self.ytdlp_logging_check = QCheckBox("Enable yt-dlp Logging")
        self.ytdlp_logging_check.toggled.connect(self.toggle_ytdlp_logging_options)
        self.ytdlp_layout.addRow("yt-dlp Logging:", self.ytdlp_logging_check)
        
        self.ytdlp_verbose_check = QCheckBox("Enable Verbose Output")
        self.ytdlp_verbose_row = self.ytdlp_layout.rowCount()
        self.ytdlp_layout.addRow("Verbose Output:", self.ytdlp_verbose_check)
        
        self.tab_widget.addTab(ytdlp_widget, "yt-dlp")
        
    @Slot(bool)
    def toggle_vlc_logging_options(self, checked):
        debug_label = self.vlc_args_edit.parent().layout().itemAt(self.debug_level_row, QFormLayout.ItemRole.LabelRole).widget() # type: ignore
        debug_field = self.vlc_args_edit.parent().layout().itemAt(self.debug_level_row, QFormLayout.ItemRole.FieldRole).widget() # type: ignore
        
        debug_label.setVisible(checked)
        debug_field.setVisible(checked)
        
    @Slot(bool)
    def toggle_ytdlp_logging_options(self, checked):
        verbose_label = self.ytdlp_layout.itemAt(self.ytdlp_verbose_row, QFormLayout.ItemRole.LabelRole).widget()
        verbose_field = self.ytdlp_layout.itemAt(self.ytdlp_verbose_row, QFormLayout.ItemRole.FieldRole).widget()
        
        verbose_label.setVisible(checked)
        verbose_field.setVisible(checked)
        
    def validate_vlc_args(self):
        text = self.vlc_args_edit.toPlainText().strip()
        if text and not is_valid_vlc_args(text):
            QMessageBox.warning(self, "Invalid VLC Arguments", 
                              "The VLC arguments are not valid. Please check the syntax.")
            self.vlc_args_edit.setFocus()
            return False
        return True
        
    @Slot()
    def browse_cookies_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Cookies File", 
                                                 "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            self.youtube_cookies_edit.setText(file_path)
            
    @Slot()
    def browse_ytdlp_path(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select yt-dlp Directory")
        if dir_path:
            self.ytdlp_path_edit.setText(dir_path)
        
    def load_preferences(self):
        current_prefs = prefs.prefs
        
        if current_prefs["language"].upper() in app_languages:
            self.language_combo.setCurrentText(current_prefs["language"].upper())
        
        if current_prefs["image_format"] in screenshot_formats:
            self.screenshot_format_combo.setCurrentText(current_prefs["image_format"])
            
        self.volume_offset_spin.setValue(current_prefs["offset"]["volume"])
        self.seek_offset_spin.setValue(current_prefs["offset"]["seek"])
        
        if len(self.audio_devices) >0 and current_prefs["device"]< len(self.audio_devices):
            self.audio_device_combo.setCurrentIndex(current_prefs["device"])
            
        self.theme_combo.setCurrentText(current_prefs["color_theme"])
        self.auto_update_check.setChecked(current_prefs["auto_check_for_updates"])
        self.vlc_logging_check.setChecked(current_prefs["vlc_logging"])
        self.debug_level_spin.setValue(current_prefs["debug_level"])
        self.vlc_args_edit.setPlainText(current_prefs["vlc_args"])
        self.youtube_cookies_edit.setText(current_prefs["youtube_cookies"])
        self.ytdlp_path_edit.setText(current_prefs["yt-dlp_path"])
        self.ytdlp_logging_check.setChecked(current_prefs["yt-dlp_logging"])
        self.ytdlp_verbose_check.setChecked(current_prefs["yt-dlp_verbose_output"])
        
        self.toggle_vlc_logging_options(current_prefs["vlc_logging"])
        self.toggle_ytdlp_logging_options(current_prefs["yt-dlp_logging"])
            
    def save_preferences(self):
        prefs.prefs["language"] = self.language_combo.currentText().lower()
        prefs.prefs["image_format"] = self.screenshot_format_combo.currentText()
        prefs.prefs["offset"]["volume"] = self.volume_offset_spin.value()
        prefs.prefs["offset"]["seek"] = self.seek_offset_spin.value()
        prefs.prefs["device"] = self.audio_device_combo.currentIndex()
        prefs.prefs["color_theme"] = self.theme_combo.currentText()
        prefs.prefs["auto_check_for_updates"] = self.auto_update_check.isChecked()
        prefs.prefs["vlc_logging"] = self.vlc_logging_check.isChecked()
        prefs.prefs["debug_level"] = self.debug_level_spin.value()
        prefs.prefs["vlc_args"] = self.vlc_args_edit.toPlainText().strip()
        prefs.prefs["youtube_cookies"] = self.youtube_cookies_edit.text()
        prefs.prefs["yt-dlp_path"] = self.ytdlp_path_edit.text()
        prefs.prefs["yt-dlp_logging"] = self.ytdlp_logging_check.isChecked()
        prefs.prefs["yt-dlp_verbose_output"] = self.ytdlp_verbose_check.isChecked()
        
        prefs.save()
        
        if self.audio_device_callback:
            self.audio_device_callback(prefs.prefs["device"])
        
        self.preferences_saved.emit(prefs.prefs.copy())
        
    def accept(self):
        if not self.validate_vlc_args():
            return
            
        self.save_preferences()
        super().accept()

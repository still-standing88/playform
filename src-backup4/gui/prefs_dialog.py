from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                               QWidget, QLabel, QComboBox, QSpinBox, QPushButton,
                               QFormLayout, QDialogButtonBox)
from PySide6.QtCore import Qt, Signal
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_config import prefs
from app_constance.misc import screenshot_formats, app_languages

class PreferencesDialog(QDialog):
    preferences_saved = Signal(dict)
    
    def __init__(self, parent=None, audio_devices=None, audio_device_callback=None):
        super().__init__(parent)
        self.audio_devices = audio_devices or ["auto"]
        self.audio_device_callback = audio_device_callback
        self.setWindowTitle("Preferences")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumSize(400, 300)
        self.setup_ui()
        self.load_preferences()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        self.setup_general_tab()
        self.setup_media_tab()
        
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
        self.audio_device_combo.addItems(self.audio_devices)
        layout.addRow("Audio Device:", self.audio_device_combo)
        
        self.tab_widget.addTab(media_widget, "Media")
        
    def load_preferences(self):
        current_prefs = prefs.prefs
        
        if current_prefs["language"].upper() in app_languages:
            self.language_combo.setCurrentText(current_prefs["language"].upper())
        
        if current_prefs["image_format"] in screenshot_formats:
            self.screenshot_format_combo.setCurrentText(current_prefs["image_format"])
            
        self.volume_offset_spin.setValue(current_prefs["offset"]["volume"])
        self.seek_offset_spin.setValue(current_prefs["offset"]["seek"])
        
        if current_prefs["device"] in self.audio_devices:
            self.audio_device_combo.setCurrentText(current_prefs["device"])
            
    def save_preferences(self):
        prefs.prefs["language"] = self.language_combo.currentText().lower()
        prefs.prefs["image_format"] = self.screenshot_format_combo.currentText()
        prefs.prefs["offset"]["volume"] = self.volume_offset_spin.value()
        prefs.prefs["offset"]["seek"] = self.seek_offset_spin.value()
        prefs.prefs["device"] = self.audio_device_combo.currentText()
        
        prefs.save()
        
        # Call audio device callback if provided
        if self.audio_device_callback:
            self.audio_device_callback(prefs.prefs["device"])
        
        self.preferences_saved.emit(prefs.prefs.copy())
        
    def accept(self):
        self.save_preferences()
        super().accept()

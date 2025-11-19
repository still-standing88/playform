from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, QDialogButtonBox)
from PySide6.QtCore import Qt, Signal
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_config import prefs
from .general_panel import GeneralPanel
from .media_panel import MediaPanel
from .accessibility_panel import AccessibilityPanel
from .advanced_panel import AdvancedPanel

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
        
        self.general_panel = GeneralPanel(self)
        self.tab_widget.addTab(self.general_panel, "General")
        
        self.media_panel = MediaPanel(self, self.audio_devices)
        self.tab_widget.addTab(self.media_panel, "Media")
        
        self.accessibility_panel = AccessibilityPanel(self)
        self.tab_widget.addTab(self.accessibility_panel, "Accessibility")
        
        self.advanced_panel = AdvancedPanel(self)
        self.tab_widget.addTab(self.advanced_panel, "Advanced")
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def load_preferences(self):
        current_prefs = prefs.prefs
        
        self.general_panel.load_settings(current_prefs)
        self.media_panel.load_settings(current_prefs)
        self.accessibility_panel.load_settings(current_prefs)
        self.advanced_panel.load_settings(current_prefs)
            
    def save_preferences(self):
        self.general_panel.save_settings(prefs.prefs)
        self.media_panel.save_settings(prefs.prefs)
        self.accessibility_panel.save_settings(prefs.prefs)
        self.advanced_panel.save_settings(prefs.prefs)
        
        prefs.save()
        
        if self.audio_device_callback:
            self.audio_device_callback(prefs.prefs["device"])
        
        self.preferences_saved.emit(prefs.prefs.copy())
        
    def accept(self):
        if not self.advanced_panel.validate_vlc_args():
            return
            
        self.save_preferences()
        super().accept()

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
        from PySide6.QtWidgets import QMessageBox
        from utilities.theme_manager import apply_theme
        old_theme = prefs.prefs.get("color_theme", "system")
        old_vlc_logging = prefs.prefs.get("vlc_logging", False)
        old_vlc_args = prefs.prefs.get("vlc_args", "")
        old_debug_level = prefs.prefs.get("debug_level", 2)
        
        self.general_panel.save_settings(prefs.prefs)
        self.media_panel.save_settings(prefs.prefs)
        self.accessibility_panel.save_settings(prefs.prefs)
        self.advanced_panel.save_settings(prefs.prefs)
        
        prefs.save()
        
        new_theme = prefs.prefs.get("color_theme", "system")
        new_vlc_logging = prefs.prefs.get("vlc_logging", False)
        new_vlc_args = prefs.prefs.get("vlc_args", "")
        new_debug_level = prefs.prefs.get("debug_level", 2)
        
        # Apply theme change immediately without restart
        if old_theme != new_theme:
            apply_theme(new_theme)
        
        needs_restart = (
            old_vlc_logging != new_vlc_logging or 
            old_vlc_args != new_vlc_args or
            old_debug_level != new_debug_level
        )
        
        if needs_restart:
            reply = QMessageBox.question(
                self,
                "Restart Required",
                "Some options you modified require an application restart to take effect.\n\nWould you like to restart now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                from utilities.functions import set_restart_flag
                set_restart_flag(True)
                from PySide6.QtWidgets import QApplication
                QApplication.quit()
        
        from player import reinit_ytdlp_settings
        from player.utilities import update_prefs_with_found_binaries
        update_prefs_with_found_binaries(prefs.prefs)
        reinit_ytdlp_settings()
        
        if self.audio_device_callback:
            self.audio_device_callback(prefs.prefs["device"])
        
        self.preferences_saved.emit(prefs.prefs.copy())
        
    def accept(self):
        if not self.advanced_panel.validate_vlc_args():
            return
            
        self.save_preferences()
        super().accept()

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, QDialogButtonBox)
from PySide6.QtCore import Qt, Signal, QTimer
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_config import prefs
from .general_panel import GeneralPanel
from .media_panel import MediaPanel
from .accessibility_panel import AccessibilityPanel
from .advanced_panel import AdvancedPanel
from .database_panel import DatabasePanel

class PreferencesDialog(QDialog):
    preferences_saved = Signal(dict)

    def __init__(self, parent=None, audio_devices=None, audio_device_callback=None):
        super().__init__(parent)
        # Stored explicitly - self.parent() isn't reliable once this dialog
        # (or its tabs) get reparented by a layout.
        self._main_window = parent
        self.audio_devices = audio_devices or [[]]
        self.audio_device_callback = audio_device_callback
        self.setWindowTitle(_("Preferences"))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumSize(500, 400)
        self.setup_ui()
        self.load_preferences()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        self.general_panel = GeneralPanel(self)
        self.tab_widget.addTab(self.general_panel, _("General"))

        self.media_panel = MediaPanel(self, self.audio_devices)
        self.tab_widget.addTab(self.media_panel, _("Media"))

        self.accessibility_panel = AccessibilityPanel(self)
        self.tab_widget.addTab(self.accessibility_panel, _("Accessibility"))

        self.advanced_panel = AdvancedPanel(self)
        self.tab_widget.addTab(self.advanced_panel, _("Advanced"))

        self.database_panel = DatabasePanel(self, main_window=self._main_window)
        self.tab_widget.addTab(self.database_panel, _("Database"))

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
        self.database_panel.load_settings(current_prefs)
            
    def save_preferences(self) -> bool:
        from PySide6.QtWidgets import QMessageBox
        from utilities.theme_manager import apply_theme
        from utilities.functions import set_restart_flag
        restart_requested = False
        old_theme = prefs.prefs.get("color_theme", "system")
        old_mpv_logging = prefs.prefs.get("mpv_logging", False)
        old_mpv_extra_options = prefs.prefs.get("mpv_extra_options", "")
        old_debug_level = prefs.prefs.get("debug_level", 2)
        old_language = prefs.prefs.get("language", "en")
        
        language_changed = self.general_panel.save_settings(prefs.prefs)
        self.media_panel.save_settings(prefs.prefs)
        self.accessibility_panel.save_settings(prefs.prefs)
        self.advanced_panel.save_settings(prefs.prefs)
        self.database_panel.save_settings(prefs.prefs)

        prefs.save()
        
        new_theme = prefs.prefs.get("color_theme", "system")
        new_mpv_logging = prefs.prefs.get("mpv_logging", False)
        new_mpv_extra_options = prefs.prefs.get("mpv_extra_options", "")
        new_debug_level = prefs.prefs.get("debug_level", 2)
        new_language = prefs.prefs.get("language", "en")

        # Apply theme change immediately without restart
        if old_theme != new_theme:
            apply_theme(new_theme)

        needs_restart = (
            prefs.prefs.get("should_restart", False) or
            old_language != new_language or
            old_mpv_logging != new_mpv_logging or
            old_mpv_extra_options != new_mpv_extra_options or
            old_debug_level != new_debug_level
        )
        prefs.prefs["should_restart"] = prefs.prefs.get("should_restart", False) or language_changed or (old_language != new_language)
        if prefs.prefs["should_restart"]:
            prefs.save()
        
        if needs_restart:
            reply = QMessageBox.question(
                self,
                _("Restart Required"),
                _(
                    "Some options you modified require an application restart to take effect.\n\n"
                    "Would you like to restart now?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                set_restart_flag(True)
                restart_requested = True
        
        from player import reinit_ytdlp_settings
        from player.util.utilities import update_prefs_with_found_binaries
        update_prefs_with_found_binaries(prefs.prefs)
        reinit_ytdlp_settings()
        
        if self.audio_device_callback:
            self.audio_device_callback(prefs.prefs.get("device_name", ""))
        
        self.preferences_saved.emit(prefs.prefs.copy())
        return restart_requested

    def _request_application_restart(self):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.closeAllWindows()
        
    def accept(self):
        if not self.advanced_panel.validate_mpv_options():
            return
            
        restart_requested = self.save_preferences()
        super().accept()
        if restart_requested:
            QTimer.singleShot(0, self._request_application_restart)

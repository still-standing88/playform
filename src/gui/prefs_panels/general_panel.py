from PySide6.QtWidgets import QWidget, QFormLayout, QComboBox, QCheckBox
from app_constance.misc import screenshot_formats, app_languages

class GeneralPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(app_languages)
        layout.addRow(_("Language:"), self.language_combo)
        
        self.screenshot_format_combo = QComboBox()
        self.screenshot_format_combo.addItems(screenshot_formats)
        layout.addRow(_("Screenshot Format:"), self.screenshot_format_combo)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["system", "light", "dark"])
        layout.addRow(_("Theme:"), self.theme_combo)
        
        self.auto_update_check = QCheckBox(_("Auto check for updates"))
        layout.addRow(_("Auto Updates:"), self.auto_update_check)
        
        self.save_urls_check = QCheckBox(_("Save URLs"))
        layout.addRow(_("Save URLs:"), self.save_urls_check)
        
    def load_settings(self, prefs):
        if prefs["language"].upper() in app_languages:
            self.language_combo.setCurrentText(prefs["language"].upper())
        
        if prefs["image_format"] in screenshot_formats:
            self.screenshot_format_combo.setCurrentText(prefs["image_format"])
            
        self.theme_combo.setCurrentText(prefs["color_theme"])
        self.auto_update_check.setChecked(prefs["auto_check_for_updates"])
        self.save_urls_check.setChecked(prefs["save_urls"])
        
    def save_settings(self, prefs):
        prefs["language"] = self.language_combo.currentText().lower()
        prefs["image_format"] = self.screenshot_format_combo.currentText()
        prefs["color_theme"] = self.theme_combo.currentText()
        prefs["auto_check_for_updates"] = self.auto_update_check.isChecked()
        prefs["save_urls"] = self.save_urls_check.isChecked()

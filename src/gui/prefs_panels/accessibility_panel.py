from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QCheckBox, 
                               QPushButton, QGroupBox, QLabel)
from PySide6.QtCore import Qt
import sys
from .voice_settings_dialog import VoiceSettingsDialog
from utilities.speech import speech_manager

class AccessibilityPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        speech_group = QGroupBox(_("Speech Settings"))
        speech_layout = QFormLayout(speech_group)
        
        self.enable_speech_check = QCheckBox(_("Enable speech accessibility feedback"))
        self.enable_speech_check.toggled.connect(self.on_speech_toggled)
        speech_layout.addRow(self.enable_speech_check)
        
        # if sys.platform == "win32":
        #     self.prefer_sapi_check = QCheckBox("Use SAPI instead of screen reader")
        #     self.prefer_sapi_check.setToolTip("Use Windows SAPI for speech output instead of screen reader")
        #     self.prefer_sapi_check.toggled.connect(self.on_prefer_sapi_toggled)
        #     speech_layout.addRow(self.prefer_sapi_check)
        #     
        #     self.voice_settings_btn = QPushButton("Voice Settings")
        #     self.voice_settings_btn.clicked.connect(self.open_voice_settings)
        #     speech_layout.addRow("Configure Voice:", self.voice_settings_btn)
        # else:
        #     self.prefer_sapi_check = None
        #     self.voice_settings_btn = QPushButton("Voice Settings")
        #     self.voice_settings_btn.clicked.connect(self.open_voice_settings)
        #     speech_layout.addRow("Configure Voice:", self.voice_settings_btn)
        
        self.prefer_sapi_check = None
        if sys.platform != "win32":
            self.voice_settings_btn = QPushButton(_("Voice Settings"))
            self.voice_settings_btn.clicked.connect(self.open_voice_settings)
            speech_layout.addRow("Configure Voice:", self.voice_settings_btn)
        else:
            self.voice_settings_btn = None
            
        self.interrupt_check = QCheckBox(_("Interrupt previous speech"))
        speech_layout.addRow("Speech Interrupt:", self.interrupt_check)
        
        layout.addWidget(speech_group)
        layout.addStretch()
        
    def on_speech_toggled(self, checked):
        # if self.prefer_sapi_check:
        #     self.prefer_sapi_check.setEnabled(checked)
        if self.voice_settings_btn:
            self.voice_settings_btn.setEnabled(checked)
        self.interrupt_check.setEnabled(checked)
        
    # def on_prefer_sapi_toggled(self, checked):
    #     if sys.platform == "win32":
    #         if self.voice_settings_btn:
    #             self.voice_settings_btn.setVisible(checked)
    #         try:
    #             from app_config import prefs
    #             prefs.prefs["tts_prefer_sapi"] = checked
    #             speech_manager.prefer_sapi(checked)
    #             speech_manager.detect_driver()
    #         except:
    #             pass
                
    def open_voice_settings(self):
        dialog = VoiceSettingsDialog(self)
        if dialog.exec() == VoiceSettingsDialog.DialogCode.Accepted:
            settings = dialog.get_settings()
            from app_config import prefs
            prefs.prefs["tts_voice"] = settings["voice"]
            prefs.prefs["tts_volume"] = settings["volume"]
            prefs.prefs["tts_rate"] = settings["rate"]
            
            try:
                voice_index = speech_manager.find_voice_by_name(settings["voice"])
                if voice_index >= 0:
                    speech_manager.set_voice(voice_index)
                speech_manager.set_volume(settings["volume"])
                speech_manager.set_rate(settings["rate"])
            except:
                pass
        
    def load_settings(self, prefs):
        self.enable_speech_check.setChecked(prefs["accessibility_feedback"])
        
        # if self.prefer_sapi_check and sys.platform == "win32":
        #     self.prefer_sapi_check.setChecked(prefs["tts_prefer_sapi"])
        #     if self.voice_settings_btn:
        #         self.voice_settings_btn.setVisible(prefs["tts_prefer_sapi"])
            
        self.interrupt_check.setChecked(prefs["tts_speech_interrupt"])
        
        self.on_speech_toggled(prefs["accessibility_feedback"])
        
    def save_settings(self, prefs):
        prefs["accessibility_feedback"] = self.enable_speech_check.isChecked()
        
        # if self.prefer_sapi_check and sys.platform == "win32":
        #     prefs["tts_prefer_sapi"] = self.prefer_sapi_check.isChecked()
            
        prefs["tts_speech_interrupt"] = self.interrupt_check.isChecked()

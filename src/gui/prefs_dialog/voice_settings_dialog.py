from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QComboBox, 
                               QDoubleSpinBox, QDialogButtonBox)
from PySide6.QtCore import Qt
import sys
from utilities.speech import speech_manager

class VoiceSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Voice Settings")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumSize(400, 250)
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.voice_combo = QComboBox()
        self.populate_voices()
        form_layout.addRow("Voice:", self.voice_combo)
        
        self.volume_spin = QDoubleSpinBox()
        self.volume_spin.setRange(0.0, 100.0)
        self.volume_spin.setSingleStep(1.0)
        self.volume_spin.setDecimals(1)
        form_layout.addRow("Volume:", self.volume_spin)
        
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0.1, 10.0)
        self.rate_spin.setSingleStep(0.1)
        self.rate_spin.setDecimals(1)
        self.rate_spin.setToolTip("Speed")
        form_layout.addRow("Rate:", self.rate_spin)
        
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def populate_voices(self):
        try:
            voice_count = speech_manager.get_voices()
            for i in range(voice_count):
                voice_name = speech_manager.get_voice(i)
                self.voice_combo.addItem(voice_name)
        except:
            pass
            
    def on_voice_changed(self, voice_name):
        if not voice_name:
            return
        try:
            index = self.voice_combo.currentIndex()
            speech_manager.set_voice(index)
            speech_manager.output(f"Voice changed to {voice_name}", True)
        except:
            pass
            
    def load_settings(self):
        from app_config import prefs
        try:
            self.volume_spin.setValue(prefs.prefs["tts_volume"])
            self.rate_spin.setValue(prefs.prefs["tts_rate"])
            
            voice_name = prefs.prefs["tts_voice"]
            if voice_name:
                index = self.voice_combo.findText(voice_name)
                if index >= 0:
                    self.voice_combo.setCurrentIndex(index)
        except:
            pass
        
        self.voice_combo.currentTextChanged.connect(self.on_voice_changed)
            
    def get_settings(self):
        return {
            "voice": self.voice_combo.currentText(),
            "volume": self.volume_spin.value(),
            "rate": self.rate_spin.value()
        }

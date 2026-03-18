from PySide6.QtWidgets import QWidget, QFormLayout, QComboBox, QSpinBox

class MediaPanel(QWidget):
    def __init__(self, parent=None, audio_devices=None):
        super().__init__(parent)
        self.audio_devices = audio_devices or [[]]
        self.setup_ui()
        
    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.volume_offset_spin = QSpinBox()
        self.volume_offset_spin.setRange(1, 20)
        layout.addRow(_("Volume Offset:"), self.volume_offset_spin)
        
        self.seek_offset_spin = QSpinBox()
        self.seek_offset_spin.setRange(1, 60)
        layout.addRow(_("Seek Offset:"), self.seek_offset_spin)
        
        self.audio_device_combo = QComboBox()
        self.audio_device_combo.addItems(self.audio_devices)
        layout.addRow(_("Audio Device:"), self.audio_device_combo)
        
    def load_settings(self, prefs):
        self.volume_offset_spin.setValue(prefs["offset"]["volume"])
        self.seek_offset_spin.setValue(prefs["offset"]["seek"])
        
        if len(self.audio_devices) > 0 and prefs["device"] < len(self.audio_devices):
            self.audio_device_combo.setCurrentIndex(prefs["device"])
            
    def save_settings(self, prefs):
        prefs["offset"]["volume"] = self.volume_offset_spin.value()
        prefs["offset"]["seek"] = self.seek_offset_spin.value()
        prefs["device"] = self.audio_device_combo.currentIndex()

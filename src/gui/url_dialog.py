
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, 
                               QPushButton, QLabel, QMessageBox)
from PySide6.QtCore import Qt, Signal, Slot
from app_config import prefs
from utilities.functions import isValidURL
from player.utilities import ensure_ytdlp_available

class URLDialog(QDialog):
    url_opened = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Open URL")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumSize(400, 120)
        self.setup_ui()
        self.load_urls()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        label = QLabel("Enter or select a media URL:")
        layout.addWidget(label)
        
        self.url_combo = QComboBox()
        self.url_combo.setEditable(True)
        self.url_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        layout.addWidget(self.url_combo)
        
        button_layout = QHBoxLayout()
        
        self.open_button = QPushButton("Open")
        self.open_button.clicked.connect(self.open_url)
        self.open_button.setDefault(True)
        button_layout.addWidget(self.open_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
    def load_urls(self):
        self.url_combo.clear()
        urls = prefs.prefs.get("urlls", [])
        for url in urls:
            self.url_combo.addItem(url)
            
    def is_valid_url(self, url):
        return isValidURL(url)
        
    def add_url_to_history(self, url):
        urls = prefs.prefs.get("urlls", [])
        
        if url in urls:
            urls.remove(url)
        
        urls.insert(0, url)
        
        if len(urls) > 50:
            urls = urls[:50]
            
        prefs.prefs["urlls"] = urls
        prefs.save()
        
    @Slot()
    def open_url(self):
        url = self.url_combo.currentText().strip()
        
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a URL.")
            return
            
        if not self.is_valid_url(url):
            QMessageBox.warning(self, "Invalid URL", f"'{url}' is not a valid URL.")
            return

        if not ensure_ytdlp_available(self, show_message=True):
            return
            
        self.add_url_to_history(url)
        self.url_opened.emit(url)
        self.accept()

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                               QLabel, QPushButton, QMessageBox)
from PySide6.QtCore import Qt, Signal, Slot
import utilities.vlc_bootstrap
from av_play import Playlist


class PlaylistEditDialog(QDialog):
    playlist_updated = Signal(str, str)
    
    def __init__(self, playlist_name, playlist, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Edit Playlist"))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(400, 150)
        self.original_name = playlist_name
        self.playlist = playlist
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel(_("Name:")))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(_("Enter playlist name"))
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        layout.addStretch()
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_button = QPushButton(_("Cancel"))
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        confirm_button = QPushButton(_("Confirm"))
        confirm_button.clicked.connect(self.confirm_update)
        confirm_button.setDefault(True)
        buttons_layout.addWidget(confirm_button)
        
        layout.addLayout(buttons_layout)
        
    def load_data(self):
        self.name_edit.setText(self.original_name)
        self.name_edit.setFocus()
        self.name_edit.selectAll()
        
    @Slot()
    def confirm_update(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                _("Warning"),
                _("Please enter a playlist name"),
            )
            self.name_edit.setFocus()
            return
            
        self.playlist.title = name
        
        self.playlist_updated.emit(self.original_name, name)
        self.accept()

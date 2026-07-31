from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                               QLabel, QPushButton, QListWidget, QFileDialog,
                               QMessageBox, QSizePolicy)
from PySide6.QtCore import Qt, Signal, Slot
import utilities.mpv_bootstrap
from media_core.av_play import Playlist, PlaylistEntry
import os


class PlaylistCreateDialog(QDialog):
    playlist_created = Signal(str, Playlist)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Create Playlist"))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(600, 400)
        self.tracks = []
        self.setup_ui()
        
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
        
        tracks_layout = QVBoxLayout()
        tracks_label = QLabel(_("Tracks:"))
        tracks_layout.addWidget(tracks_label)
        
        self.tracks_list = QListWidget()
        self.tracks_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tracks_layout.addWidget(self.tracks_list)
        
        browse_button = QPushButton(_("Browse"))
        browse_button.clicked.connect(self.browse_tracks)
        tracks_layout.addWidget(browse_button)
        
        layout.addLayout(tracks_layout)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        confirm_button = QPushButton(_("Create"))
        confirm_button.clicked.connect(self.confirm_creation)
        confirm_button.setDefault(True)
        buttons_layout.addWidget(confirm_button)

        cancel_button = QPushButton(_("Cancel"))
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        layout.addLayout(buttons_layout)
        
        self.name_edit.setFocus()
        
    @Slot()
    def browse_tracks(self):
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter(_("Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a);;All Files (*)"))
        
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            for file_path in files:
                if file_path not in self.tracks:
                    self.tracks.append(file_path)
                    filename = os.path.basename(file_path)
                    self.tracks_list.addItem(filename)
                    
    @Slot()
    def confirm_creation(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                _("Warning"),
                _("Please enter a playlist name"),
            )
            self.name_edit.setFocus()
            return
            
        playlist = Playlist(title=name)
        for track_path in self.tracks:
            entry = PlaylistEntry(location=track_path)
            playlist.add_entry(entry)
            
        self.playlist_created.emit(name, playlist)
        self.accept()

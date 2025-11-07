from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                               QPushButton, QLabel, QMessageBox)
from PySide6.QtCore import Qt, Signal, Slot
from av_play import PlaylistManager


class PlaylistSelectionDialog(QDialog):
    playlist_selected = Signal(str)
    
    def __init__(self, playlist_manager: PlaylistManager, parent=None):
        super().__init__(parent)
        self.playlist_manager = playlist_manager
        self.setWindowTitle("Select Playlist")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(400, 300)
        self.setup_ui()
        self.load_playlists()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        label = QLabel("Select a playlist to add the file to:")
        layout.addWidget(label)
        
        self.playlists_list = QListWidget()
        self.playlists_list.itemDoubleClicked.connect(self.accept_selection)
        layout.addWidget(self.playlists_list)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        select_button = QPushButton("Select")
        select_button.clicked.connect(self.accept_selection)
        select_button.setDefault(True)
        buttons_layout.addWidget(select_button)
        
        layout.addLayout(buttons_layout)
        
    def load_playlists(self):
        self.playlists_list.clear()
        playlists = self.playlist_manager.list_playlists()
        
        if not playlists:
            no_playlists_label = QLabel("No playlists available. Create a playlist first.")
            no_playlists_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_playlists_label.setStyleSheet("color: gray; font-style: italic;")
        else:
            for playlist_name in playlists:
                self.playlists_list.addItem(playlist_name)
                
    @Slot()
    def accept_selection(self):
        current_item = self.playlists_list.currentItem()
        if current_item:
            playlist_name = current_item.text()
            self.playlist_selected.emit(playlist_name)
            self.accept()
        else:
            QMessageBox.warning(self, "Warning", "Please select a playlist")
            
    def get_selected_playlist(self):
        current_item = self.playlists_list.currentItem()
        return current_item.text() if current_item else None
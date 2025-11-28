from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QListWidget, QSplitter, QLabel, QMessageBox,
                               QListWidgetItem)
from PySide6.QtCore import Qt, Signal
from playlist_view import PlaylistView
from playlist_create_dialog import PlaylistCreateDialog
from playlist_edit_dialog import PlaylistEditDialog
from av_play import Playlist, PlaylistManager
import os
import json

from utilities.functions import get_app_path


class PlaylistsWidget(QWidget):
    playlist_selected = Signal(Playlist)
    
    def __init__(self, parent=None, play_callback=None):
        super().__init__(parent)
        self.play_callback = play_callback
        self.playlist_manager = PlaylistManager()
        self.setup_ui()
        self.setup_data_paths()
        self.load_playlists_data()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Playlists"))
        header_layout.addStretch()
        
        self.create_button = QPushButton("Create Playlist")
        self.create_button.clicked.connect(self.create_playlist)
        header_layout.addWidget(self.create_button)
        
        layout.addLayout(header_layout)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.playlists_list = QListWidget()
        self.playlists_list.setMaximumWidth(250)
        self.playlists_list.itemClicked.connect(self.on_playlist_selected)
        self.playlists_list.itemDoubleClicked.connect(self.edit_playlist)
        splitter.addWidget(self.playlists_list)
        
        self.playlist_view = PlaylistView(play_callback=self.play_callback)
        splitter.addWidget(self.playlist_view)
        
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        
    def setup_data_paths(self):
        app_dir = get_app_path()
        self.data_dir = os.path.join(app_dir, "data")
        self.playlists_dir = os.path.join(self.data_dir, "playlists")
        self.playlists_json_path = os.path.join(self.data_dir, "playlists.json")
        
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.playlists_dir, exist_ok=True)
        
    def load_playlists_data(self):
        if os.path.exists(self.playlists_json_path):
            try:
                with open(self.playlists_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for playlist_info in data.get("playlists", []):
                    name = playlist_info.get("name")
                    file_path = playlist_info.get("file_path")
                    
                    if name and file_path and os.path.exists(file_path):
                        try:
                            playlist = self.playlist_manager.load_playlist(name, file_path)
                            self.add_playlist_to_list(name)
                        except Exception as e:
                            print(f"Error loading playlist {name}: {e}")
                            
            except Exception as e:
                print(f"Error loading playlists data: {e}")
                
    def save_playlists_data(self):
        try:
            playlists_data = []
            
            for i in range(self.playlists_list.count()):
                item = self.playlists_list.item(i)
                name = item.text()
                playlist = self.playlist_manager.get_playlist(name)
                
                if playlist:
                    file_path = os.path.join(self.playlists_dir, f"{name}.json")
                    self.playlist_manager.save_playlist(name, file_path)
                    
                    playlist_info = {
                        "name": name,
                        "file_path": file_path
                    }
                    playlists_data.append(playlist_info)
                    
            data = {"playlists": playlists_data}
            
            with open(self.playlists_json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving playlists data: {e}")
            
    def add_playlist_to_list(self, name):
        item = QListWidgetItem(name)
        self.playlists_list.addItem(item)
        
    def create_playlist(self):
        dialog = PlaylistCreateDialog(self)
        dialog.playlist_created.connect(self.on_playlist_created)
        dialog.exec()
        
    def on_playlist_created(self, name, playlist):
        if name in [self.playlists_list.item(i).text() for i in range(self.playlists_list.count())]:
            QMessageBox.warning(self, "Warning", f"Playlist '{name}' already exists")
            return
            
        self.playlist_manager.playlists[name] = playlist
        self.add_playlist_to_list(name)
        self.save_playlists_data()
        
        for i in range(self.playlists_list.count()):
            if self.playlists_list.item(i).text() == name:
                self.playlists_list.setCurrentRow(i)
                self.on_playlist_selected(self.playlists_list.item(i))
                break
                
    def edit_playlist(self, item):
        name = item.text()
        playlist = self.playlist_manager.get_playlist(name)
        
        if playlist:
            dialog = PlaylistEditDialog(name, playlist, self)
            dialog.playlist_updated.connect(self.on_playlist_updated)
            dialog.exec()
            
    def on_playlist_updated(self, old_name, new_name):
        if old_name != new_name:
            if new_name in [self.playlists_list.item(i).text() for i in range(self.playlists_list.count())]:
                QMessageBox.warning(self, "Warning", f"Playlist '{new_name}' already exists")
                return
                
            playlist = self.playlist_manager.get_playlist(old_name)
            if playlist:
                self.playlist_manager.playlists[new_name] = playlist
                del self.playlist_manager.playlists[old_name]
                
                for i in range(self.playlists_list.count()):
                    if self.playlists_list.item(i).text() == old_name:
                        self.playlists_list.item(i).setText(new_name)
                        break
                        
        self.save_playlists_data()
        
    def on_playlist_selected(self, item):
        if item:
            name = item.text()
            playlist = self.playlist_manager.get_playlist(name)
            if playlist:
                self.playlist_view.set_playlist(playlist)
                self.playlist_selected.emit(playlist)
                
    def get_current_playlist(self):
        current_item = self.playlists_list.currentItem()
        if current_item:
            name = current_item.text()
            return self.playlist_manager.get_playlist(name)
        return None
        
    def refresh_current_playlist(self):
        current_item = self.playlists_list.currentItem()
        if current_item:
            self.on_playlist_selected(current_item)
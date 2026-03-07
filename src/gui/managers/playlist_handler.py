import os
from PySide6.QtWidgets import QMessageBox
from utilities.media_utils import get_media_files_from_directory
from av_play import Playlist, PlaylistEntry
from utilities.formats import formats
from utilities.util_gui import messageBox
from utilities import signal_manager
from playlist_manager.playlist_selection_dialog import PlaylistSelectionDialog
from playlist_manager.playlist_create_dialog import PlaylistCreateDialog

class PlaylistHandler:
    def __init__(self, main_window):
        self.main_window = main_window
        
    def load_folder_as_playlist(self, folder_path: str):
        media_files = get_media_files_from_directory(folder_path, formats["audio"], formats["video"])
        
        if not media_files:
            QMessageBox.information(
                self.main_window, 
                "No Media Found", 
                f"No supported media files were found in the selected folder:\n{folder_path}\n\nSupported formats include audio and video files."
            )
            return
        
        playlist = Playlist(title=os.path.basename(folder_path))
        for media_file in media_files:
            playlist.add_entry(PlaylistEntry(location=media_file, title=os.path.basename(media_file)))
        
        if media_files:
            self.main_window.player_widget.load_playlist(playlist, start_index=0)
            self.main_window.play_file(media_files[0])
            
    def add_to_playlist(self, file_path: str):
        playlist_manager = self.main_window.playlists_widget.playlist_manager
        
        if not playlist_manager.list_playlists():
            reply = QMessageBox.question(
                self.main_window, "No Playlists",
                "No playlists exist. Would you like to create a new playlist?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.create_new_playlist_with_file(file_path)
            return
        
        dialog = PlaylistSelectionDialog(playlist_manager, self.main_window)
        dialog.playlist_selected.connect(
            lambda playlist_name: self.add_file_to_playlist(file_path, playlist_name)
        )
        dialog.exec()
        
    def create_playlist_from_folder(self, folder_path: str):
        if not os.path.isdir(folder_path):
            messageBox("Error", "Selected path is not a directory")
            return
            
        audio_formats = [ext.lower() for ext in formats.get("audio", [])]
        video_formats = [ext.lower() for ext in formats.get("video", [])]
        
        media_files = get_media_files_from_directory(folder_path, audio_formats, video_formats)
        
        if not media_files:
            messageBox("No Media Files", "No supported media files found in the selected folder")
            return
            
        folder_name = os.path.basename(folder_path)
        playlist_name = f"Playlist from {folder_name}"
        
        playlist = Playlist(title=playlist_name)
        for file_path in media_files:
            entry = PlaylistEntry(location=file_path)
            playlist.add_entry(entry)
            
        self.main_window.playlists_widget.playlist_manager.playlists[playlist_name] = playlist
        self.main_window.playlists_widget.add_playlist_to_list(playlist_name)
        self.main_window.playlists_widget.save_playlists_data()
        
        self.main_window.player_widget.load_playlist(playlist, start_index=0, auto_play=True)
        
        signal_manager.statusbar_message.emit(f"Created and loaded playlist '{playlist_name}' with {len(media_files)} tracks")
        
    def add_file_to_playlist(self, file_path: str, playlist_name: str):
        playlist = self.main_window.playlists_widget.playlist_manager.get_playlist(playlist_name)
        if playlist:
            entry = PlaylistEntry(location=file_path)
            playlist.add_entry(entry)
            self.main_window.playlists_widget.save_playlists_data()
            
            filename = os.path.basename(file_path)
            signal_manager.statusbar_message.emit(f"Added '{filename}' to playlist '{playlist_name}'")
        else:
            messageBox("Error", f"Playlist '{playlist_name}' not found")
            
    def create_new_playlist_with_file(self, file_path: str):
        dialog = PlaylistCreateDialog(self.main_window)
        dialog.tracks = [file_path]
        dialog.tracks_list.addItem(os.path.basename(file_path))
        
        dialog.playlist_created.connect(
            lambda name, playlist: self.handle_new_playlist_created(name, playlist)
        )
        dialog.exec()
        
    def handle_new_playlist_created(self, name: str, playlist: Playlist):
        self.main_window.playlists_widget.playlist_manager.playlists[name] = playlist
        self.main_window.playlists_widget.add_playlist_to_list(name)
        self.main_window.playlists_widget.save_playlists_data()
        signal_manager.statusbar_message.emit(f"Created new playlist '{name}'")

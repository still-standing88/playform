import os
from PySide6.QtWidgets import QMessageBox
from utilities.media_utils import get_media_files_from_directory
import utilities.vlc_bootstrap
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
                _("No Media Found"), 
                _(
                    "No supported media files were found in the selected folder:\n{folder_path}\n\n"
                    "Supported formats include audio and video files."
                ).format(folder_path=folder_path)
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
                self.main_window, _("No Playlists"),
                _("No playlists exist. Would you like to create a new playlist?"),
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
            messageBox(_("Error"), _("Selected path is not a directory"))
            return
            
        audio_formats = [ext.lower() for ext in formats.get("audio", [])]
        video_formats = [ext.lower() for ext in formats.get("video", [])]
        
        media_files = get_media_files_from_directory(folder_path, audio_formats, video_formats)
        
        if not media_files:
            messageBox(_("No Media Files"), _("No supported media files found in the selected folder"))
            return
            
        folder_name = os.path.basename(folder_path)
        playlist_name = _("Playlist from {folder_name}").format(folder_name=folder_name)
        
        playlist = Playlist(title=playlist_name)
        for file_path in media_files:
            entry = PlaylistEntry(location=file_path)
            playlist.add_entry(entry)

        names = [os.path.basename(e.location) for e in playlist.entries]
        print(f"[TRACE] playlist_handler: create_playlist_from_folder title={playlist_name} total={len(names)} first3={names[:3]}")

        self.main_window.playlists_widget.playlist_manager.playlists[playlist_name] = playlist
        self.main_window.playlists_widget.add_playlist_to_list(playlist_name)
        self.main_window.playlists_widget.save_playlists_data()
        
        self.main_window.player_widget.load_playlist(playlist, start_index=0, auto_play=True)
        
        signal_manager.statusbar_message.emit(
            _("Created and loaded playlist '{playlist_name}' with {track_count} tracks").format(
                playlist_name=playlist_name,
                track_count=len(media_files),
            )
        )
        
    def add_file_to_playlist(self, file_path: str, playlist_name: str):
        playlist = self.main_window.playlists_widget.playlist_manager.get_playlist(playlist_name)
        if playlist is not None:
            entry = PlaylistEntry(location=file_path)
            playlist.add_entry(entry)
            self.main_window.playlists_widget.save_playlists_data()
            
            filename = os.path.basename(file_path)
            signal_manager.statusbar_message.emit(
                _("Added '{filename}' to playlist '{playlist_name}'").format(
                    filename=filename,
                    playlist_name=playlist_name,
                )
            )
        else:
            messageBox(_("Error"), _("Playlist '{playlist_name}' not found").format(playlist_name=playlist_name))
            
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
        signal_manager.statusbar_message.emit(f"{_('Created new playlist')} '{name}'")

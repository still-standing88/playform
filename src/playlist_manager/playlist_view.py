from PySide6.QtWidgets import (QWidget, QVBoxLayout, QMenu, QApplication,
                               QMessageBox, QFileDialog)
from PySide6.QtCore import Signal, Qt, Slot
from PySide6.QtGui import QAction
from gui_controls.list_control import Listctrl
from av_play import Playlist, PlaylistEntry
from utilities import signal_manager


class PlaylistView(QWidget):
    play_playlist_signal = Signal(Playlist)
    
    def __init__(self, parent=None, play_callback=None):
        super().__init__(parent)
        self.play_callback = play_callback
        self.current_playlist = None
        self.setup_ui()
        self.setup_context_menu()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.list_ctrl = Listctrl(self)
        self.list_ctrl.column(0, "File Name")
        self.list_ctrl.column(1, "Title")
        self.list_ctrl.column(2, "Artist")
        self.list_ctrl.column(3, "Album")
        
        self.list_ctrl.itemDoubleClicked.connect(self.on_item_activated)
        self.list_ctrl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_ctrl.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.list_ctrl)
        
    def setup_context_menu(self):
        self.context_menu = QMenu(self)
        
        add_tracks_action = QAction("Add Tracks", self)
        add_tracks_action.triggered.connect(self.add_tracks)
        self.context_menu.addAction(add_tracks_action)
        
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_selected)
        self.context_menu.addAction(delete_action)
        
        self.context_menu.addSeparator()
        
        clear_action = QAction("Clear Tracks", self)
        clear_action.triggered.connect(self.clear_tracks)
        self.context_menu.addAction(clear_action)
        
    @Slot(object)
    def show_context_menu(self, position):
        self.context_menu.exec(self.list_ctrl.mapToGlobal(position))
        
    def set_playlist(self, playlist):
        self.current_playlist = playlist
        self.refresh_view()
        
    def refresh_view(self):
        self.list_ctrl.clearAll()
        
        if not self.current_playlist:
            return
            
        self.list_ctrl.column(0, "File Name")
        self.list_ctrl.column(1, "Title")
        self.list_ctrl.column(2, "Artist")
        self.list_ctrl.column(3, "Album")
        
        for entry in self.current_playlist.entries:
            import os
            filename = os.path.basename(entry.location)
            title = entry.title or ""
            artist = entry.artist or ""
            album = entry.album or ""
            
            self.list_ctrl.appendRow({
                "0": filename,
                "1": title,
                "2": artist,
                "3": album
            })
            
    @Slot(object)
    def on_item_activated(self, item):
        if self.current_playlist and self.play_callback:
            self.play_callback(self.current_playlist)
        elif self.current_playlist:
            self.play_playlist_signal.emit(self.current_playlist)
            
    @Slot()
    def add_tracks(self):
        if not self.current_playlist:
            QMessageBox.warning(self, "Warning", "No playlist selected")
            return
            
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter("Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a);;All Files (*)")
        
        if file_dialog.exec():
            files = file_dialog.selectedFiles()
            for file_path in files:
                entry = PlaylistEntry(location=file_path)
                self.current_playlist.add_entry(entry)
            self.refresh_view()
            signal_manager.statusbar_message.emit(f"Added {len(files)} track(s) to playlist")
            
    @Slot()
    def delete_selected(self):
        if not self.current_playlist:
            return
            
        current_row = self.list_ctrl.getCurrentRowIndex()
        if current_row > 0:
            index = current_row - 1
            self.current_playlist.remove_entry(index)
            self.refresh_view()
            signal_manager.statusbar_message.emit("Track removed from playlist")
            
    @Slot()
    def clear_tracks(self):
        if not self.current_playlist:
            return
            
        reply = QMessageBox.question(self, "Confirm", "Clear all tracks?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.current_playlist.clear()
            self.refresh_view()
            signal_manager.statusbar_message.emit("Playlist cleared")
import os
import sys
import app_guard

from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, 
    QMenuBar, QMenu, QStatusBar, QToolBar, QDockWidget, QLabel,
    QFileDialog, QInputDialog, QSystemTrayIcon, QApplication, QMessageBox, QDialog, QPushButton
)
from PySide6.QtCore import Qt, Signal, QTimer, QUrl
from PySide6.QtGui import QAction, QIcon, QKeySequence

from app_db import UserFiles
from app_config import prefs
from EXPLORER.explorer_widget import ExplorerWidget
from player.player_widget import PlayerWidget
from playlist_manager.playlists_widget import PlaylistsWidget
from playlist_manager.playlist_selection_dialog import PlaylistSelectionDialog
from playlist_manager.playlist_create_dialog import PlaylistCreateDialog
from .favorites import FavoritesWidget
from .recents import RecentsWidget
from .prefs_dialog import PreferencesDialog
from .hotkeys_dialog import HotkeysDialog
from utilities.util_gui import menuItem, messageBox
from utilities.media_utils import get_media_files_from_directory
from av_play import Playlist, PlaylistEntry, formats
from tools.batch_converter_ui import BatchConverterUI
from tools.extractor_ui import ExtractorUI
from tools.tag_editor_ui import TagEditorUI
from tools.thumbnail_generator_ui import ThumbnailGeneratorUI


class ToolDialog(QDialog):
    def __init__(self, tool_widget, title, parent=None):
        super().__init__(parent)
        self.tool_widget = tool_widget
        self.is_minimized = False
        self.original_size = None
        
        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumSize(600, 400)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title bar with controls
        title_bar = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_bar.addWidget(title_label)
        title_bar.addStretch()
        
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setFixedSize(30, 25)
        self.minimize_btn.setToolTip("Minimize to sidebar")
        self.minimize_btn.clicked.connect(self.toggle_minimize)
        title_bar.addWidget(self.minimize_btn)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 25)
        close_btn.setToolTip("Close")
        close_btn.clicked.connect(self.close)
        title_bar.addWidget(close_btn)
        
        layout.addLayout(title_bar)
        layout.addWidget(self.tool_widget)
        
    def toggle_minimize(self):
        if self.is_minimized:
            self.restore_dialog()
        else:
            self.minimize_dialog()
            
    def minimize_dialog(self):
        if not self.is_minimized:
            self.original_size = self.size()
            self.resize(250, 80)
            self.is_minimized = True
            self.minimize_btn.setText("□")
            self.minimize_btn.setToolTip("Restore")
            self.tool_widget.hide()
            
    def restore_dialog(self):
        if self.is_minimized:
            if self.original_size:
                self.resize(self.original_size)
            else:
                self.resize(800, 600)
            self.is_minimized = False
            self.minimize_btn.setText("−")
            self.minimize_btn.setToolTip("Minimize to sidebar")
            self.tool_widget.show()
from tools.batch_converter_ui import BatchConverterUI
from tools.extractor_ui import ExtractorUI
from tools.tag_editor_ui import TagEditorUI
from tools.thumbnail_generator_ui import ThumbnailGeneratorUI


class MainWindow(QMainWindow):
    fileOpened = Signal(str)
    urlOpened = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        self.user_db = UserFiles()
        self.current_player_instance = None
        self.is_repeat_enabled = False
        self.tool_dialogs = {}  # Store open tool dialogs
        
        self.global_hotkeys = {
            "Play/Pause": self.toggle_play_pause,
            "Mute/Unmute": self.toggle_mute,
            "Volume Down": self.volume_down,
            "Volume Up": self.volume_up,
            "Previous": self.previous_track,
            "Next": self.next_track,
        }
        
        self.setWindowTitle("PlayForm")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        self.setup_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_statusbar()
        self.setup_dock_widgets()
        self.setup_main_layout()
        self.setup_system_tray()
        self.connect_signals()
        
        self.restore_window_state()
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(10)
        
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_layout.addWidget(self.main_splitter)
        
        self.favorites_widget = FavoritesWidget(self.user_db)
        self.recents_widget = RecentsWidget(self.user_db)
        
        self.explorer_widget = ExplorerWidget(
            self.user_db,
            parent=self,
            favorites_callback=self.add_to_favorites,
            open_callback=self.play_file,
            recent_callback=self.add_to_recents,
            playlist_callback=self.add_to_playlist,
            create_playlist_callback=self.create_playlist_from_folder
        )
        
        self.player_widget = PlayerWidget(self)
        
        self.playlists_widget = PlaylistsWidget(
            parent=self,
            play_callback=self.play_file
        )
        
    def setup_menus(self):
        menubar = self.menuBar()
        
        self.file_menu = menubar.addMenu("&File")
        self.setup_file_menu()
        
        self.media_menu = menubar.addMenu("&Media")
        self.setup_media_menu()
        
        self.view_menu = menubar.addMenu("&View")
        self.setup_view_menu()
        
        self.tools_menu = menubar.addMenu("&Tools")
        self.setup_tools_menu()
        
        self.about_menu = menubar.addMenu("&About")
        self.setup_about_menu()
        
    def setup_file_menu(self):
        self.open_file_action = QAction("&Open File...", self)
        self.open_file_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_file_action.triggered.connect(self.open_file_dialog)
        self.file_menu.addAction(self.open_file_action)
        
        self.open_url_action = QAction("Open &URL...", self)
        self.open_url_action.setShortcut(QKeySequence("Ctrl+U"))
        self.open_url_action.triggered.connect(self.open_url_dialog)
        self.file_menu.addAction(self.open_url_action)
        
        self.file_menu.addSeparator()
        
        self.recent_files_menu = QMenu("&Recent Files", self)
        self.file_menu.addMenu(self.recent_files_menu)
        self.update_recent_files_menu()
        
        self.file_menu.addSeparator()
        
        self.minimize_action = QAction("&Minimize to Taskbar", self)
        self.minimize_action.triggered.connect(self.hide_to_tray)
        self.file_menu.addAction(self.minimize_action)
        
        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close_application)
        self.file_menu.addAction(self.exit_action)
        
    def setup_media_menu(self):
        self.play_pause_action = QAction("&Play/Pause", self)
        self.play_pause_action.setShortcut(QKeySequence("Space"))
        self.play_pause_action.triggered.connect(self.toggle_play_pause)
        self.media_menu.addAction(self.play_pause_action)
        
        self.stop_action = QAction("&Stop", self)
        self.stop_action.setShortcut(QKeySequence("Ctrl+S"))
        self.stop_action.triggered.connect(self.stop_playback)
        self.media_menu.addAction(self.stop_action)
        
        self.media_menu.addSeparator()
        
        self.mute_action = QAction("&Mute/Unmute", self)
        self.mute_action.setShortcut(QKeySequence("M"))
        self.mute_action.triggered.connect(self.toggle_mute)
        self.media_menu.addAction(self.mute_action)
        
        self.media_menu.addSeparator()
        
        self.forward_action = QAction("&Forward", self)
        self.forward_action.setShortcut(QKeySequence("Right"))
        self.forward_action.triggered.connect(self.seek_forward)
        self.media_menu.addAction(self.forward_action)
        
        self.backward_action = QAction("&Backward", self)
        self.backward_action.setShortcut(QKeySequence("Left"))
        self.backward_action.triggered.connect(self.seek_backward)
        self.media_menu.addAction(self.backward_action)
        
        self.media_menu.addSeparator()
        
        self.previous_action = QAction("&Previous", self)
        self.previous_action.setShortcut(QKeySequence("Ctrl+Left"))
        self.previous_action.triggered.connect(self.previous_track)
        self.media_menu.addAction(self.previous_action)
        
        self.next_action = QAction("&Next", self)
        self.next_action.setShortcut(QKeySequence("Ctrl+Right"))
        self.next_action.triggered.connect(self.next_track)
        self.media_menu.addAction(self.next_action)
        
        self.media_menu.addSeparator()
        
        self.repeat_action = QAction("Toggle &Repeat: Off", self)
        self.repeat_action.setShortcut(QKeySequence("R"))
        self.repeat_action.triggered.connect(self.toggle_repeat)
        self.media_menu.addAction(self.repeat_action)
        
    def setup_view_menu(self):
        self.show_explorer_action = QAction("Show &Explorer", self)
        self.show_explorer_action.setCheckable(True)
        self.show_explorer_action.setChecked(True)
        self.show_explorer_action.triggered.connect(self.toggle_explorer)
        self.view_menu.addAction(self.show_explorer_action)
        
        self.minimize_player_action = QAction("&Minimize Player", self)
        self.minimize_player_action.setCheckable(True)
        self.minimize_player_action.triggered.connect(self.toggle_player_minimize)
        self.view_menu.addAction(self.minimize_player_action)
        
        self.show_playlists_action = QAction("Show &Playlists", self)
        self.show_playlists_action.setCheckable(True)
        self.show_playlists_action.setChecked(True)
        self.show_playlists_action.triggered.connect(self.toggle_playlists)
        self.view_menu.addAction(self.show_playlists_action)
        
    def setup_tools_menu(self):
        self.batch_converter_action = QAction("&Batch Converter", self)
        self.batch_converter_action.triggered.connect(self.open_batch_converter)
        self.tools_menu.addAction(self.batch_converter_action)
        
        self.extractor_action = QAction("&Media Extractor", self)
        self.extractor_action.triggered.connect(self.open_extractor)
        self.tools_menu.addAction(self.extractor_action)
        
        self.tag_editor_action = QAction("&Tag Editor", self)
        self.tag_editor_action.triggered.connect(self.open_tag_editor)
        self.tools_menu.addAction(self.tag_editor_action)
        
        self.thumbnail_generator_action = QAction("&Thumbnail Generator", self)
        self.thumbnail_generator_action.triggered.connect(self.open_thumbnail_generator)
        self.tools_menu.addAction(self.thumbnail_generator_action)
        
    def setup_about_menu(self):
        self.preferences_action = QAction("&Manage Preferences", self)
        self.preferences_action.triggered.connect(self.open_preferences)
        self.about_menu.addAction(self.preferences_action)
        
        self.hotkeys_action = QAction("Manage &Hotkeys", self)
        self.hotkeys_action.triggered.connect(self.open_hotkeys)
        self.about_menu.addAction(self.hotkeys_action)
        
    def setup_toolbar(self):
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        
        self.toolbar.addAction(self.open_file_action)
        self.toolbar.addAction(self.open_url_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.play_pause_action)
        self.toolbar.addAction(self.stop_action)
        self.toolbar.addAction(self.mute_action)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.previous_action)
        self.toolbar.addAction(self.next_action)
        
    def setup_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        self.media_info_label = QLabel("")
        self.status_bar.addPermanentWidget(self.media_info_label)
        
    def setup_dock_widgets(self):
        self.explorer_dock = QDockWidget("Explorer", self)
        self.explorer_dock.setWidget(self.explorer_widget)
        self.explorer_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.explorer_dock)
        
        self.player_dock = QDockWidget("Player", self)
        self.player_dock.setWidget(self.player_widget)
        self.player_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.player_dock)
        
        self.playlists_dock = QDockWidget("Playlists", self)
        self.playlists_dock.setWidget(self.playlists_widget)
        self.playlists_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.playlists_dock)
        
    def setup_main_layout(self):
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        favorites_label = QLabel("Favorites")
        favorites_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(favorites_label)
        left_layout.addWidget(self.favorites_widget, 1)
        
        recents_label = QLabel("Recent Files")
        recents_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(recents_label)
        left_layout.addWidget(self.recents_widget, 1)
        
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.setSizes([300, 1100])
        
    def setup_system_tray(self):
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MediaPlay))
            
            tray_menu = QMenu()
            
            self.show_hide_action = QAction("Hide", self)
            self.show_hide_action.triggered.connect(self.toggle_window_visibility)
            tray_menu.addAction(self.show_hide_action)
            
            tray_menu.addSeparator()
            
            exit_action = QAction("Exit", self)
            exit_action.triggered.connect(self.close_application)
            tray_menu.addAction(exit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_icon_activated)
            self.tray_icon.show()
        else:
            self.tray_icon = None
            
    def connect_signals(self):
        self.favorites_widget.itemRequested.connect(self.play_file)
        self.recents_widget.itemRequested.connect(self.play_file)
        
        if hasattr(self.explorer_dock, 'visibilityChanged'):
            self.explorer_dock.visibilityChanged.connect(self.update_explorer_menu)
        if hasattr(self.player_dock, 'visibilityChanged'):
            self.player_dock.visibilityChanged.connect(self.update_player_menu)
        if hasattr(self.playlists_dock, 'visibilityChanged'):
            self.playlists_dock.visibilityChanged.connect(self.update_playlists_menu)
            
    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Media File", "", 
            "Media Files (*.mp4 *.avi *.mkv *.mp3 *.wav *.flac *.ogg *.m4a);;All Files (*)"
        )
        if file_path:
            self.play_file(file_path)
            
    def open_url_dialog(self):
        url, ok = QInputDialog.getText(self, "Open URL", "Enter media URL:")
        if ok and url:
            self.play_url(url)
            
    def play_file(self, file_path: str):
        self.status_label.setText(f"Loading: {os.path.basename(file_path)}")
        self.media_info_label.setText(file_path)
        self.add_to_recents(file_path)
        self.update_recent_files_menu()
        self.fileOpened.emit(file_path)
        
    def play_url(self, url: str):
        self.status_label.setText(f"Loading URL: {url}")
        self.media_info_label.setText(url)
        self.urlOpened.emit(url)
        
    def add_to_favorites(self, file_path: str):
        self.favorites_widget.add_favorite(file_path)
        
    def add_to_recents(self, file_path: str):
        self.recents_widget.add_recent(file_path)
        
    def add_to_playlist(self, file_path: str):
        """Add a file to an existing playlist"""
        playlist_manager = self.playlists_widget.playlist_manager
        
        if not playlist_manager.list_playlists():
            reply = QMessageBox.question(
                self, "No Playlists",
                "No playlists exist. Would you like to create a new playlist?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.create_new_playlist_with_file(file_path)
            return
        
        dialog = PlaylistSelectionDialog(playlist_manager, self)
        dialog.playlist_selected.connect(
            lambda playlist_name: self.add_file_to_playlist(file_path, playlist_name)
        )
        dialog.exec()
        
    def create_playlist_from_folder(self, folder_path: str):
        """Create a new playlist from all media files in a folder"""
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
            
        self.playlists_widget.playlist_manager.playlists[playlist_name] = playlist
        self.playlists_widget.add_playlist_to_list(playlist_name)
        self.playlists_widget.save_playlists_data()
        
        self.status_label.setText(f"Created playlist '{playlist_name}' with {len(media_files)} tracks")
        
    def add_file_to_playlist(self, file_path: str, playlist_name: str):
        """Helper method to add a file to a specific playlist"""
        playlist = self.playlists_widget.playlist_manager.get_playlist(playlist_name)
        if playlist:
            entry = PlaylistEntry(location=file_path)
            playlist.add_entry(entry)
            self.playlists_widget.save_playlists_data()
            
            filename = os.path.basename(file_path)
            self.status_label.setText(f"Added '{filename}' to playlist '{playlist_name}'")
        else:
            messageBox("Error", f"Playlist '{playlist_name}' not found")
            
    def create_new_playlist_with_file(self, file_path: str):
        """Helper method to create a new playlist and add a file to it"""
        dialog = PlaylistCreateDialog(self)
        dialog.tracks = [file_path]
        dialog.tracks_list.addItem(os.path.basename(file_path))
        
        dialog.playlist_created.connect(
            lambda name, playlist: self.handle_new_playlist_created(name, playlist)
        )
        dialog.exec()
        
    def handle_new_playlist_created(self, name: str, playlist: Playlist):
        """Handle the creation of a new playlist"""
        self.playlists_widget.playlist_manager.playlists[name] = playlist
        self.playlists_widget.add_playlist_to_list(name)
        self.playlists_widget.save_playlists_data()
        self.status_label.setText(f"Created new playlist '{name}'")
        
    def update_recent_files_menu(self):
        self.recent_files_menu.clear()
        recent_files = self.recents_widget.get_recent_files_list()
        
        if not recent_files:
            no_recent_action = QAction("No recent files", self)
            no_recent_action.setEnabled(False)
            self.recent_files_menu.addAction(no_recent_action)
        else:
            for file_path in recent_files:
                action = QAction(os.path.basename(file_path), self)
                action.setToolTip(file_path)
                action.triggered.connect(lambda checked, path=file_path: self.play_file(path))
                self.recent_files_menu.addAction(action)
                
    def toggle_play_pause(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    state = self.player_widget.player.primary_instance.get_playback_state()
                    if state == "playing":
                        self.player_widget.player.primary_instance.pause()
                        self.status_label.setText("Paused")
                    else:
                        self.player_widget.player.primary_instance.play()
                        self.status_label.setText("Playing")
            except Exception as e:
                self.status_label.setText("No media loaded")
                
    def stop_playback(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    self.player_widget.player.primary_instance.stop()
                    self.status_label.setText("Stopped")
            except Exception as e:
                self.status_label.setText("No media loaded")
                
    def toggle_mute(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    self.status_label.setText("Mute toggled")
            except Exception as e:
                self.status_label.setText("No media loaded")
                
    def seek_forward(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    current_pos = self.player_widget.player.primary_instance.get_position()
                    self.player_widget.player.primary_instance.set_position(current_pos + 10)
            except Exception as e:
                pass
                
    def seek_backward(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    current_pos = self.player_widget.player.primary_instance.get_position()
                    self.player_widget.player.primary_instance.set_position(max(0, current_pos - 10))
            except Exception as e:
                pass
                
    def previous_track(self):
        self.status_label.setText("Previous track")
        
    def next_track(self):
        self.status_label.setText("Next track")

    def volume_down(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            instance = self.player_widget.player.primary_instance
            if instance and hasattr(instance, "get_volume") and hasattr(instance, "set_volume"):
                current_volume = instance.get_volume()
                instance.set_volume(max(0, current_volume - 5))

    def volume_up(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            instance = self.player_widget.player.primary_instance
            if instance and hasattr(instance, "get_volume") and hasattr(instance, "set_volume"):
                current_volume = instance.get_volume()
                instance.set_volume(min(100, current_volume + 5))
    
    def open_batch_converter(self):
        self.open_tool_dialog("batch_converter", BatchConverterUI(), "Batch Converter")
        
    def open_extractor(self):
        self.open_tool_dialog("extractor", ExtractorUI(), "Media Extractor")
        
    def open_tag_editor(self):
        self.open_tool_dialog("tag_editor", TagEditorUI(), "Tag Editor")
        
    def open_thumbnail_generator(self):
        self.open_tool_dialog("thumbnail_generator", ThumbnailGeneratorUI(), "Thumbnail Generator")
        
    def open_tool_dialog(self, tool_name, tool_widget, title):
        if tool_name in self.tool_dialogs and self.tool_dialogs[tool_name].isVisible():
            # Bring existing dialog to front
            self.tool_dialogs[tool_name].raise_()
            self.tool_dialogs[tool_name].activateWindow()
        else:
            # Create new dialog
            dialog = ToolDialog(tool_widget, title, self)
            self.tool_dialogs[tool_name] = dialog
            dialog.show()
            self.status_label.setText(f"Opened {title}")
        
    def toggle_repeat(self):
        self.is_repeat_enabled = not self.is_repeat_enabled
        prefs.prefs['repeat'] = self.is_repeat_enabled
        prefs.save()
        
        repeat_text = "Toggle Repeat: On" if self.is_repeat_enabled else "Toggle Repeat: Off"
        self.repeat_action.setText(repeat_text)
        self.status_label.setText(f"Repeat: {'On' if self.is_repeat_enabled else 'Off'}")
        
    def toggle_explorer(self, checked):
        self.explorer_dock.setVisible(checked)
        
    def toggle_player_minimize(self, checked):
        if checked:
            self.player_dock.hide()
        else:
            self.player_dock.show()
            
    def toggle_playlists(self, checked):
        self.playlists_dock.setVisible(checked)
        
    def update_explorer_menu(self, visible):
        self.show_explorer_action.setChecked(visible)
        
    def update_player_menu(self, visible):
        self.minimize_player_action.setChecked(not visible)
        
    def update_playlists_menu(self, visible):
        self.show_playlists_action.setChecked(visible)
        
    def open_preferences(self):
        dialog = PreferencesDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.status_label.setText("Preferences saved")
            
    def open_hotkeys(self):
        dialog = HotkeysDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.status_label.setText("Hotkeys updated")
            
    def hide_to_tray(self):
        if self.tray_icon:
            self.hide()
            self.show_hide_action.setText("Show")
            if hasattr(self.tray_icon, 'showMessage'):
                self.tray_icon.showMessage(
                    "PlayForm Media Player",
                    "Application was minimized to tray",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
        else:
            self.showMinimized()
            
    def toggle_window_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
            self.show_hide_action.setText("Show")
        else:
            self.show()
            self.raise_()
            self.activateWindow()
            self.show_hide_action.setText("Hide")
            
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window_visibility()
            
    def close_application(self):
        self.save_window_state()
        # Close all tool dialogs
        for dialog in self.tool_dialogs.values():
            if dialog.isVisible():
                dialog.close()
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()
        
    def save_window_state(self):
        prefs.prefs['window_geometry'] = self.saveGeometry().data().hex()
        prefs.prefs['window_state'] = self.saveState().data().hex()
        prefs.save()
        
    def restore_window_state(self):
        if 'window_geometry' in prefs.prefs and prefs.prefs['window_geometry']:
            try:
                geometry = bytes.fromhex(prefs.prefs['window_geometry'])
                self.restoreGeometry(geometry)
            except:
                pass
                
        if 'window_state' in prefs.prefs and prefs.prefs['window_state']:
            try:
                state = bytes.fromhex(prefs.prefs['window_state'])
                self.restoreState(state)
            except:
                pass
                
    def closeEvent(self, event):
        if self.tray_icon and self.tray_icon.isVisible():
            event.ignore()
            self.hide_to_tray()
        else:
            self.close_application()
            event.accept()



    def cli_load_file(self, ipc_msg_data:dict[str, str]):
        self.play_file(ipc_msg_data["msg_data"])

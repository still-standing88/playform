import os
import platform
import sys
import app_guard

from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, 
    QMenuBar, QMenu, QStatusBar, QToolBar, QDockWidget, QLabel,
    QFileDialog, QInputDialog, QSystemTrayIcon, QApplication, QMessageBox, QDialog,
    QPushButton
)
from PySide6.QtCore import Qt, Signal, QTimer, QUrl
from PySide6.QtGui import QAction, QIcon, QKeySequence

from app_db import UserFiles
from app_config import prefs
from EXPLORER.explorer_widget import ExplorerWidget
import app_db
from player.player_widget import PlayerWidget
from playlist_manager.playlists_widget import PlaylistsWidget
from playlist_manager.playlist_selection_dialog import PlaylistSelectionDialog
from playlist_manager.playlist_create_dialog import PlaylistCreateDialog
from .favorites import FavoritesWidget
from .recents import RecentsWidget
from .prefs_dialog import PreferencesDialog
from .hotkeys_dialog import HotkeysDialog
from .url_dialog import URLDialog
from utilities.util_gui import menuItem, messageBox
from utilities.media_utils import get_media_files_from_directory
from utilities.speech import speech_manager
from utilities import signal_manager
from av_play import Playlist, PlaylistEntry, formats
from tools.batch_converter_ui import BatchConverterUI
from tools.extractor_ui import ExtractorUI
from tools.tag_editor_ui import TagEditorUI
from tools.thumbnail_generator_ui import ThumbnailGeneratorUI
from tools.subtitle_converter_ui import SubtitleConverterUI
from tools.subtitle_editor_ui import SubtitleEditorUI
from gui_controls.key_event_filter import ShortcutManager
from app_config import key_config
from app_constance.file_filter import file_filter
from .tool_dialog import ToolDialog
from tools.logs_viewer_dialog import LogsViewerDialog
from tools.debug_console_dock import DebugConsoleDock
from app_constance.styles import SECTION_LABEL_STYLE



class MainWindow(QMainWindow):
    fileOpened = Signal(str)
    urlOpened = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        self.setObjectName("mainWindow")
        
        self.user_db = app_db.user_db
        self.current_player_instance = None
        self.is_repeat_enabled = False
        self.tool_dialogs = {}
        self.active_tool_name = None
        self.show_tool_button: QPushButton
        
        self.global_hotkeys = {
            "Play/Pause": self.toggle_play_pause,
            "Mute/Unmute": self.toggle_mute,
            "Volume Down": self.volume_down,
            "Volume Up": self.volume_up,
            "Previous": self.previous_track,
            "Next": self.next_track,
        }


        self.user_db.connect_to_database()
        self.setWindowTitle("PlayForm")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        self._shortcut_manager = ShortcutManager(self)
        
        self.setup_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_statusbar()
        self.setup_dock_widgets()
        self.setup_main_layout()
        self.setup_system_tray()
        self.connect_signals()
        self.set_shortcuts()
        
        self.restore_window_state()

    def set_shortcuts(self):
        hotkeys = key_config.key_config["Main interface"]
        shortcuts = {
            hotkeys["Open file"]: self.open_file_dialog,
            hotkeys["Open folder"]: self.open_folder_dialog,
            hotkeys["Open URL"]: self.open_url_dialog,
            hotkeys["Show/Hide explorer"]: self.toggle_explorer_shortcut,
            hotkeys["Show/Hide player controls"]: self.toggle_player_minimize_shortcut,
            hotkeys["Hide window"]: self.hide_to_tray,
            hotkeys["Exit"]: self.close_application,
            hotkeys["Focus explorer"]: self.focus_explorer,
            hotkeys["Focus player"]: self.focus_player,
            hotkeys["Hotkeys dialog"]: self.open_hotkeys,
            hotkeys["Prefrences Dialog"]: self.open_preferences,
        }

        self._shortcut_manager.clear_shortcuts()
        for shortcut in shortcuts:
            self._shortcut_manager.add_context_shortcut(shortcut, shortcuts[shortcut])
        self.install_shortcuts()

    def reset_shortcuts(self):
        self.set_shortcuts()

    def reset_shortcuts_callback(self):
        self.reset_shortcuts()
        
        if hasattr(self.explorer_widget, 'reset_shortcuts'):
            self.explorer_widget.reset_shortcuts()
            
        if hasattr(self.player_widget, 'reset_shortcuts'):
            self.player_widget.reset_shortcuts()

    def install_shortcuts(self):
        self._shortcut_manager.install_on_application()
    
    def uninstall_shortcuts(self):
        self._shortcut_manager.uninstall_from_application()

    def toggle_explorer_shortcut(self):
        is_visible = self.explorer_dock.isVisible()
        self.explorer_dock.setVisible(not is_visible)
        self.show_explorer_action.setChecked(not is_visible)
        if not is_visible:
            self.explorer_widget.setFocus()

    def toggle_player_minimize_shortcut(self):
        is_visible = self.player_dock.isVisible()
        self.player_dock.setVisible(not is_visible)
        self.minimize_player_action.setChecked(is_visible)
        if not is_visible:
            self.player_widget.setFocus()

    def focus_explorer(self):
        if self.explorer_dock.isVisible():
            self.explorer_widget.setFocus()

    def focus_player(self):
        if self.player_dock.isVisible():
            self.player_widget.setFocus()

    def setup_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(10)
        
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("mainSplitter")
        self.main_layout.addWidget(self.main_splitter)
        
        self.favorites_widget = FavoritesWidget(self.user_db)
        self.favorites_widget.setObjectName("favoritesWidget")
        self.recents_widget = RecentsWidget(self.user_db)
        self.recents_widget.setObjectName("recentsWidget")
        
        self.explorer_widget = ExplorerWidget(
            self.user_db,
            parent=self,
            favorites_callback=self.add_to_favorites,
            open_callback=self.play_file,
            recent_callback=self.add_to_recents,
            playlist_callback=self.add_to_playlist,
            create_playlist_callback=self.create_playlist_from_folder
        )
        self.explorer_widget.setObjectName("explorerWidget")
        
        self.player_widget = PlayerWidget(self)
        self.player_widget.setObjectName("playerWidget")
        
        self.playlists_widget = PlaylistsWidget(
            parent=self,
            play_callback=self.play_file
        )
        self.playlists_widget.setObjectName("playlistsWidget")
        
    def setup_menus(self):
        menubar = self.menuBar()
        menubar.setObjectName("menuBar")
        
        self.file_menu = menubar.addMenu("&File")
        self.file_menu.setObjectName("fileMenu")
        self.setup_file_menu()
        
        self.media_menu = menubar.addMenu("&Media")
        self.media_menu.setObjectName("mediaMenu")
        self.setup_media_menu()
        
        self.view_menu = menubar.addMenu("&View")
        self.view_menu.setObjectName("viewMenu")
        self.setup_view_menu()
        
        self.tools_menu = menubar.addMenu("&Tools")
        self.tools_menu.setObjectName("toolsMenu")
        self.setup_tools_menu()
        
        self.about_menu = menubar.addMenu("&About")
        self.about_menu.setObjectName("aboutMenu")
        self.setup_about_menu()
        
    def setup_file_menu(self):
        self.open_file_action = QAction("&Open File...", self)
        self.open_file_action.triggered.connect(self.open_file_dialog)
        self.file_menu.addAction(self.open_file_action)
        
        self.open_folder_action = QAction("Open &Folder...", self)
        self.open_folder_action.triggered.connect(self.open_folder_dialog)
        self.file_menu.addAction(self.open_folder_action)
        
        self.open_url_action = QAction("Open &URL...", self)
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
        self.exit_action.triggered.connect(self.close_application)
        self.file_menu.addAction(self.exit_action)
        
    def setup_media_menu(self):
        self.play_pause_action = QAction("&Play/Pause", self)
        self.play_pause_action.triggered.connect(self.toggle_play_pause)
        self.media_menu.addAction(self.play_pause_action)
        
        self.stop_action = QAction("&Stop", self)
        self.stop_action.triggered.connect(self.stop_playback)
        self.media_menu.addAction(self.stop_action)
        
        self.media_menu.addSeparator()
        
        self.mute_action = QAction("&Mute/Unmute", self)
        self.mute_action.triggered.connect(self.toggle_mute)
        self.media_menu.addAction(self.mute_action)
        
        self.media_menu.addSeparator()
        
        self.forward_action = QAction("&Forward", self)
        self.forward_action.triggered.connect(self.seek_forward)
        self.media_menu.addAction(self.forward_action)
        
        self.backward_action = QAction("&Backward", self)
        self.backward_action.triggered.connect(self.seek_backward)
        self.media_menu.addAction(self.backward_action)
        
        self.media_menu.addSeparator()
        
        self.previous_action = QAction("&Previous", self)
        self.previous_action.triggered.connect(self.previous_track)
        self.media_menu.addAction(self.previous_action)
        
        self.next_action = QAction("&Next", self)
        self.next_action.triggered.connect(self.next_track)
        self.media_menu.addAction(self.next_action)
        
        self.media_menu.addSeparator()
        
        self.repeat_action = QAction("Toggle &Repeat: Off", self)
        self.repeat_action.triggered.connect(self.toggle_repeat)
        self.media_menu.addAction(self.repeat_action)
        
    def setup_view_menu(self):
        self.show_explorer_action = QAction("Show &Explorer", self)
        self.show_explorer_action.setCheckable(True)
        self.show_explorer_action.setChecked(False)
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

        self.subtitle_tools_menu = self.tools_menu.addMenu("&Subtitle Tools")
        self.subtitle_converter_action = QAction("Subtitle &Converter", self)
        self.subtitle_converter_action.triggered.connect(self.open_subtitle_converter)
        self.subtitle_tools_menu.addAction(self.subtitle_converter_action)
        
        self.subtitle_editor_action = QAction("Subtitle &Editor", self)
        self.subtitle_editor_action.triggered.connect(self.open_subtitle_editor)
        self.subtitle_tools_menu.addAction(self.subtitle_editor_action)

        self.debug_menu = self.tools_menu.addMenu("&Debug")
        self.view_logs_action = QAction("&View Logs…", self)
        self.view_logs_action.triggered.connect(self.open_logs_viewer)
        self.debug_menu.addAction(self.view_logs_action)

        self.show_console_dock_action = QAction("Show &Console Dock", self)
        self.show_console_dock_action.setCheckable(True)
        self.show_console_dock_action.setChecked(False)
        self.show_console_dock_action.triggered.connect(self.toggle_console_dock)
        self.debug_menu.addAction(self.show_console_dock_action)
        
    def setup_about_menu(self):
        self.preferences_action = QAction("&Manage Preferences", self)
        self.preferences_action.triggered.connect(self.open_preferences)
        self.about_menu.addAction(self.preferences_action)
        
        self.hotkeys_action = QAction("Manage &Hotkeys", self)
        self.hotkeys_action.triggered.connect(self.open_hotkeys)
        self.about_menu.addAction(self.hotkeys_action)
        
    def setup_toolbar(self):
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setObjectName("mainToolbar")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)
        
        self.toolbar.addAction(self.open_file_action)
        self.toolbar.addAction(self.open_folder_action)
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
        self.status_bar.setObjectName("statusBar")
        self.setStatusBar(self.status_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        self.status_bar.addWidget(self.status_label)
        
        self.media_info_label = QLabel("")
        self.media_info_label.setObjectName("mediaInfoLabel")
        self.status_bar.addPermanentWidget(self.media_info_label)
        

        self.show_tool_button = QPushButton("Show Tool")
        self.show_tool_button.setObjectName("showToolButton")
        self.show_tool_button.clicked.connect(self.show_hidden_tool)
        self.show_tool_button.setVisible(False)
        self.status_bar.addPermanentWidget(self.show_tool_button)
        
        signal_manager.statusbar_message.connect(self._update_status_message)
        signal_manager.media_info_message.connect(self.media_info_label.setText)
        
    def setup_dock_widgets(self):
        self.explorer_dock = QDockWidget("Explorer", self)
        self.explorer_dock.setObjectName("explorerDock")
        self.explorer_dock.setWidget(self.explorer_widget)
        self.explorer_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.explorer_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.explorer_dock.setVisible(False)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.explorer_dock)
        
        self.player_dock = QDockWidget("Player", self)
        self.player_dock.setObjectName("playerDock")
        self.player_dock.setWidget(self.player_widget)
        self.player_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.player_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.player_dock)
        
        self.playlists_dock = QDockWidget("Playlists", self)
        self.playlists_dock.setObjectName("playlistsDock")
        self.playlists_dock.setWidget(self.playlists_widget)
        self.playlists_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.playlists_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.playlists_dock)


        self.debug_console_dock = DebugConsoleDock(self)
        self.debug_console_dock.setObjectName("debugConsoleDock")
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.debug_console_dock)
        self.debug_console_dock.hide()
        if hasattr(self.debug_console_dock, 'visibilityChanged'):
            self.debug_console_dock.visibilityChanged.connect(self.update_console_menu)
        
    def setup_main_layout(self):
        left_panel = QWidget()
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        favorites_label = QLabel("Favorites")
        favorites_label.setObjectName("favoritesLabel")
        favorites_label.setStyleSheet(SECTION_LABEL_STYLE)
        left_layout.addWidget(favorites_label)
        left_layout.addWidget(self.favorites_widget, 1)
        
        recents_label = QLabel("Recent Files")
        recents_label.setObjectName("recentsLabel")
        recents_label.setStyleSheet(SECTION_LABEL_STYLE)
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

        self.urlOpened.connect(self.player_widget.change_path)
        self.fileOpened.connect(self.player_widget.change_path)
        if hasattr(self.explorer_dock, 'visibilityChanged'):
            self.explorer_dock.visibilityChanged.connect(self.update_explorer_menu)
        if hasattr(self.player_dock, 'visibilityChanged'):
            self.player_dock.visibilityChanged.connect(self.update_player_menu)
        if hasattr(self.playlists_dock, 'visibilityChanged'):
            self.playlists_dock.visibilityChanged.connect(self.update_playlists_menu)
            
    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Media File", "", file_filter
        )
        if file_path:
            self.play_file(file_path)
    
    def open_folder_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Open Folder", ""
        )
        if folder_path:
            self.load_folder_as_playlist(folder_path)
            
    def open_url_dialog(self):
        dialog = URLDialog(self)
        dialog.url_opened.connect(self.play_url)
        dialog.exec()

    def load_folder_as_playlist(self, folder_path: str):
        media_files = get_media_files_from_directory(folder_path, formats["audio"], formats["video"])
        
        if not media_files:
            QMessageBox.information(
                self, 
                "No Media Found", 
                f"No supported media files were found in the selected folder:\n{folder_path}\n\nSupported formats include audio and video files."
            )
            return
        
        playlist = Playlist(title=os.path.basename(folder_path))
        for media_file in media_files:
            playlist.add_entry(PlaylistEntry(location=media_file, title=os.path.basename(media_file)))
        
        if media_files:
            self.player_widget.load_playlist(playlist, start_index=0)
            self.play_file(media_files[0])
            
    def play_file(self, file_path: str):
        signal_manager.statusbar_message.emit(f"Loading: {os.path.basename(file_path)}")
        signal_manager.media_info_message.emit(file_path)
        self.add_to_recents(file_path)
        self.update_recent_files_menu()
        self.fileOpened.emit(file_path)
        
    def play_url(self, url: str):
        signal_manager.statusbar_message.emit(f"Loading URL: {url}")
        signal_manager.media_info_message.emit(url)
        self.urlOpened.emit(url)
        
    def add_to_favorites(self, file_path: str):
        self.favorites_widget.add_favorite(file_path)
        
    def add_to_recents(self, file_path: str):
        self.recents_widget.add_recent(file_path)
        
    def add_to_playlist(self, file_path: str):

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
        

        self.player_widget.load_playlist(playlist, start_index=0, auto_play=True)
        
        signal_manager.statusbar_message.emit(f"Created and loaded playlist '{playlist_name}' with {len(media_files)} tracks")
        
    def add_file_to_playlist(self, file_path: str, playlist_name: str):

        playlist = self.playlists_widget.playlist_manager.get_playlist(playlist_name)
        if playlist:
            entry = PlaylistEntry(location=file_path)
            playlist.add_entry(entry)
            self.playlists_widget.save_playlists_data()
            
            filename = os.path.basename(file_path)
            signal_manager.statusbar_message.emit(f"Added '{filename}' to playlist '{playlist_name}'")
        else:
            messageBox("Error", f"Playlist '{playlist_name}' not found")
            
    def create_new_playlist_with_file(self, file_path: str):

        dialog = PlaylistCreateDialog(self)
        dialog.tracks = [file_path]
        dialog.tracks_list.addItem(os.path.basename(file_path))
        
        dialog.playlist_created.connect(
            lambda name, playlist: self.handle_new_playlist_created(name, playlist)
        )
        dialog.exec()
        
    def handle_new_playlist_created(self, name: str, playlist: Playlist):

        self.playlists_widget.playlist_manager.playlists[name] = playlist
        self.playlists_widget.add_playlist_to_list(name)
        self.playlists_widget.save_playlists_data()
        signal_manager.statusbar_message.emit(f"Created new playlist '{name}'")
        
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
                action.triggered.connect(lambda checked=False, path=file_path: self.play_file(path))
                self.recent_files_menu.addAction(action)

    def _update_status_message(self, message: str):
        self.status_label.setText(message)
        
        if prefs.prefs["accessibility_feedback"]:
            # The following is a conditional check to disable Sapi onWindows until a solution is fodun for GUI freezing when Sapi speaks.
            if  sys.platform == "win32" and speech_manager.current_driver() == "Sapi5":
                pass

            speech_manager.output(message, prefs.prefs["tts_speech_interrupt"])

    def toggle_play_pause(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    state = self.player_widget.player.primary_instance.get_playback_state()
                    if state == "playing":
                        self.player_widget.player.primary_instance.pause()
                        signal_manager.statusbar_message.emit("Paused")
                    else:
                        self.player_widget.player.primary_instance.play()
                        signal_manager.statusbar_message.emit("Playing")
            except Exception as e:
                signal_manager.statusbar_message.emit("No media loaded")
                
    def stop_playback(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    self.player_widget.player.primary_instance.stop()
                    signal_manager.statusbar_message.emit("Stopped")
            except Exception as e:
                signal_manager.statusbar_message.emit("No media loaded")
                
    def toggle_mute(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    signal_manager.statusbar_message.emit("Mute toggled")
            except Exception as e:
                signal_manager.statusbar_message.emit("No media loaded")
                
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
        signal_manager.statusbar_message.emit("Previous track")
        
    def next_track(self):
        signal_manager.statusbar_message.emit("Next track")

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
    
    def open_subtitle_converter(self):
        self.open_tool_dialog("subtitle_converter", SubtitleConverterUI(), "Subtitle Converter")
    
    def open_subtitle_editor(self):
        self.open_tool_dialog("subtitle_editor", SubtitleEditorUI(), "Subtitle Editor")
        
    def open_tool_dialog(self, tool_name, tool_widget, title):

        if self.active_tool_name and self.active_tool_name != tool_name:
            if self.active_tool_name in self.tool_dialogs:
                active_dialog = self.tool_dialogs[self.active_tool_name]
                if active_dialog.isVisible() or self.show_tool_button.isVisible():
                    QMessageBox.information(
                        self,
                        "Tool Already Open",
                        f"'{active_dialog.title}' is already open. Please close it before opening another tool.",
                        QMessageBox.StandardButton.Ok
                    )
                    return
        
        if tool_name in self.tool_dialogs:
            dialog = self.tool_dialogs[tool_name]
            dialog.show_dialog()
            self.show_tool_button.setVisible(False)
        else:
            dialog = ToolDialog(tool_widget, title, self)
            dialog.dialog_hidden.connect(lambda: self.on_tool_hidden(tool_name, title))
            dialog.finished.connect(lambda: self.on_tool_closed(tool_name))
            self.tool_dialogs[tool_name] = dialog
            dialog.show_dialog()
        
        self.active_tool_name = tool_name
        signal_manager.statusbar_message.emit(f"Opened {title}")
    
    def on_tool_hidden(self, tool_name, title):

        self.show_tool_button.setText(f"Show {title}")
        self.show_tool_button.setVisible(True)
        signal_manager.statusbar_message.emit(f"{title} hidden")
    
    def on_tool_closed(self, tool_name):

        if tool_name in self.tool_dialogs:
            del self.tool_dialogs[tool_name]
        if self.active_tool_name == tool_name:
            self.active_tool_name = None
        self.show_tool_button.setVisible(False)
        signal_manager.statusbar_message.emit("Tool closed")
    
    def show_hidden_tool(self):
        if self.active_tool_name and self.active_tool_name in self.tool_dialogs:
            dialog = self.tool_dialogs[self.active_tool_name]
            dialog.show_dialog()
            self.show_tool_button.setVisible(False)
            signal_manager.statusbar_message.emit(f"Showing {dialog.title}")
        
    def toggle_repeat(self):
        self.is_repeat_enabled = not self.is_repeat_enabled
        prefs.prefs['repeat'] = self.is_repeat_enabled
        prefs.save()
        
        repeat_text = "Toggle Repeat: On" if self.is_repeat_enabled else "Toggle Repeat: Off"
        self.repeat_action.setText(repeat_text)
        signal_manager.statusbar_message.emit(f"Repeat: {'On' if self.is_repeat_enabled else 'Off'}")
        
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
        
    def update_console_menu(self, visible):

        if hasattr(self, 'show_console_dock_action'):
            self.show_console_dock_action.setChecked(visible)

    def toggle_console_dock(self, checked):
        if not hasattr(self, 'debug_console_dock') or self.debug_console_dock is None:
            self.debug_console_dock = DebugConsoleDock(self)
            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.debug_console_dock)
            if hasattr(self.debug_console_dock, 'visibilityChanged'):
                self.debug_console_dock.visibilityChanged.connect(self.update_console_menu)
        if checked:
            self.debug_console_dock.show()
            self.debug_console_dock.raise_()
        else:
            self.debug_console_dock.hide()

    def open_logs_viewer(self):
        dlg = LogsViewerDialog(self)
        dlg.exec()
        
    def apply_audio_device(self, device_index):

        try:

            if hasattr(self.player_widget, 'player') and self.player_widget.player:

                device_count = self.player_widget.player.get_devices()
                if device_index < device_count:
                    self.player_widget.player.set_device(device_index)
        except Exception as e:
            pass
        
        try:

            if hasattr(self.explorer_widget, '_player') and self.explorer_widget._player:

                device_count = self.explorer_widget._player.get_devices()
                if device_index < device_count:
                    self.explorer_widget._player.set_device(device_index)
        except Exception as e:
            pass
    
    def open_preferences(self):

        audio_devices = []
        try:
            if hasattr(self.player_widget, 'player') and self.player_widget.player:

                device_count = self.player_widget.player.get_devices()
                for i in range(device_count):
                    device_info = self.player_widget.player.get_device(i)
                    if device_info and device_info.name:
                        audio_devices.append(device_info.name)
        except Exception:
            pass
        
        dialog = PreferencesDialog(self, audio_devices, self.apply_audio_device)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            signal_manager.statusbar_message.emit("Preferences saved")
            
    def open_hotkeys(self):
        dialog = HotkeysDialog(self, reset_callback=self.reset_shortcuts_callback)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            signal_manager.statusbar_message.emit("Hotkeys updated")
            
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
            
    def has_active_tools(self):
        for tool_name, dialog in self.tool_dialogs.items():
            if dialog.is_tool_active():
                return True
        return False
    
    def get_active_tool_names(self):
        active_tools = []
        for tool_name, dialog in self.tool_dialogs.items():
            if dialog.is_tool_active():
                active_tools.append(dialog.title)
        return active_tools
    
    def confirm_close_with_active_tools(self):

        active_tools = self.get_active_tool_names()
        if not active_tools:
            return True
        
        tools_text = ", ".join(active_tools)
        reply = QMessageBox.question(
            self,
            "Active Tools",
            f"The following tools are currently active:\n{tools_text}\n\n"
            "Closing the application will stop these processes. Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        return reply == QMessageBox.StandardButton.Yes

    def close_application(self):
        if self.has_active_tools():
            if not self.confirm_close_with_active_tools():
                return
        
        self.save_window_state()

        for dialog in list(self.tool_dialogs.values()):
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

        if self.has_active_tools():
            if not self.confirm_close_with_active_tools():
                event.ignore()
                return
        
        if self.tray_icon and self.tray_icon.isVisible():
            event.ignore()
            self.hide_to_tray()
        else:
            self.close_application()
            event.accept()



    def cli_load_file(self, ipc_msg_data:dict[str, str]):
        self.play_file(ipc_msg_data["msg_data"])

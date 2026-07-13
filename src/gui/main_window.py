import os
import platform
import sys
import app_guard

from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter, 
    QMenuBar, QMenu, QStatusBar, QToolBar, QDockWidget, QLabel,
    QFileDialog, QInputDialog, QApplication, QMessageBox, QDialog,
    QPushButton
)
from PySide6.QtCore import Qt, Signal, QTimer, QUrl
from PySide6.QtGui import QAction, QIcon, QKeySequence

from app_db import UserFiles
from app_config import prefs
from EXPLORER.explorer_widget import ExplorerWidget
import app_db
import av_play
from player.player_widget import PlayerWidget
from playlist_manager.playlists_widget import PlaylistsWidget
from playlist_manager.playlist_selection_dialog import PlaylistSelectionDialog
from playlist_manager.playlist_create_dialog import PlaylistCreateDialog
from .recents_favorites import RecentsAndFavoritesWidget
from .dialogs.hotkeys_dialog import HotkeysDialog
from .dialogs.url_dialog import URLDialog
from .dialogs.prefs_dialog import PreferencesDialog
from utilities.util_gui import menuItem, messageBox
from utilities.media_utils import get_media_files_from_directory
from utilities.speech import speech_manager
from utilities import signal_manager
from player.utilities import ensure_ffmpeg_available
import utilities.vlc_bootstrap
from av_play import Playlist, PlaylistEntry
from utilities.formats import formats
from tools.batch_converter_ui import BatchConverterUI
from tools.extractor_ui import ExtractorUI
from tools.tag_editor_ui import TagEditorUI
from tools.thumbnail_generator_ui import ThumbnailGeneratorUI
from tools.subtitle_converter_ui import SubtitleConverterUI
from tools.subtitle_editor_ui import SubtitleEditorUI
from gui_controls.key_event_filter import ShortcutManager
from app_config import key_config
from app_constance.file_filter import file_filter
from .dialogs.tool_dialog import ToolDialog
from tools.logs_viewer_dialog import LogsViewerDialog
from tools.debug_console_dock import DebugConsoleDock
from media_providers.radio import RadioBrowserWidget
from media_providers.podcasts.feed_widget import FeedWidget
from app_constance.styles import SECTION_LABEL_STYLE
from utilities.session import dock_session
from app_config.toolbar_config import toolbar_config
from .dialogs.toolbar_customize_dialog import ToolbarCustomizeDialog


from .managers.menu_manager import MenuManager
from .managers.toolbar_manager import ToolbarManager
from .managers.dock_manager import DockManager
from .managers.tool_window_manager import ToolWindowManager
from .managers.playlist_handler import PlaylistHandler
from system_tray import SystemTrayIcon
from .dialogs.downloader_dialog import DownloaderDialog
from .dialogs.about_dialog import AboutDialog
from downloader.downloader import Downloader
from utilities.functions import get_restart_flag




class MainWindow(QMainWindow):
    fileOpened = Signal(str)
    urlOpened = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        self.setObjectName("mainWindow")
        
        self.user_db = app_db.user_db
        self.current_player_instance = None
        self._dialog_open = False
        self.tool_dialogs = {}
        self.active_tool_name = None
        self.show_tool_button: QPushButton

        # Downloader singleton
        self._shared_downloader: Optional[Downloader] = None
        self._downloader_dialog: Optional[DownloaderDialog] = None
        self.show_downloader_button: QPushButton
        
        self.radio_widget = None
        self.radio_dock = None
        self.podcast_widget = None
        self.podcast_dock = None
        

        self.explorer_dock: Optional[QDockWidget] = None
        self.player_dock: Optional[QDockWidget] = None
        self.playlists_dock: Optional[QDockWidget] = None
        self.recents_favorites_dock: Optional[QDockWidget] = None
        self.debug_console_dock: Optional[QDockWidget] = None
        
        self.repeat_action: Optional[QAction] = None
        self.show_recents_favorites_action: Optional[QAction] = None
        self.show_explorer_action: Optional[QAction] = None
        self.minimize_player_action: Optional[QAction] = None
        self.show_playlists_action: Optional[QAction] = None
        self.show_radio_action: Optional[QAction] = None
        self.show_podcast_action: Optional[QAction] = None
        self.show_console_dock_action: Optional[QAction] = None
        self.toolbar: Optional[QToolBar] = None

        self.focusable_widgets = []
        self.current_focus_index = -1
        self.tool_actions_map = {}
        self.customize_toolbar_action: Optional[QAction] = None
        
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
        

        self.menu_manager = MenuManager(self)
        self.toolbar_manager = ToolbarManager(self)
        self.dock_manager = DockManager(self)
        self.tool_manager = ToolWindowManager(self)
        self.tray = None
        
        self.setup_ui()
        self.setup_statusbar()
        self.menu_manager.setup_menus()
        self.toolbar_manager.setup_toolbar()
        self.dock_manager.setup_dock_widgets()
        self.dock_manager.restore_dock_session()
        self.tray = SystemTrayIcon(self)
        QApplication.instance()._tray_icon = self.tray.tray_icon
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
            hotkeys["Show/Hide player controls"]: self.toggle_player_shortcut,
            hotkeys["Toggle playlists"]: self.toggle_playlists_shortcut,
            hotkeys["Toggle podcasts"]: self.toggle_podcasts_shortcut,
            hotkeys["Toggle radio"]: self.toggle_radio_shortcut,
            hotkeys["Toggle recents/favorites"]: self.toggle_recents_favorites_shortcut,
            hotkeys["Focus playlists"]: self.focus_playlists,
            hotkeys["Focus podcasts"]: self.focus_podcasts,
            hotkeys["Focus radio"]: self.focus_radio,
            hotkeys["Focus recents/favorites"]: self.focus_recents_favorites,
            hotkeys["Hide window"]: self.hide_to_tray,
            hotkeys["Exit"]: self.close_application,
            hotkeys["Focus explorer"]: self.focus_explorer,
            hotkeys["Focus player"]: self.focus_player,
            hotkeys["Documentation"]: self.open_documentation,
            hotkeys["Hotkeys dialog"]: self.open_hotkeys,
            hotkeys["Prefrences Dialog"]: self.open_preferences,
            "F6": self.focus_next_widget,
            "Shift+F6": self.focus_previous_widget,
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

    def focus_explorer(self):
        if self.explorer_dock and self.explorer_dock.isVisible():
            if self.explorer_widget:
                self.explorer_widget.setFocus()

    def focus_player(self):
        if self.player_dock and self.player_dock.isVisible():
            self.player_widget.setFocus()

    def focus_playlists(self):
        if self.playlists_dock and self.playlists_dock.isVisible():
            if self.playlists_widget:
                self.playlists_widget.setFocus()

    def focus_podcasts(self):
        if self.podcast_dock and self.podcast_dock.isVisible():
            if self.podcast_widget:
                self.podcast_widget.setFocus()

    def focus_radio(self):
        if self.radio_dock and self.radio_dock.isVisible():
            if self.radio_widget:
                self.radio_widget.setFocus()

    def focus_recents_favorites(self):
        if self.recents_favorites_dock and self.recents_favorites_dock.isVisible():
            if self.recents_and_favorites_widget:
                self.recents_and_favorites_widget.setFocus()
    
    def toggle_explorer_shortcut(self):
        if self.show_explorer_action:
            self.show_explorer_action.trigger()  # type: ignore
    
    def toggle_player_shortcut(self):

        if self.minimize_player_action:
            self.minimize_player_action.trigger()  # type: ignore
    
    def toggle_playlists_shortcut(self):
        if self.playlists_dock:
            is_visible = self.playlists_dock.isVisible()
            self.playlists_dock.setVisible(not is_visible)
            if self.show_playlists_action:
                self.show_playlists_action.setChecked(not is_visible)
            if not is_visible and self.playlists_widget:
                self.playlists_widget.setFocus()
    
    def toggle_podcasts_shortcut(self):

        if self.podcast_dock:
            is_visible = self.podcast_dock.isVisible()
            self.podcast_dock.setVisible(not is_visible)
            if self.show_podcast_action:
                self.show_podcast_action.setChecked(not is_visible)
            if not is_visible and self.podcast_widget:
                self.podcast_widget.setFocus()
        elif self.show_podcast_action:
            # Create dock if it doesn't exist
            self.show_podcast_action.setChecked(True)
            self.show_podcast_action.trigger()
    
    def toggle_radio_shortcut(self):
        if self.radio_dock:
            is_visible = self.radio_dock.isVisible()
            self.radio_dock.setVisible(not is_visible)
            if self.show_radio_action:
                self.show_radio_action.setChecked(not is_visible)
            if not is_visible and self.radio_widget:
                self.radio_widget.setFocus()
        elif self.show_radio_action:
            # Create dock if it doesn't exist
            self.show_radio_action.setChecked(True)
            self.show_radio_action.trigger()
    
    def toggle_recents_favorites_shortcut(self):
        if self.recents_favorites_dock:
            is_visible = self.recents_favorites_dock.isVisible()
            self.recents_favorites_dock.setVisible(not is_visible)
            if self.show_recents_favorites_action:
                self.show_recents_favorites_action.setChecked(not is_visible)
            if not is_visible and self.recents_and_favorites_widget:
                self.recents_and_favorites_widget.setFocus()

    def setup_ui(self):
        self.setCentralWidget(None)
        
        self.recents_and_favorites_widget = RecentsAndFavoritesWidget(self.user_db)
        self.recents_and_favorites_widget.setObjectName("recentsAndFavoritesWidget")
        
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
            play_callback=self.play_playlist_track
        )
        self.playlists_widget.setObjectName("playlistsWidget")
        
    def setup_statusbar(self):
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("statusBar")
        self.status_bar.setSizeGripEnabled(True)
        self.status_bar.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setStatusBar(self.status_bar)
        
        self.status_label = QLabel(_("Ready"))
        self.status_label.setObjectName("statusLabel")
        self.status_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.status_bar.addWidget(self.status_label, 1)
        
        self.media_info_label = QLabel("")
        self.media_info_label.setObjectName("mediaInfoLabel")
        self.media_info_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.status_bar.addPermanentWidget(self.media_info_label)
        
        self.show_tool_button = QPushButton(_("Show Tool"))
        self.show_tool_button.setObjectName("showToolButton")
        self.show_tool_button.clicked.connect(self.show_hidden_tool)
        self.show_tool_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.show_tool_button.setVisible(False)
        self.status_bar.addPermanentWidget(self.show_tool_button)

        self.show_downloader_button = QPushButton(_("Show Downloader"))
        self.show_downloader_button.setObjectName("showDownloaderButton")
        self.show_downloader_button.clicked.connect(self._show_minimized_downloader)
        self.show_downloader_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.show_downloader_button.setVisible(False)
        self.status_bar.addPermanentWidget(self.show_downloader_button)
        
        self.status_bar.show()
        
        signal_manager.statusbar_message.connect(self._update_status_message)
        signal_manager.media_info_message.connect(self.media_info_label.setText)
        
    def connect_signals(self):
        self.recents_and_favorites_widget.itemRequested.connect(self.play_file)

        self.urlOpened.connect(self.player_widget.change_path)
        self.fileOpened.connect(self.player_widget.change_path)
        if self.explorer_dock and hasattr(self.explorer_dock, 'visibilityChanged'):
            self.explorer_dock.visibilityChanged.connect(self.menu_manager.update_explorer_menu)
        if self.playlists_dock and hasattr(self.playlists_dock, 'visibilityChanged'):
            self.playlists_dock.visibilityChanged.connect(self.menu_manager.update_playlists_menu)

        self.player_widget.playbackStateChanged.connect(self.menu_manager.update_media_playback_state)
        self.player_widget.muteStateChanged.connect(self.menu_manager.update_media_mute_state)
        self.player_widget.mediaAvailable.connect(self.menu_manager.update_media_available)
        self.player_widget.repeatModeChanged.connect(self.menu_manager.update_media_repeat_mode)
        self.player_widget.currentTrackIndexChanged.connect(self._on_current_track_index_changed)
        self.playlists_widget.playlist_selected.connect(lambda _p: self._apply_now_playing_highlight())
            
    def open_file_dialog(self):
        file_path, selected_filter = QFileDialog.getOpenFileName(
            self, _("Open Media File"), "", file_filter
        )
        if file_path:
            self.play_file(os.path.normpath(file_path))
    
    def open_folder_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(
            self, _("Open Folder"), ""
        )
        if folder_path:
            self.load_folder_as_playlist(folder_path)

    def open_playlist_dialog(self):
        file_path, selected_filter = QFileDialog.getOpenFileName(
            self,
            _("Open Playlist"),
            "",
            PlaylistsWidget.PLAYLIST_FILE_FILTER,
        )
        if file_path:
            self.play_file(file_path)
            
    def open_url_dialog(self):
        dialog = URLDialog(self)
        dialog.url_opened.connect(self.play_url)
        dialog.download_requested.connect(self.download_url)
        dialog.exec()

    def download_url(self, url: str):
        from player.url import is_url_supported
        from player.utilities import ensure_ytdlp_available

        downloader = self._get_shared_downloader()
        if is_url_supported(url):
            if not ensure_ytdlp_available(self):
                return
            downloader.add_ytdlp_download(url)
        else:
            downloader.add_download(url)

        self.open_downloader()

    def load_folder_as_playlist(self, folder_path: str):
        media_files = get_media_files_from_directory(folder_path, formats["audio"], formats["video"])
        
        if not media_files:
            QMessageBox.information(
                self, 
                _("No Media Found"), 
                f"{_('No supported media files were found in the selected folder:')}\n{folder_path}\n\n{_('Supported formats include audio and video files.')}"
            )
            return
        
        playlist = Playlist(title=os.path.basename(folder_path))
        for media_file in media_files:
            playlist.add_entry(PlaylistEntry(location=media_file, title=os.path.basename(media_file)))
        
        if media_files:
            self.player_widget.load_playlist(playlist, start_index=0)
            self.play_file(media_files[0])
            
    def play_file(self, file_path: str):
        signal_manager.statusbar_message.emit(f"{_("Loading:")} {os.path.basename(file_path)}")
        signal_manager.media_info_message.emit(file_path)
        self.add_to_recents(file_path)
        self.menu_manager.update_recent_files_menu()
        self.fileOpened.emit(file_path)
        self.close_media_action.setEnabled(True)

    def play_playlist_track(self, playlist: Playlist, start_index: int = 0):
        if playlist is None or len(playlist) == 0:
            return

        if start_index < 0 or start_index >= len(playlist):
            start_index = 0

        entry = playlist[start_index]
        signal_manager.statusbar_message.emit(
            _("Loading playlist: {title}").format(
                title=playlist.title or _("Untitled")
            )
        )
        signal_manager.media_info_message.emit(entry.location)
        self.add_to_recents(entry.location)
        self.menu_manager.update_recent_files_menu()
        self.player_widget.load_playlist(playlist, start_index=start_index, auto_play=True)
        self.close_media_action.setEnabled(True)
        
    def play_url(self, url: str):
        signal_manager.statusbar_message.emit(f"{_('Loading URL:')} {url}")
        signal_manager.media_info_message.emit(url)
        self.urlOpened.emit(url)
        self.close_media_action.setEnabled(True)
    
    def close_current_media(self):
        if self.player_widget and hasattr(self.player_widget, 'close_current_media'):
            self.player_widget.close_current_media()
            self.close_media_action.setEnabled(False)
        
    def add_to_favorites(self, file_path: str):
        self.recents_and_favorites_widget.add_favorite(file_path)
        
    def add_to_recents(self, file_path: str):
        self.recents_and_favorites_widget.add_recent(file_path)
        
    def add_to_playlist(self, file_path: str):

        playlist_manager = self.playlists_widget.playlist_manager
        
        if not playlist_manager.list_playlists():
            reply = QMessageBox.question(
                self, _("No Playlists"),
                _("No playlists exist. Would you like to create a new playlist?"),
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
            messageBox(_("Error"), _("Selected path is not a directory"))
            return
            
        audio_formats = [ext.lower() for ext in formats.get("audio", [])]
        video_formats = [ext.lower() for ext in formats.get("video", [])]
        
        media_files = get_media_files_from_directory(folder_path, audio_formats, video_formats)
        
        if not media_files:
            messageBox(_("No Media Files"), _("No supported media files found in the selected folder"))
            return
            
        folder_name = os.path.basename(folder_path)
        playlist_name = f"{_("Playlist from")} {folder_name}"
        
        playlist = Playlist(title=playlist_name)
        for file_path in media_files:
            entry = PlaylistEntry(location=file_path)
            playlist.add_entry(entry)
            
        self.playlists_widget.playlist_manager.playlists[playlist_name] = playlist
        self.playlists_widget.add_playlist_to_list(playlist_name)
        self.playlists_widget.save_playlists_data()
        

        self.player_widget.load_playlist(playlist, start_index=0, auto_play=True)

        signal_manager.statusbar_message.emit(
            _("Created and loaded playlist '{playlist_name}' with {track_count} tracks").format(
                playlist_name=playlist_name,
                track_count=len(media_files),
            )
        )
        
    def add_file_to_playlist(self, file_path: str, playlist_name: str):

        playlist = self.playlists_widget.playlist_manager.get_playlist(playlist_name)
        if playlist is not None:
            entry = PlaylistEntry(location=file_path)
            playlist.add_entry(entry)
            self.playlists_widget.save_playlists_data()
            
            filename = os.path.basename(file_path)
            signal_manager.statusbar_message.emit(
                _("Added '{filename}' to playlist '{playlist_name}'").format(
                    filename=filename,
                    playlist_name=playlist_name,
                )
            )
        else:
            messageBox(
                _("Error"),
                _("Playlist '{playlist_name}' not found").format(
                    playlist_name=playlist_name
                ),
            )
            
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
        signal_manager.statusbar_message.emit(
            _("Created new playlist '{name}'").format(name=name)
        )
        


    def _update_status_message(self, message: str):
        self.status_label.setText(message)
        
        if prefs.prefs["accessibility_feedback"]:
            # The following is a conditional check to disable Sapi onWindows until a solution is found for GUI freezing when Sapi speaks.
            if sys.platform == "win32" and speech_manager.current_driver() == "Sapi5":
                return

            speech_manager.output(message, prefs.prefs["tts_speech_interrupt"])

    def toggle_play_pause(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    state = self.player_widget.player.primary_instance.get_playback_state()
                    if state == av_play.AVPlaybackState.AV_STATE_PLAYING:
                        self.player_widget.player.primary_instance.pause()
                        signal_manager.statusbar_message.emit(_("Paused"))
                    else:
                        self.player_widget.player.primary_instance.play()
                        signal_manager.statusbar_message.emit(_("Playing"))
            except Exception as e:
                signal_manager.statusbar_message.emit(_("No media loaded"))
                
    def stop_playback(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    self.player_widget.player.primary_instance.stop()
                    signal_manager.statusbar_message.emit(_("Stopped"))
            except Exception as e:
                signal_manager.statusbar_message.emit(_("No media loaded"))
                
    def toggle_mute(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    instance = self.player_widget.player.primary_instance
                    if instance.get_mute_state() == av_play.AVMuteState.AV_AUDIO_UNMUTED:
                        instance.mute()
                    else:
                        instance.unmute()
                    signal_manager.statusbar_message.emit(_("Mute toggled"))
            except Exception as e:
                signal_manager.statusbar_message.emit(_("No media loaded"))
                
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
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    self.player_widget.player.previous()
                    signal_manager.statusbar_message.emit(_("Previous track"))
            except Exception:
                signal_manager.statusbar_message.emit(_("No media loaded"))

    def next_track(self):
        if hasattr(self.player_widget, 'player') and self.player_widget.player:
            try:
                if self.player_widget.player.primary_instance:
                    self.player_widget.player.next()
                    signal_manager.statusbar_message.emit(_("Next track"))
            except Exception:
                signal_manager.statusbar_message.emit(_("No media loaded"))

    def _on_current_track_index_changed(self, index: int):
        self._apply_now_playing_highlight(index)

    def _apply_now_playing_highlight(self, index: Optional[int] = None):
        if index is None and hasattr(self.player_widget, 'player') and self.player_widget.player:
            index = self.player_widget.player.get_current_track_index()

        displayed_playlist = self.playlists_widget.playlist_view.current_playlist
        playing_playlist = getattr(self.player_widget.player, 'current_playlist', None) if hasattr(self.player_widget, 'player') else None

        if displayed_playlist is not None and playing_playlist is not None and displayed_playlist is playing_playlist:
            self.playlists_widget.playlist_view.update_now_playing(index)
        else:
            self.playlists_widget.playlist_view.update_now_playing(None)

    def open_bookmarks_dialog(self):
        if hasattr(self.player_widget, 'player_controls'):
            self.player_widget.player_controls.show_bookmarks_dialog()

    def open_goto_dialog(self):
        if hasattr(self.player_widget, 'player_controls'):
            self.player_widget.player_controls.show_goto_dialog()

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
        if not ensure_ffmpeg_available(self, show_message=True, min_major=6):
            return
        self.open_tool_dialog("batch_converter", BatchConverterUI(), _("Batch Converter"))
        
    def open_extractor(self):
        if not ensure_ffmpeg_available(self, show_message=True, min_major=6):
            return
        self.open_tool_dialog("extractor", ExtractorUI(), _("Media Extractor"))
        
    def open_tag_editor(self):
        self.open_tool_dialog("tag_editor", TagEditorUI(), _("Tag Editor"))
        
    def open_thumbnail_generator(self):
        if not ensure_ffmpeg_available(self, show_message=True, min_major=6):
            return
        self.open_tool_dialog("thumbnail_generator", ThumbnailGeneratorUI(), _("Thumbnail Generator"))
    
    def open_subtitle_converter(self):
        self.open_tool_dialog("subtitle_converter", SubtitleConverterUI(), _("Subtitle Converter"))
    
    def open_subtitle_editor(self):
        self.open_tool_dialog("subtitle_editor", SubtitleEditorUI(), _("Subtitle Editor"))
        
    def open_tool_dialog(self, tool_name, tool_widget, title):

        if self.active_tool_name and self.active_tool_name != tool_name:
            if self.active_tool_name in self.tool_dialogs:
                active_dialog = self.tool_dialogs[self.active_tool_name]
                if active_dialog.isVisible() or self.show_tool_button.isVisible():
                    QMessageBox.information(
                        self,
                        _("Tool Already Open"),
                        _("'{title}' is already open. Please close it before opening another tool.").format(
                            title=active_dialog.title
                        ),
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
        signal_manager.statusbar_message.emit(
            _("Opened {title}").format(title=title)
        )
    
    def on_tool_hidden(self, tool_name, title):

        self.show_tool_button.setText(_("Show {title}").format(title=title))
        self.show_tool_button.setVisible(True)
        signal_manager.statusbar_message.emit(
            _("{title} hidden").format(title=title)
        )
    
    def on_tool_closed(self, tool_name):

        if tool_name in self.tool_dialogs:
            del self.tool_dialogs[tool_name]
        if self.active_tool_name == tool_name:
            self.active_tool_name = None
        self.show_tool_button.setVisible(False)
        signal_manager.statusbar_message.emit(_("Tool closed"))
    
    def show_hidden_tool(self):
        if self.active_tool_name and self.active_tool_name in self.tool_dialogs:
            dialog = self.tool_dialogs[self.active_tool_name]
            dialog.show_dialog()
            self.show_tool_button.setVisible(False)
            signal_manager.statusbar_message.emit(
                _("Showing {title}").format(title=dialog.title)
            )
        
    def toggle_repeat(self):
        if hasattr(self.player_widget, '_on_repeat_clicked'):
            self.player_widget._on_repeat_clicked()
        

    

    

    
    def focus_next_widget(self):
        self.dock_manager.update_focusable_widgets()
        if not self.focusable_widgets:
            return
        
        self.current_focus_index = (self.current_focus_index + 1) % len(self.focusable_widgets)
        self._focus_navigation_target(self.focusable_widgets[self.current_focus_index])
    
    def focus_previous_widget(self):
        self.dock_manager.update_focusable_widgets()
        if not self.focusable_widgets:
            return
        
        self.current_focus_index = (self.current_focus_index - 1) % len(self.focusable_widgets)
        self._focus_navigation_target(self.focusable_widgets[self.current_focus_index])

    def _focus_navigation_target(self, widget):
        if widget is None:
            return

        if widget is self.menuBar():
            widget.setFocus()
            first_action = next((action for action in widget.actions() if action.isVisible()), None)
            if first_action is not None:
                widget.setActiveAction(first_action)
            return

        if widget is self.toolbar:
            widget.setFocus()
            toolbar_actions = [action for action in widget.actions() if action.isVisible() and not action.isSeparator()]
            if toolbar_actions:
                toolbar_widget = widget.widgetForAction(toolbar_actions[0])
                if toolbar_widget is not None:
                    toolbar_widget.setFocus()
            return

        if widget is self.status_bar:
            widget.setFocus()
            if self.show_tool_button.isVisible():
                self.show_tool_button.setFocus()
            elif self.show_downloader_button.isVisible():
                self.show_downloader_button.setFocus()
            elif self.media_info_label.isVisible():
                self.media_info_label.setFocus()
            else:
                self.status_label.setFocus()
            return

        widget.setFocus()
    


    def open_logs_viewer(self):
        dlg = LogsViewerDialog(self)
        dlg.exec()
        
    def _find_device_index(self, player, device_name: str) -> int:
        if not device_name:
            return -1
        try:
            device_count = player.get_devices()
            for i in range(device_count):
                device_info = player.get_device(i)
                if device_info and device_info.name == device_name:
                    return i
        except Exception:
            pass
        return -1

    def apply_audio_device(self, device_name: str):

        try:

            if hasattr(self.player_widget, 'player') and self.player_widget.player:

                idx = self._find_device_index(self.player_widget.player, device_name)
                if idx >= 0:
                    self.player_widget.player.set_device(idx)
        except Exception as e:
            pass

        try:

            if hasattr(self.explorer_widget, '_player') and self.explorer_widget._player:

                idx = self._find_device_index(self.explorer_widget._player, device_name)
                if idx >= 0:
                    self.explorer_widget._player.set_device(idx)
        except Exception as e:
            pass

    def open_preferences(self):

        if self._dialog_open:
            return
        self._dialog_open = True

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
        dialog.finished.connect(lambda: setattr(self, '_dialog_open', False))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            signal_manager.statusbar_message.emit(_("Preferences saved"))
            
    def open_hotkeys(self):
        if self._dialog_open:
            return
        self._dialog_open = True
        dialog = HotkeysDialog(self, reset_callback=self.reset_shortcuts_callback)
        dialog.finished.connect(lambda: setattr(self, '_dialog_open', False))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            signal_manager.statusbar_message.emit(_("Hotkeys updated"))

    # ------------------------------------------------------------------
    # About & Options menu actions
    # ------------------------------------------------------------------
    def open_about_dialog(self):
        dlg = AboutDialog(self)
        dlg.exec()

    def open_documentation(self):
        """Open the local documentation in the default web browser."""
        import webbrowser
        from pathlib import Path
        from utilities.functions import get_parent_dir, is_dev_mode
        from PySide6.QtWidgets import QMessageBox

        base = Path(get_parent_dir())
        lang = prefs.prefs.get("language", "en")
        if is_dev_mode():
            doc_path = base / "docs" / "build" / lang / "documentation.html"
        else:
            doc_path = base / "docs" / lang / "documentation.html"

        if not doc_path.exists():
            doc_path = base / "docs" / ("build" if is_dev_mode() else "") / "en" / "documentation.html"

        if doc_path.exists():
            webbrowser.open(doc_path.as_uri())
        else:
            QMessageBox.information(
                self,
                _("Documentation Not Found"),
                _("The documentation could not be found.\n\nPlease visit the project website for help."),
            )

    def check_for_updates(self):
        from update_checker import UpdateChecker
        checker = UpdateChecker.instance(self)
        checker.check_now(silent=False)

    def open_utility_download_dialog(self):
        from util_download_center import UtilityDownloadDialog
        dlg = UtilityDownloadDialog(
            downloader=self._get_shared_downloader(), parent=self
        )
        dlg.exec()

    # ------------------------------------------------------------------
    # Singleton downloader dialog management
    # ------------------------------------------------------------------
    def _get_shared_downloader(self) -> Downloader:
        """Return the singleton Downloader, creating it on first call."""
        if self._shared_downloader is None:
            from utilities.functions import get_app_path
            import os
            dest = os.path.join(get_app_path(), "downloads")
            self._shared_downloader = Downloader(destination=dest)
        return self._shared_downloader

    def open_downloader(self):
        """Open (or raise) the singleton downloader dialog."""
        if self._downloader_dialog is not None:
            # Dialog was minimized or still alive – bring it back
            self._downloader_dialog.show_dialog()
            self.show_downloader_button.setVisible(False)
            signal_manager.statusbar_message.emit(_("Download Manager opened"))
            return

        # First time (or after close) – create fresh dialog
        dlg = DownloaderDialog(self._get_shared_downloader(), parent=self)
        dlg.dialog_hidden.connect(self._on_downloader_hidden)
        dlg.dialog_closed.connect(self._on_downloader_closed)
        self._downloader_dialog = dlg
        dlg.show_dialog()
        self.show_downloader_button.setVisible(False)
        signal_manager.statusbar_message.emit(_("Download Manager opened"))

    def _on_downloader_hidden(self):
        """Called when dialog hides itself (Minimize button)."""
        self.show_downloader_button.setVisible(True)
        signal_manager.statusbar_message.emit(_("Download Manager minimized"))

    def _on_downloader_closed(self):
        """Called when dialog is fully closed so it can be re-created next time."""
        self._downloader_dialog = None
        self.show_downloader_button.setVisible(False)
        signal_manager.statusbar_message.emit(_("Download Manager closed"))

    def _show_minimized_downloader(self):
        """Status-bar button: show the minimized dialog."""
        if self._downloader_dialog is not None:
            self._downloader_dialog.show_dialog()
            self.show_downloader_button.setVisible(False)
            signal_manager.statusbar_message.emit(_("Download Manager restored"))
            
    def hide_to_tray(self):
        if self.tray:
            self.tray.hide_window_to_tray()
        else:
            self.showMinimized()
            
    def toggle_window_visibility(self):
        if self.tray:
            self.tray.toggle_window_visibility()
        else:
            if self.isVisible() and not self.isMinimized():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()
    
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
        
        tools_text = "\n".join(f"• {tool}" for tool in active_tools)
        reply = QMessageBox.question(
            self,
            _("Active Tools"),
            _("The following tools are currently active:\n{tools}\n\nClosing the application will stop these processes. Do you want to continue?").format(
                tools=tools_text
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        return reply == QMessageBox.StandardButton.Yes

    def close_application(self):
        if not get_restart_flag() and self.has_active_tools():
            if not self.confirm_close_with_active_tools():
                return
        
        self.save_window_state()
        
        if self.tray:
            self.tray.cleanup()
        
        for dialog in list(self.tool_dialogs.values()):
            dialog.close()
        
        QApplication.quit()
        
    def save_window_state(self):
        prefs.prefs['window_geometry'] = self.saveGeometry().data().hex()
        prefs.prefs['window_state'] = self.saveState().data().hex()
        prefs.prefs['player_visible'] = self.player_dock.isVisible() if self.player_dock else True
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

        if self.player_dock:
            self.player_dock.setVisible(prefs.prefs.get('player_visible', True))
        if self.minimize_player_action:
            self.minimize_player_action.setChecked(not (self.player_dock.isVisible() if self.player_dock else True))
                
    def closeEvent(self, event):

        is_restarting = get_restart_flag()

        if not is_restarting and self.has_active_tools():
            if not self.confirm_close_with_active_tools():
                event.ignore()
                return
        
        self.dock_manager.save_dock_session()
        
        if self.radio_widget and hasattr(self.radio_widget, 'closeEvent'):
            self.radio_widget.closeEvent(event)
        
        if self.podcast_widget and hasattr(self.podcast_widget, 'close'):
            self.podcast_widget.close()
        
        if self.tray and self.tray.is_available() and not is_restarting:
            event.ignore()
            self.hide_to_tray()
        else:
            self.close_application()
            event.accept()
            event.accept()



    def cli_load_file(self, ipc_msg_data:dict[str, str]):
        path = ipc_msg_data.get("msg_data", "")
        if path:
            self.load_external_path(path)

    def load_external_path(self, path: str):
        import av_play
        if av_play.is_url(path):
            self.play_url(path)
        elif os.path.isdir(path):
            self.load_folder_as_playlist(path)
        elif os.path.isfile(path):
            self.play_file(path)
        else:
            signal_manager.statusbar_message.emit(_("Unrecognized path: {path}").format(path=path))

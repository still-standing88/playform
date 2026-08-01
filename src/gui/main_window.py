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
import media_core.av_play as av_play
from player.player_widget import PlayerWidget
from playlist_manager.playlists_widget import PlaylistsWidget
from .recents_favorites import RecentsAndFavoritesWidget
from .dialogs.hotkeys_dialog import HotkeysDialog
from .dialogs.url_dialog import URLDialog
from .dialogs.prefs_dialog import PreferencesDialog
from utilities.util_gui import menuItem
from utilities.speech import speech_manager
from utilities import signal_manager
import utilities.mpv_bootstrap
from media_core.av_play import Playlist, PlaylistEntry
from gui_controls.key_event_filter import ShortcutManager
from app_constance.file_filter import file_filter
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
from .managers.focus_navigation_manager import FocusNavigationManager
from .managers.global_playback_actions import GlobalPlaybackActions
from .managers.singleton_dialogs_manager import SingletonDialogsManager
from .managers.shortcuts_manager import MainWindowShortcuts
from system_tray import SystemTrayIcon
from .dialogs.downloader_dialog import DownloaderDialog
from .dialogs.about_dialog import AboutDialog
from .dialogs.catalog_progress_dialog import CatalogProgressDialog
from downloader.downloader import Downloader
from app_db.catalog_worker import CatalogWorker
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

        # Catalog worker singleton
        self._catalog_worker: Optional[CatalogWorker] = None
        self._catalog_dialog: Optional[CatalogProgressDialog] = None
        self.show_catalog_button: QPushButton

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
        # A flat 1200x800 floor is bigger than plenty of real screens (e.g.
        # 1366x768 laptops, ~720px tall after the taskbar), and Qt then
        # refuses to ever shrink the window below it - this is what was
        # pushing the status bar off the bottom of the screen. This initial
        # value is just a reasonable pre-layout guess; restore_window_state()
        # (called at the end of __init__) schedules clamp_to_screen(), which
        # owns the real, frame-aware, screen-relative version of this floor
        # and corrects it within one event loop tick regardless.
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        self._shortcut_manager = ShortcutManager(self)
        

        self.menu_manager = MenuManager(self)
        self.toolbar_manager = ToolbarManager(self)
        self.dock_manager = DockManager(self)
        self.tool_manager = ToolWindowManager(self)
        self.playlist_handler = PlaylistHandler(self)
        self.focus_nav = FocusNavigationManager(self)
        self.global_actions = GlobalPlaybackActions(self)
        self.singleton_dialogs = SingletonDialogsManager(self)
        self.shortcuts = MainWindowShortcuts(self)
        self.tray = None
        
        self.setup_ui()
        self.setup_statusbar()
        self.menu_manager.setup_menus()
        self.setup_menubar_indicators()
        self.toolbar_manager.setup_toolbar()
        self.dock_manager.setup_dock_widgets()
        self.toolbar_manager.setup_panels_toolbar()
        self.dock_manager.restore_dock_session()
        self.tray = SystemTrayIcon(self)
        QApplication.instance()._tray_icon = self.tray.tray_icon
        self.connect_signals()
        self.set_shortcuts()

        self.restore_window_state()
        self.toolbar_manager.ensure_panels_toolbar_break()

    def set_shortcuts(self):
        self.shortcuts.setup()

    def reset_shortcuts(self):
        self.shortcuts.reset_shortcuts()

    def reset_shortcuts_callback(self):
        self.shortcuts.reset_shortcuts_callback()

    def setup_ui(self):
        # QMainWindow's internal layout math for reserving the status bar's
        # row gets unreliable with no central widget at all - docks (e.g. the
        # bottom Player dock together with a side dock) can then visually
        # overlap/cover the status bar. A zero-size placeholder anchors the
        # layout without taking any space away from the dock areas.
        placeholder = QWidget()
        placeholder.setFixedSize(0, 0)
        self.setCentralWidget(placeholder)

        self.recents_and_favorites_widget = RecentsAndFavoritesWidget(self.user_db)
        self.recents_and_favorites_widget.setObjectName("recentsAndFavoritesWidget")
        
        self.explorer_widget = ExplorerWidget(
            self.user_db,
            parent=self,
            favorites_callback=self.add_to_favorites,
            open_callback=self.play_file,
            recent_callback=self.add_to_recents,
            playlist_callback=self.add_to_playlist,
            create_playlist_callback=self.create_playlist_from_folder,
            catalog_folder_callback=self.catalog_folder
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
        # Without an explicit floor, this has no protected minimum the way
        # the accordion/video placeholder now do - when the window's true
        # combined minimum height exceeds the screen (clamp_to_screen()
        # still has to fit the window on-screen regardless), something has
        # to be squeezed below its stated minimum, and this had the least
        # protection of anything competing for that space.
        self.status_bar.setMinimumHeight(24)
        self.setStatusBar(self.status_bar)
        
        self.status_label = QLabel(_("Ready"))
        self.status_label.setObjectName("statusLabel")
        self.status_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.status_bar.addWidget(self.status_label, 1)

        self.media_info_label = QLabel("")
        self.media_info_label.setObjectName("mediaInfoLabel")
        self.media_info_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.status_bar.addPermanentWidget(self.media_info_label)

        self.status_bar.show()

        signal_manager.statusbar_message.connect(self._update_status_message)
        signal_manager.media_info_message.connect(self.media_info_label.setText)

    def setup_menubar_indicators(self):
        """"Restore minimized" indicators, in the menu bar's own corner
        instead of the status bar. The status bar is the first thing
        squeezed off-screen once two docks together exceed the screen's
        available height (see setup_statusbar()'s status_bar minimum-height
        comment) - the menu bar row doesn't compete for that same space, so
        these stay reachable exactly when the status bar wouldn't be."""
        self.menubar_indicators = QWidget()
        self.menubar_indicators.setObjectName("menubarIndicators")
        indicators_layout = QHBoxLayout(self.menubar_indicators)
        indicators_layout.setContentsMargins(0, 0, 4, 0)
        indicators_layout.setSpacing(4)

        self.show_tool_button = QPushButton(_("Show Tool"))
        self.show_tool_button.setObjectName("showToolButton")
        self.show_tool_button.clicked.connect(self.show_hidden_tool)
        self.show_tool_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.show_tool_button.setVisible(False)
        indicators_layout.addWidget(self.show_tool_button)

        self.show_downloader_button = QPushButton(_("Show Downloader"))
        self.show_downloader_button.setObjectName("showDownloaderButton")
        self.show_downloader_button.clicked.connect(self._show_minimized_downloader)
        self.show_downloader_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.show_downloader_button.setVisible(False)
        indicators_layout.addWidget(self.show_downloader_button)

        self.show_catalog_button = QPushButton(_("Show Cataloging"))
        self.show_catalog_button.setObjectName("showCatalogButton")
        self.show_catalog_button.clicked.connect(self._show_minimized_catalog)
        self.show_catalog_button.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.show_catalog_button.setVisible(False)
        indicators_layout.addWidget(self.show_catalog_button)

        self.menuBar().setCornerWidget(self.menubar_indicators, Qt.Corner.TopRightCorner)
        
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
        from player.util.url import is_url_supported

        if is_url_supported(url):
            QMessageBox.warning(
                self,
                _("Unsupported Download"),
                _("Downloading from this type of link isn't supported yet."),
            )
            return

        downloader = self._get_shared_downloader()
        downloader.add_download(url)
        self.open_downloader()

    def load_folder_as_playlist(self, folder_path: str):
        self.playlist_handler.load_folder_as_playlist(folder_path)


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
        self.playlist_handler.add_to_playlist(file_path)

    def create_playlist_from_folder(self, folder_path: str):
        self.playlist_handler.create_playlist_from_folder(folder_path)

    def add_file_to_playlist(self, file_path: str, playlist_name: str):
        self.playlist_handler.add_file_to_playlist(file_path, playlist_name)

    def create_new_playlist_with_file(self, file_path: str):
        self.playlist_handler.create_new_playlist_with_file(file_path)

    def handle_new_playlist_created(self, name: str, playlist: Playlist):
        self.playlist_handler.handle_new_playlist_created(name, playlist)




    def _update_status_message(self, message: str):
        self.status_label.setText(message)
        
        if prefs.prefs["accessibility_feedback"]:
            # The following is a conditional check to disable Sapi onWindows until a solution is found for GUI freezing when Sapi speaks.
            if sys.platform == "win32" and speech_manager.current_driver() == "Sapi5":
                return

            speech_manager.output(message, prefs.prefs["tts_speech_interrupt"])

    def toggle_play_pause(self):
        self.global_actions.toggle_play_pause()

    def stop_playback(self):
        self.global_actions.stop_playback()

    def toggle_mute(self):
        self.global_actions.toggle_mute()

    def seek_forward(self):
        self.global_actions.seek_forward()

    def seek_backward(self):
        self.global_actions.seek_backward()

    def previous_track(self):
        self.global_actions.previous_track()

    def next_track(self):
        self.global_actions.next_track()

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
        self.global_actions.open_bookmarks_dialog()

    def open_goto_dialog(self):
        self.global_actions.open_goto_dialog()

    def volume_down(self):
        self.global_actions.volume_down()

    def volume_up(self):
        self.global_actions.volume_up()

    def show_hidden_tool(self):
        if self.active_tool_name and self.active_tool_name in self.tool_dialogs:
            dialog = self.tool_dialogs[self.active_tool_name]
            dialog.show_dialog()
            self.show_tool_button.setVisible(False)
            signal_manager.statusbar_message.emit(
                _("Showing {title}").format(title=dialog.title)
            )
        
    def toggle_repeat(self):
        self.global_actions.toggle_repeat()

    def focus_next_widget(self):
        self.focus_nav.focus_next_widget()

    def focus_previous_widget(self):
        self.focus_nav.focus_previous_widget()

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

    def zoom_in(self):
        self._adjust_ui_zoom(1)

    def zoom_out(self):
        self._adjust_ui_zoom(-1)

    def _adjust_ui_zoom(self, delta):
        import app_init
        current = prefs.prefs.get("ui_zoom_level", 0)
        new_level = app_init.apply_ui_zoom(QApplication.instance(), current + delta)
        prefs.prefs["ui_zoom_level"] = new_level
        prefs.save()

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

    def _get_shared_downloader(self) -> Downloader:
        return self.singleton_dialogs.get_shared_downloader()

    def open_downloader(self):
        self.singleton_dialogs.open_downloader()

    def _show_minimized_downloader(self):
        self.singleton_dialogs.show_minimized_downloader()

    def catalog_folder(self, path: str):
        self.singleton_dialogs.catalog_folder(path)

    def rebuild_catalog(self):
        self.singleton_dialogs.rebuild_catalog()

    def clear_explorer_search_history(self):
        """Clear both the persisted search history and the live Explorer
        search box's dropdown, if it's currently constructed."""
        if self.explorer_widget is not None:
            self.explorer_widget.clear_search_history()

    def _show_minimized_catalog(self):
        self.singleton_dialogs.show_minimized_catalog()

    def hide_to_tray(self):
        # Keep the persisted floating/geometry blob fresh on every hide, not
        # just on a true exit - otherwise it only reflects whatever the
        # layout was the last time the user actually quit via close_application(),
        # which can drift out of sync with dock_session.json's (always-fresh)
        # visibility flags across a full app restart.
        self.save_window_state()
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
        # QApplication.quit() below triggers closeEvent() on every visible
        # top-level window, including this one - and closeEvent(), when the
        # tray is no longer available (we just cleaned it up), falls through
        # to calling close_application() again. That second pass used to
        # re-save dock state after quit() had already un-floated/hidden any
        # floating docks via their own closeEvent(), silently clobbering the
        # correct save from this call with the torn-down state. Guard against
        # running this more than once per real quit.
        if getattr(self, '_quitting', False):
            return

        if not get_restart_flag() and self.has_active_tools():
            if not self.confirm_close_with_active_tools():
                return

        self._quitting = True

        # This is also the exit path for the tray "Exit" action, the File
        # menu's Exit action, and the Exit hotkey - none of which go through
        # closeEvent(), which was the only place saving dock_session.json.
        # Any dock created lazily from that file (Radio, Podcast) would never
        # get recreated on the next launch if the session was closed this
        # way, since restoreState() can't restore a dock widget that was
        # never added back in the first place.
        self.dock_manager.save_dock_session()
        self.save_window_state()

        if self.tray:
            self.tray.cleanup()
        
        for dialog in list(self.tool_dialogs.values()):
            dialog.close()
        
        QApplication.quit()
        
    def save_window_state(self):
        self.dock_manager.save_window_state()

    def showEvent(self, event):
        super().showEvent(event)
        # restore_dock_session()'s dock.setVisible(True) calls happen inside
        # __init__, before this top-level window has ever been shown - a
        # child widget's isVisible() reflects the whole ancestor chain, so
        # it still reports False right after setVisible(True) until the
        # window itself is actually shown. clamp_to_screen()'s first pass
        # (scheduled from restore_window_state(), also called from
        # __init__) runs before that, so it undercounts which docks are
        # really visible and nothing re-checks once they are. Re-running it
        # here, once the window is genuinely on-screen, closes that gap.
        self.dock_manager._schedule_clamp_to_screen()

    def restore_window_state(self):
        self.dock_manager.restore_window_state()

    def show_or_maximize(self):
        # A totally fresh install has no saved window_geometry to restore,
        # so it falls back to the hardcoded resize(1400, 900) from __init__ -
        # which has no screen-fit clamping at all, unlike restoreGeometry()
        # (see restore_window_state()/clamp_to_screen()), and could already
        # exceed a smaller screen before any dock has even been toggled.
        if getattr(self.dock_manager, 'had_saved_geometry', False):
            self.show()
            return

        # Not self.showMaximized() - that's a documented Qt bug (QTBUG-38756):
        # called from code rather than by the user clicking the maximize
        # button, it can miscalculate available space relative to the
        # taskbar, pushing bottom content like the status bar behind it even
        # though the window otherwise looks maximized. Simulating the same
        # full-screen appearance manually, the same frame-aware way
        # clamp_to_screen() already does, sidesteps the bug entirely.
        self.show()
        QApplication.processEvents()
        screen = self.screen()
        if screen is None:
            self.showMaximized()
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        geo = self.geometry()
        frame_extra_w = frame.width() - geo.width()
        frame_extra_h = frame.height() - geo.height()
        self.resize(available.width() - frame_extra_w, available.height() - frame_extra_h)
        self.move(available.left(), available.top())

    def closeEvent(self, event):
        # QApplication.quit() (from close_application()) re-triggers this
        # very closeEvent() on its way out - without this guard, the
        # save_dock_session() call below would run a second time here, after
        # quit() has already un-floated/hidden floating docks via their own
        # closeEvent(), overwriting the correct save from close_application()
        # with that torn-down state.
        if getattr(self, '_quitting', False):
            event.accept()
            return

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
        import media_core.av_play as av_play
        if av_play.is_url(path):
            self.play_url(path)
        elif os.path.isdir(path):
            self.load_folder_as_playlist(path)
        elif os.path.isfile(path):
            self.play_file(path)
        else:
            signal_manager.statusbar_message.emit(_("Unrecognized path: {path}").format(path=path))

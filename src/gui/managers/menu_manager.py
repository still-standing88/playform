from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction, QKeySequence
import os
from app_config import key_config
from utilities.icon_loader import load_icon

class MenuManager:

    
    def __init__(self, main_window):
        self.main_window = main_window
        
    def setup_menus(self):
        menubar = self.main_window.menuBar()
        menubar.setObjectName("menuBar")
        
        self.main_window.file_menu = menubar.addMenu(_("&File"))
        self.main_window.file_menu.setObjectName("fileMenu")
        self.setup_file_menu()
        
        self.main_window.media_menu = menubar.addMenu(_("&Media"))
        self.main_window.media_menu.setObjectName("mediaMenu")
        self.setup_media_menu()
        
        self.main_window.view_menu = menubar.addMenu(_("&View"))
        self.main_window.view_menu.setObjectName("viewMenu")
        self.setup_view_menu()
        
        self.main_window.tools_menu = menubar.addMenu(_("&Tools"))
        self.main_window.tools_menu.setObjectName("toolsMenu")
        self.setup_tools_menu()
        
        self.main_window.options_menu = menubar.addMenu(_("&Options"))
        self.main_window.options_menu.setObjectName("optionsMenu")

        self.main_window.about_menu = self.main_window.options_menu
        self.setup_options_menu()
        
    def setup_file_menu(self):
        self.main_window.open_menu = QMenu(_("&Open"), self.main_window)

        self.main_window.open_file_action = QAction(_("&Open File..."), self.main_window)
        self.main_window.open_file_action.triggered.connect(self.main_window.open_file_dialog)
        self.main_window.open_menu.addAction(self.main_window.open_file_action)
        
        self.main_window.open_folder_action = QAction(_("Open &Folder..."), self.main_window)
        self.main_window.open_folder_action.setIcon(load_icon("explorer.svg"))
        self.main_window.open_folder_action.triggered.connect(self.main_window.open_folder_dialog)
        self.main_window.open_menu.addAction(self.main_window.open_folder_action)

        self.main_window.open_playlist_action = QAction(_("Open &Playlist..."), self.main_window)
        self.main_window.open_playlist_action.triggered.connect(self.main_window.open_playlist_dialog)
        self.main_window.open_menu.addAction(self.main_window.open_playlist_action)
        
        self.main_window.open_url_action = QAction(_("Open &URL..."), self.main_window)
        self.main_window.open_url_action.triggered.connect(self.main_window.open_url_dialog)
        self.main_window.open_menu.addAction(self.main_window.open_url_action)

        self.main_window.file_menu.addMenu(self.main_window.open_menu)

        self.main_window.file_menu.addSeparator()
        
        self.main_window.close_media_action = QAction(_("&Close Media"), self.main_window)
        self.main_window.close_media_action.triggered.connect(self.main_window.close_current_media)
        self.main_window.close_media_action.setEnabled(False)
        self.main_window.file_menu.addAction(self.main_window.close_media_action)
        
        self.main_window.file_menu.addSeparator()
        
        self.main_window.recent_files_menu = QMenu(_("&Recent Files"), self.main_window)
        self.main_window.file_menu.addMenu(self.main_window.recent_files_menu)
        self.update_recent_files_menu()
        
        self.main_window.file_menu.addSeparator()
        
        self.main_window.minimize_action = QAction(_("&Minimize to Taskbar"), self.main_window)
        self.main_window.minimize_action.triggered.connect(self.main_window.hide_to_tray)
        self.main_window.file_menu.addAction(self.main_window.minimize_action)
        
        self.main_window.exit_action = QAction(_("&Exit"), self.main_window)
        self.main_window.exit_action.triggered.connect(self.main_window.close_application)
        self.main_window.file_menu.addAction(self.main_window.exit_action)
        
    def setup_media_menu(self):
        self.main_window.play_pause_action = QAction(_("&Play/Pause"), self.main_window)
        self.main_window.play_pause_action.setCheckable(True)
        self.main_window.play_pause_action.triggered.connect(self.main_window.toggle_play_pause)
        self.main_window.media_menu.addAction(self.main_window.play_pause_action)
        
        self.main_window.stop_action = QAction(_("&Stop"), self.main_window)
        self.main_window.stop_action.setIcon(load_icon("stop.svg"))
        self.main_window.stop_action.triggered.connect(self.main_window.stop_playback)
        self.main_window.media_menu.addAction(self.main_window.stop_action)
        
        self.main_window.media_menu.addSeparator()
        
        self.main_window.mute_action = QAction(_("&Mute/Unmute"), self.main_window)
        self.main_window.mute_action.setCheckable(True)
        self.main_window.mute_action.setIcon(load_icon("volume.svg"))
        self.main_window.mute_action.triggered.connect(self.main_window.toggle_mute)
        self.main_window.media_menu.addAction(self.main_window.mute_action)
        
        self.main_window.media_menu.addSeparator()
        
        self.main_window.forward_action = QAction(_("&Forward"), self.main_window)
        self.main_window.forward_action.triggered.connect(self.main_window.seek_forward)
        self.main_window.media_menu.addAction(self.main_window.forward_action)
        
        self.main_window.backward_action = QAction(_("&Backward"), self.main_window)
        self.main_window.backward_action.triggered.connect(self.main_window.seek_backward)
        self.main_window.media_menu.addAction(self.main_window.backward_action)
        
        self.main_window.media_menu.addSeparator()
        
        self.main_window.previous_action = QAction(_("&Previous"), self.main_window)
        self.main_window.previous_action.triggered.connect(self.main_window.previous_track)
        self.main_window.media_menu.addAction(self.main_window.previous_action)
        
        self.main_window.next_action = QAction(_("&Next"), self.main_window)
        self.main_window.next_action.triggered.connect(self.main_window.next_track)
        self.main_window.media_menu.addAction(self.main_window.next_action)
        
        self.main_window.media_menu.addSeparator()
        
        self.main_window.repeat_action = QAction(_("Toggle &Repeat: Off"), self.main_window)
        self.main_window.repeat_action.triggered.connect(self.main_window.toggle_repeat)
        self.main_window.media_menu.addAction(self.main_window.repeat_action)

        self.main_window.media_menu.addSeparator()

        self.main_window.bookmarks_action = QAction(_("&Bookmarks..."), self.main_window)
        self.main_window.bookmarks_action.setIcon(load_icon("bookmarks.svg"))
        self.main_window.bookmarks_action.triggered.connect(self.main_window.open_bookmarks_dialog)
        self.main_window.media_menu.addAction(self.main_window.bookmarks_action)

        self.main_window.goto_action = QAction(_("&Go to Time..."), self.main_window)
        self.main_window.goto_action.setIcon(load_icon("seek.svg"))
        self.main_window.goto_action.triggered.connect(self.main_window.open_goto_dialog)
        self.main_window.media_menu.addAction(self.main_window.goto_action)

        self._set_media_actions_enabled(False)

        from app_config import prefs
        self.update_media_repeat_mode(prefs.prefs.get("repeat_mode", 0))
        
    def _set_media_actions_enabled(self, enabled: bool):
        for name in ("play_pause_action", "stop_action", "mute_action",
                     "forward_action", "backward_action",
                     "previous_action", "next_action", "repeat_action",
                     "bookmarks_action", "goto_action"):
            action = getattr(self.main_window, name, None)
            if action:
                action.setEnabled(enabled)

    def update_media_playback_state(self, is_playing: bool):
        self.main_window.play_pause_action.setChecked(is_playing)

    def update_media_mute_state(self, is_muted: bool):
        self.main_window.mute_action.setChecked(is_muted)

    def update_media_available(self, available: bool):
        self._set_media_actions_enabled(available)
        if not available:
            self.main_window.play_pause_action.setChecked(False)
            self.main_window.mute_action.setChecked(False)

    def update_media_repeat_mode(self, mode: int):
        labels = {0: _("Toggle &Repeat: Off"), 1: _("Toggle &Repeat: All"), 2: _("Toggle &Repeat: One")}
        text = labels.get(mode, labels[0])
        if self.main_window.repeat_action:
            self.main_window.repeat_action.setText(text)
        
    def setup_view_menu(self):
        self.main_window.zoom_in_action = QAction(_("Zoom &In"), self.main_window)
        self.main_window.zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.main_window.zoom_in_action.triggered.connect(self.main_window.zoom_in)
        self.main_window.view_menu.addAction(self.main_window.zoom_in_action)

        self.main_window.zoom_out_action = QAction(_("Zoom &Out"), self.main_window)
        self.main_window.zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.main_window.zoom_out_action.triggered.connect(self.main_window.zoom_out)
        self.main_window.view_menu.addAction(self.main_window.zoom_out_action)

        self.main_window.view_menu.addSeparator()

        self.main_window.minimize_player_action = QAction(_("&Minimize Player"), self.main_window)
        self.main_window.minimize_player_action.setCheckable(True)
        self.main_window.minimize_player_action.triggered.connect(self.main_window.dock_manager.toggle_player_minimize)
        self.main_window.view_menu.addAction(self.main_window.minimize_player_action)

        self.main_window.view_menu.addSeparator()

        # Panels toolbar already surfaces show/hide (+ float) for every pane;
        # the individual actions still live here too (reused, not duplicated)
        # but nested in their own submenu instead of cluttering View directly.
        self.main_window.panels_menu = self.main_window.view_menu.addMenu(_("&Panels"))
        self.main_window.panels_menu.setObjectName("panelsMenu")

        self.main_window.show_recents_favorites_action = QAction(_("Show &Recents/Favorites"), self.main_window)
        self.main_window.show_recents_favorites_action.setCheckable(True)
        self.main_window.show_recents_favorites_action.setChecked(True)
        self.main_window.show_recents_favorites_action.triggered.connect(self.main_window.dock_manager.toggle_recents_favorites)
        self.main_window.panels_menu.addAction(self.main_window.show_recents_favorites_action)

        self.main_window.show_explorer_action = QAction(_("Show &Explorer"), self.main_window)
        self.main_window.show_explorer_action.setIcon(load_icon("explorer.svg"))
        self.main_window.show_explorer_action.setCheckable(True)
        self.main_window.show_explorer_action.setChecked(False)
        self.main_window.show_explorer_action.triggered.connect(self.main_window.dock_manager.toggle_explorer)
        self.main_window.panels_menu.addAction(self.main_window.show_explorer_action)

        self.main_window.show_playlists_action = QAction(_("Show &Playlists"), self.main_window)
        self.main_window.show_playlists_action.setCheckable(True)
        self.main_window.show_playlists_action.setChecked(False)
        self.main_window.show_playlists_action.triggered.connect(self.main_window.dock_manager.toggle_playlists)
        self.main_window.panels_menu.addAction(self.main_window.show_playlists_action)

        self.main_window.panels_menu.addSeparator()

        self.main_window.show_radio_action = QAction(_("Show &Radio Browser"), self.main_window)
        self.main_window.show_radio_action.setCheckable(True)
        self.main_window.show_radio_action.setChecked(False)
        self.main_window.show_radio_action.triggered.connect(self.main_window.dock_manager.toggle_radio)
        self.main_window.panels_menu.addAction(self.main_window.show_radio_action)

        self.main_window.show_podcast_action = QAction(_("Show &Podcasts"), self.main_window)
        self.main_window.show_podcast_action.setCheckable(True)
        self.main_window.show_podcast_action.setChecked(False)
        self.main_window.show_podcast_action.triggered.connect(self.main_window.dock_manager.toggle_podcast)
        self.main_window.panels_menu.addAction(self.main_window.show_podcast_action)

    def setup_tools_menu(self):
        self.main_window.batch_converter_action = QAction(_("&Batch Converter"), self.main_window)
        self.main_window.batch_converter_action.triggered.connect(self.main_window.tool_manager.open_batch_converter)
        self.main_window.tools_menu.addAction(self.main_window.batch_converter_action)
        
        self.main_window.extractor_action = QAction(_("&Media Extractor"), self.main_window)
        self.main_window.extractor_action.triggered.connect(self.main_window.tool_manager.open_extractor)
        self.main_window.tools_menu.addAction(self.main_window.extractor_action)
        
        self.main_window.tag_editor_action = QAction(_("&Tag Editor"), self.main_window)
        self.main_window.tag_editor_action.triggered.connect(self.main_window.tool_manager.open_tag_editor)
        self.main_window.tools_menu.addAction(self.main_window.tag_editor_action)
        
        self.main_window.thumbnail_generator_action = QAction(_("&Thumbnail Generator"), self.main_window)
        self.main_window.thumbnail_generator_action.triggered.connect(self.main_window.tool_manager.open_thumbnail_generator)
        self.main_window.tools_menu.addAction(self.main_window.thumbnail_generator_action)

        self.main_window.speech_converter_action = QAction(_("&Speech Converter"), self.main_window)
        self.main_window.speech_converter_action.triggered.connect(self.main_window.tool_manager.open_speech_converter)
        self.main_window.tools_menu.addAction(self.main_window.speech_converter_action)

        self.main_window.audiobook_tools_action = QAction(_("&Audiobook Tools (Bind/Split/Slide/Labels/Cover)"), self.main_window)
        self.main_window.audiobook_tools_action.triggered.connect(self.main_window.tool_manager.open_audiobook_tools)
        self.main_window.tools_menu.addAction(self.main_window.audiobook_tools_action)

        self.main_window.audiobook_combiner_action = QAction(_("Audiobook Co&mbiner (Combine/Metadata Dump)"), self.main_window)
        self.main_window.audiobook_combiner_action.triggered.connect(self.main_window.tool_manager.open_audiobook_combiner)
        self.main_window.tools_menu.addAction(self.main_window.audiobook_combiner_action)

        self.main_window.tools_menu.addSeparator()

        self.main_window.show_downloader_action = QAction(_("&Download Manager"), self.main_window)
        self.main_window.show_downloader_action.triggered.connect(self.main_window.open_downloader)
        self.main_window.tools_menu.addAction(self.main_window.show_downloader_action)

        self.main_window.subtitle_tools_menu = self.main_window.tools_menu.addMenu(_("&Subtitle Tools"))
        self.main_window.subtitle_converter_action = QAction(_("Subtitle &Converter"), self.main_window)
        self.main_window.subtitle_converter_action.triggered.connect(self.main_window.tool_manager.open_subtitle_converter)
        self.main_window.subtitle_tools_menu.addAction(self.main_window.subtitle_converter_action)
        
        self.main_window.subtitle_editor_action = QAction(_("Subtitle &Editor"), self.main_window)
        self.main_window.subtitle_editor_action.triggered.connect(self.main_window.tool_manager.open_subtitle_editor)
        self.main_window.subtitle_tools_menu.addAction(self.main_window.subtitle_editor_action)

        self.main_window.debug_menu = self.main_window.tools_menu.addMenu(_("&Debug"))
        self.main_window.view_logs_action = QAction(_("&View Logs…"), self.main_window)
        self.main_window.view_logs_action.triggered.connect(self.main_window.open_logs_viewer)
        self.main_window.debug_menu.addAction(self.main_window.view_logs_action)

        self.main_window.show_console_dock_action = QAction(_("Show &Console Dock"), self.main_window)
        self.main_window.show_console_dock_action.setCheckable(True)
        self.main_window.show_console_dock_action.setChecked(False)
        self.main_window.show_console_dock_action.triggered.connect(self.main_window.dock_manager.toggle_console_dock)
        self.main_window.debug_menu.addAction(self.main_window.show_console_dock_action)
        
    def setup_options_menu(self):
        self.main_window.preferences_action = QAction(_("&Manage Preferences"), self.main_window)
        self.main_window.preferences_action.triggered.connect(self.main_window.open_preferences)
        self.main_window.options_menu.addAction(self.main_window.preferences_action)

        self.main_window.manage_database_action = QAction(_("Manage &Database..."), self.main_window)
        self.main_window.manage_database_action.triggered.connect(self.main_window.open_manage_database)
        self.main_window.options_menu.addAction(self.main_window.manage_database_action)

        self.main_window.hotkeys_action = QAction(_("&Manage Hotkeys"), self.main_window)
        self.main_window.hotkeys_action.triggered.connect(self.main_window.open_hotkeys)
        self.main_window.options_menu.addAction(self.main_window.hotkeys_action)

        self.main_window.customize_toolbar_action = QAction(_("Customize &Toolbar..."), self.main_window)
        self.main_window.customize_toolbar_action.triggered.connect(
            self.main_window.toolbar_manager.open_toolbar_customize_dialog
        )
        self.main_window.options_menu.addAction(self.main_window.customize_toolbar_action)

        self.main_window.about_action = QAction(_("&About PlayForm..."), self.main_window)
        self.main_window.about_action.triggered.connect(self.main_window.open_about_dialog)
        self.main_window.options_menu.addAction(self.main_window.about_action)

        self.main_window.options_menu.addSeparator()

        self.main_window.check_updates_action = QAction(_("&Check for Updates..."), self.main_window)
        self.main_window.check_updates_action.triggered.connect(self.main_window.check_for_updates)
        self.main_window.options_menu.addAction(self.main_window.check_updates_action)

        self.main_window.get_utilities_action = QAction(_("Get/Update &Utilities..."), self.main_window)
        self.main_window.get_utilities_action.triggered.connect(self.main_window.open_utility_download_dialog)
        self.main_window.options_menu.addAction(self.main_window.get_utilities_action)

        self.main_window.options_menu.addSeparator()

        self.main_window.documentation_action = QAction(_("&Documentation..."), self.main_window)
        self.main_window.documentation_action.triggered.connect(self.main_window.open_documentation)
        self.main_window.options_menu.addAction(self.main_window.documentation_action)

    def update_recent_files_menu(self):
        self.main_window.recent_files_menu.clear()
        recent_files = self.main_window.recents_and_favorites_widget.get_recent_files_list()
        
        if not recent_files:
            no_recent_action = QAction(_("No recent files"), self.main_window)
            no_recent_action.setEnabled(False)
            self.main_window.recent_files_menu.addAction(no_recent_action)
        else:
            for file_path in recent_files:
                action = QAction(os.path.basename(file_path), self.main_window)
                action.setToolTip(file_path)
                action.triggered.connect(lambda checked=False, path=file_path: self.main_window.play_file(path))
                self.main_window.recent_files_menu.addAction(action)

    def update_recents_favorites_menu(self, visible):
        self.main_window.show_recents_favorites_action.setChecked(visible)
        self.main_window.dock_manager.update_focusable_widgets()
    
    def update_explorer_menu(self, visible):
        self.main_window.show_explorer_action.setChecked(visible)
        self.main_window.dock_manager.update_focusable_widgets()
        
    def update_player_menu(self, visible):
        self.main_window.minimize_player_action.setChecked(not visible)
        self.main_window.dock_manager.update_focusable_widgets()
        
    def update_playlists_menu(self, visible):
        self.main_window.show_playlists_action.setChecked(visible)
        self.main_window.dock_manager.update_focusable_widgets()
    
    def update_radio_menu(self, visible):
        if hasattr(self.main_window, 'show_radio_action'):
            self.main_window.show_radio_action.setChecked(visible)
        self.main_window.dock_manager.update_focusable_widgets()
    
    def update_podcast_menu(self, visible):
        if hasattr(self.main_window, 'show_podcast_action'):
            self.main_window.show_podcast_action.setChecked(visible)
        self.main_window.dock_manager.update_focusable_widgets()

    def update_console_menu(self, visible):
        if hasattr(self.main_window, 'show_console_dock_action'):
            self.main_window.show_console_dock_action.setChecked(visible)
        self.main_window.dock_manager.update_focusable_widgets()

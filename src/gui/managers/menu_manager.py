from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction
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
        self.main_window.open_file_action = QAction(_("&Open File..."), self.main_window)
        self.main_window.open_file_action.triggered.connect(self.main_window.open_file_dialog)
        self.main_window.file_menu.addAction(self.main_window.open_file_action)
        
        self.main_window.open_folder_action = QAction(_("Open &Folder..."), self.main_window)
        self.main_window.open_folder_action.setIcon(load_icon("explorer.svg"))
        self.main_window.open_folder_action.triggered.connect(self.main_window.open_folder_dialog)
        self.main_window.file_menu.addAction(self.main_window.open_folder_action)

        self.main_window.open_playlist_action = QAction(_("Open &Playlist..."), self.main_window)
        self.main_window.open_playlist_action.triggered.connect(self.main_window.open_playlist_dialog)
        self.main_window.file_menu.addAction(self.main_window.open_playlist_action)
        
        self.main_window.open_url_action = QAction(_("Open &URL..."), self.main_window)
        self.main_window.open_url_action.triggered.connect(self.main_window.open_url_dialog)
        self.main_window.file_menu.addAction(self.main_window.open_url_action)
        
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
        self.main_window.play_pause_action.triggered.connect(self.main_window.toggle_play_pause)
        self.main_window.media_menu.addAction(self.main_window.play_pause_action)
        
        self.main_window.stop_action = QAction(_("&Stop"), self.main_window)
        self.main_window.stop_action.setIcon(load_icon("stop.svg"))
        self.main_window.stop_action.triggered.connect(self.main_window.stop_playback)
        self.main_window.media_menu.addAction(self.main_window.stop_action)
        
        self.main_window.media_menu.addSeparator()
        
        self.main_window.mute_action = QAction(_("&Mute/Unmute"), self.main_window)
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
        
    def setup_view_menu(self):
        self.main_window.show_recents_favorites_action = QAction(_("Show &Recents/Favorites"), self.main_window)
        self.main_window.show_recents_favorites_action.setCheckable(True)
        self.main_window.show_recents_favorites_action.setChecked(True)
        self.main_window.show_recents_favorites_action.triggered.connect(self.main_window.dock_manager.toggle_recents_favorites)
        self.main_window.view_menu.addAction(self.main_window.show_recents_favorites_action)
        
        self.main_window.show_explorer_action = QAction(_("Show &Explorer"), self.main_window)
        self.main_window.show_explorer_action.setIcon(load_icon("explorer.svg"))
        self.main_window.show_explorer_action.setCheckable(True)
        self.main_window.show_explorer_action.setChecked(False)
        self.main_window.show_explorer_action.triggered.connect(self.main_window.dock_manager.toggle_explorer)
        self.main_window.view_menu.addAction(self.main_window.show_explorer_action)
        
        self.main_window.minimize_player_action = QAction(_("&Minimize Player"), self.main_window)
        self.main_window.minimize_player_action.setCheckable(True)
        self.main_window.minimize_player_action.triggered.connect(self.main_window.dock_manager.toggle_player_minimize)
        self.main_window.view_menu.addAction(self.main_window.minimize_player_action)
        
        self.main_window.show_playlists_action = QAction(_("Show &Playlists"), self.main_window)
        self.main_window.show_playlists_action.setCheckable(True)
        self.main_window.show_playlists_action.setChecked(False)
        self.main_window.show_playlists_action.triggered.connect(self.main_window.dock_manager.toggle_playlists)
        self.main_window.view_menu.addAction(self.main_window.show_playlists_action)
        
        self.main_window.view_menu.addSeparator()
        
        self.main_window.show_radio_action = QAction(_("Show &Radio Browser"), self.main_window)
        self.main_window.show_radio_action.setCheckable(True)
        self.main_window.show_radio_action.setChecked(False)
        self.main_window.show_radio_action.triggered.connect(self.main_window.dock_manager.toggle_radio)
        self.main_window.view_menu.addAction(self.main_window.show_radio_action)
        
        self.main_window.show_podcast_action = QAction(_("Show &Podcasts"), self.main_window)
        self.main_window.show_podcast_action.setCheckable(True)
        self.main_window.show_podcast_action.setChecked(False)
        self.main_window.show_podcast_action.triggered.connect(self.main_window.dock_manager.toggle_podcast)
        self.main_window.view_menu.addAction(self.main_window.show_podcast_action)

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

        self.main_window.customize_toolbar_action = QAction(_("Customize &Toolbar..."), self.main_window)
        self.main_window.customize_toolbar_action.triggered.connect(
            self.main_window.toolbar_manager.open_toolbar_customize_dialog
        )
        self.main_window.options_menu.addAction(self.main_window.customize_toolbar_action)

        self.main_window.hotkeys_action = QAction(_("&Manage Hotkeys"), self.main_window)
        self.main_window.hotkeys_action.triggered.connect(self.main_window.open_hotkeys)
        self.main_window.options_menu.addAction(self.main_window.hotkeys_action)

        self.main_window.options_menu.addSeparator()

        self.main_window.check_updates_action = QAction(_("&Check for Updates..."), self.main_window)
        self.main_window.check_updates_action.triggered.connect(self.main_window.check_for_updates)
        self.main_window.options_menu.addAction(self.main_window.check_updates_action)

        self.main_window.get_utilities_action = QAction(_("Get/Update &Utilities..."), self.main_window)
        self.main_window.get_utilities_action.triggered.connect(self.main_window.open_utility_download_dialog)
        self.main_window.options_menu.addAction(self.main_window.get_utilities_action)

        self.main_window.documentation_action = QAction(_("&Documentation"), self.main_window)
        self.main_window.documentation_action.setShortcut(
            key_config.key_config["Main interface"].get("Documentation", "F1")
        )
        self.main_window.documentation_action.triggered.connect(self.main_window.open_documentation)
        self.main_window.options_menu.addAction(self.main_window.documentation_action)

        self.main_window.options_menu.addSeparator()

        self.main_window.about_action = QAction(_("&About PlayForm..."), self.main_window)
        self.main_window.about_action.triggered.connect(self.main_window.open_about_dialog)
        self.main_window.options_menu.addAction(self.main_window.about_action)

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

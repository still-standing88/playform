from app_config import key_config


class MainWindowShortcuts:
    """MainWindow-level hotkey wiring and pane focus/toggle shortcuts,
    extracted out of MainWindow. Mirrors what core/player_shortcuts.py
    already does for PlayerWidget."""

    def __init__(self, main_window):
        self.main_window = main_window

    def setup(self):
        mw = self.main_window
        hotkeys = key_config.key_config["Main interface"]
        shortcuts = {
            hotkeys["Open file"]: mw.open_file_dialog,
            hotkeys["Open folder"]: mw.open_folder_dialog,
            hotkeys["Open URL"]: mw.open_url_dialog,
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
            hotkeys["Hide window"]: mw.hide_to_tray,
            hotkeys["Exit"]: mw.close_application,
            hotkeys["Focus explorer"]: self.focus_explorer,
            hotkeys["Focus player"]: self.focus_player,
            hotkeys["Documentation"]: mw.open_documentation,
            hotkeys["Hotkeys dialog"]: mw.open_hotkeys,
            hotkeys["Prefrences Dialog"]: mw.open_preferences,
            "F6": mw.focus_next_widget,
            "Shift+F6": mw.focus_previous_widget,
        }

        mw._shortcut_manager.clear_shortcuts()
        for shortcut in shortcuts:
            mw._shortcut_manager.add_context_shortcut(shortcut, shortcuts[shortcut])
        self.install_shortcuts()

    def reset_shortcuts(self):
        self.setup()

    def reset_shortcuts_callback(self):
        mw = self.main_window
        self.reset_shortcuts()

        if hasattr(mw.explorer_widget, 'reset_shortcuts'):
            mw.explorer_widget.reset_shortcuts()

        if hasattr(mw.player_widget, 'reset_shortcuts'):
            mw.player_widget.reset_shortcuts()

    def install_shortcuts(self):
        self.main_window._shortcut_manager.install_on_application()

    def uninstall_shortcuts(self):
        self.main_window._shortcut_manager.uninstall_from_application()

    def focus_explorer(self):
        mw = self.main_window
        if mw.explorer_dock and mw.explorer_dock.isVisible():
            if mw.explorer_widget:
                mw.explorer_widget.setFocus()

    def focus_player(self):
        mw = self.main_window
        if mw.player_dock and mw.player_dock.isVisible():
            mw.player_widget.setFocus()

    def focus_playlists(self):
        mw = self.main_window
        if mw.playlists_dock and mw.playlists_dock.isVisible():
            if mw.playlists_widget:
                mw.playlists_widget.setFocus()

    def focus_podcasts(self):
        mw = self.main_window
        if mw.podcast_dock and mw.podcast_dock.isVisible():
            if mw.podcast_widget:
                mw.podcast_widget.setFocus()

    def focus_radio(self):
        mw = self.main_window
        if mw.radio_dock and mw.radio_dock.isVisible():
            if mw.radio_widget:
                mw.radio_widget.setFocus()

    def focus_recents_favorites(self):
        mw = self.main_window
        if mw.recents_favorites_dock and mw.recents_favorites_dock.isVisible():
            if mw.recents_and_favorites_widget:
                mw.recents_and_favorites_widget.setFocus()

    def toggle_explorer_shortcut(self):
        mw = self.main_window
        if mw.show_explorer_action:
            mw.show_explorer_action.trigger()  # type: ignore

    def toggle_player_shortcut(self):
        mw = self.main_window
        if mw.minimize_player_action:
            mw.minimize_player_action.trigger()  # type: ignore

    def toggle_playlists_shortcut(self):
        mw = self.main_window
        if mw.playlists_dock:
            is_visible = mw.playlists_dock.isVisible()
            mw.playlists_dock.setVisible(not is_visible)
            if mw.show_playlists_action:
                mw.show_playlists_action.setChecked(not is_visible)
            if not is_visible and mw.playlists_widget:
                mw.playlists_widget.setFocus()

    def toggle_podcasts_shortcut(self):
        mw = self.main_window
        if mw.podcast_dock:
            is_visible = mw.podcast_dock.isVisible()
            mw.podcast_dock.setVisible(not is_visible)
            if mw.show_podcast_action:
                mw.show_podcast_action.setChecked(not is_visible)
            if not is_visible and mw.podcast_widget:
                mw.podcast_widget.setFocus()
        elif mw.show_podcast_action:
            # Create dock if it doesn't exist
            mw.show_podcast_action.setChecked(True)
            mw.show_podcast_action.trigger()

    def toggle_radio_shortcut(self):
        mw = self.main_window
        if mw.radio_dock:
            is_visible = mw.radio_dock.isVisible()
            mw.radio_dock.setVisible(not is_visible)
            if mw.show_radio_action:
                mw.show_radio_action.setChecked(not is_visible)
            if not is_visible and mw.radio_widget:
                mw.radio_widget.setFocus()
        elif mw.show_radio_action:
            # Create dock if it doesn't exist
            mw.show_radio_action.setChecked(True)
            mw.show_radio_action.trigger()

    def toggle_recents_favorites_shortcut(self):
        mw = self.main_window
        if mw.recents_favorites_dock:
            is_visible = mw.recents_favorites_dock.isVisible()
            mw.recents_favorites_dock.setVisible(not is_visible)
            if mw.show_recents_favorites_action:
                mw.show_recents_favorites_action.setChecked(not is_visible)
            if not is_visible and mw.recents_and_favorites_widget:
                mw.recents_and_favorites_widget.setFocus()

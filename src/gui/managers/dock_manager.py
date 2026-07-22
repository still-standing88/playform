from PySide6.QtWidgets import QDockWidget
from PySide6.QtCore import Qt
from app_config import prefs
from tools.debug_console_dock import DebugConsoleDock
from media_providers.radio import RadioBrowserWidget
from media_providers.podcasts.feed_widget import FeedWidget
from utilities.session import dock_session
from gui_controls.floatable_dock_widget import FloatableDockWidget


class DockManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self._dock_features = QDockWidget.DockWidgetFeature.DockWidgetMovable

    @staticmethod
    def _make_float_a_real_window(dock: QDockWidget):
        """A floated QDockWidget defaults to Qt::Tool, which most window
        managers (including Windows) exclude from Alt-Tab/taskbar switching.
        Force Qt::Window instead so it behaves like a normal, switchable
        top-level window once floated."""
        def on_top_level_changed(floating: bool):
            if floating:
                dock.setWindowFlags(dock.windowFlags() | Qt.WindowType.Window)
                dock.show()

        dock.topLevelChanged.connect(on_top_level_changed)

    def _floatable_features(self):
        # Closable so a close button renders once floated - FloatableDockWidget
        # overrides closeEvent so it re-docks and hides instead of destroying.
        return (
            self._dock_features
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

    def setup_dock_widgets(self):
        self.recents_favorites_dock = FloatableDockWidget(_("Recents && Favorites"), self.main_window)
        self.recents_favorites_dock.setObjectName("recentsFavoritesDock")
        self.recents_favorites_dock.setWidget(self.main_window.recents_and_favorites_widget)
        self.recents_favorites_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.recents_favorites_dock.setFeatures(self._floatable_features())
        self._make_float_a_real_window(self.recents_favorites_dock)
        self.recents_favorites_dock.visibilityChanged.connect(self.main_window.menu_manager.update_recents_favorites_menu)
        self.main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.recents_favorites_dock)
        self.main_window.recents_favorites_dock = self.recents_favorites_dock

        self.explorer_dock = FloatableDockWidget(_("Explorer"), self.main_window)
        self.explorer_dock.setObjectName("explorerDock")
        self.explorer_dock.setWidget(self.main_window.explorer_widget)
        self.explorer_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.explorer_dock.setFeatures(self._floatable_features())
        self._make_float_a_real_window(self.explorer_dock)
        self.explorer_dock.setVisible(False)
        self.explorer_dock.visibilityChanged.connect(self.main_window.menu_manager.update_explorer_menu)
        self.main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.explorer_dock)
        self.main_window.explorer_dock = self.explorer_dock

        self.playlists_dock = FloatableDockWidget(_("Playlists"), self.main_window)
        self.playlists_dock.setObjectName("playlistsDock")
        self.playlists_dock.setWidget(self.main_window.playlists_widget)
        self.playlists_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.playlists_dock.setFeatures(self._floatable_features())
        self._make_float_a_real_window(self.playlists_dock)
        self.playlists_dock.setVisible(False)
        self.playlists_dock.visibilityChanged.connect(self.main_window.menu_manager.update_playlists_menu)
        self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.playlists_dock)
        self.main_window.playlists_dock = self.playlists_dock

        self.player_dock = FloatableDockWidget(_("Player"), self.main_window)
        self.player_dock.setObjectName("playerDock")
        self.player_dock.setWidget(self.main_window.player_widget)
        self.player_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.player_dock.setFeatures(self._floatable_features())
        self._make_float_a_real_window(self.player_dock)
        self.player_dock.visibilityChanged.connect(self.main_window.menu_manager.update_player_menu)
        self.main_window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.player_dock)
        self.main_window.player_dock = self.player_dock

        # Debug console deliberately excluded from DockWidgetClosable/
        # FloatableDockWidget: its own closeEvent tears down the stdout/stderr
        # log redirect, which must only happen on real app shutdown, not on a
        # "close the floated window" hide - so it keeps no close button and
        # its default QDockWidget close-is-ignored behavior.
        self.debug_console_dock = DebugConsoleDock(self.main_window)
        self.debug_console_dock.setObjectName("debugConsoleDock")
        self._make_float_a_real_window(self.debug_console_dock)
        self.main_window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.debug_console_dock)
        self.debug_console_dock.hide()
        if hasattr(self.debug_console_dock, 'visibilityChanged'):
            self.debug_console_dock.visibilityChanged.connect(self.main_window.menu_manager.update_console_menu)
        self.main_window.debug_console_dock = self.debug_console_dock

        self.update_focusable_widgets()

    def save_dock_session(self):
        dock_states = {
            'recents_favorites': self.main_window.recents_favorites_dock.isVisible(),
            'explorer': self.main_window.explorer_dock.isVisible(),
            'player': self.player_dock.isVisible(),
            'playlists': self.main_window.playlists_dock.isVisible(),
            'radio': self.main_window.radio_dock.isVisible() if self.main_window.radio_dock else False,
            'podcast': self.main_window.podcast_dock.isVisible() if self.main_window.podcast_dock else False,
            'debug_console': self.main_window.debug_console_dock.isVisible() if hasattr(self.main_window, 'debug_console_dock') else False
        }
        dock_session.save_session(dock_states)

    def restore_dock_session(self):
        dock_states = dock_session.load_session()

        self.main_window.recents_favorites_dock.setVisible(dock_states.get('recents_favorites', True))
        self.main_window.show_recents_favorites_action.setChecked(dock_states.get('recents_favorites', True))

        self.main_window.explorer_dock.setVisible(dock_states.get('explorer', False))
        self.main_window.show_explorer_action.setChecked(dock_states.get('explorer', False))

        self.player_dock.setVisible(dock_states.get('player', True))
        self.main_window.minimize_player_action.setChecked(not dock_states.get('player', True))

        self.main_window.playlists_dock.setVisible(dock_states.get('playlists', False))
        self.main_window.show_playlists_action.setChecked(dock_states.get('playlists', False))

        if dock_states.get('radio', False):
            self._create_radio_dock()
            self.main_window.radio_dock.setVisible(True)
            if hasattr(self.main_window, 'show_radio_action'):
                self.main_window.show_radio_action.setChecked(True)

        if dock_states.get('podcast', False):
            self._create_podcast_dock()
            self.main_window.podcast_dock.setVisible(True)
            if hasattr(self.main_window, 'show_podcast_action'):
                self.main_window.show_podcast_action.setChecked(True)

        if dock_states.get('debug_console', False) and hasattr(self.main_window, 'debug_console_dock'):
            self.main_window.debug_console_dock.setVisible(True)
            if hasattr(self.main_window, 'show_console_dock_action'):
                self.main_window.show_console_dock_action.setChecked(True)

        self.update_focusable_widgets()

    def toggle_recents_favorites(self, checked):
        if self.main_window.recents_favorites_dock:
            self.main_window.recents_favorites_dock.setVisible(checked)
            if checked and self.main_window.recents_and_favorites_widget:
                self.main_window.recents_and_favorites_widget.setFocus()

    def toggle_explorer(self, checked):
        if self.main_window.explorer_dock:
            self.main_window.explorer_dock.setVisible(checked)
            if checked and self.main_window.explorer_widget:
                self.main_window.explorer_widget.setFocus()

    def toggle_player_minimize(self, checked):
        if self.player_dock:
            self.player_dock.setVisible(not checked)
            if not checked and self.main_window.player_widget:
                self.main_window.player_widget.setFocus()
        self.update_focusable_widgets()

    def toggle_playlists(self, checked):
        if self.main_window.playlists_dock:
            self.main_window.playlists_dock.setVisible(checked)
            if checked and self.main_window.playlists_widget:
                self.main_window.playlists_widget.setFocus()

    def toggle_radio(self, checked):
        if self.main_window.radio_dock is None and checked:
            self._create_radio_dock()
        if self.main_window.radio_dock:
            self.main_window.radio_dock.setVisible(checked)
            if checked and self.main_window.radio_widget:
                self.main_window.radio_widget.setFocus()
            self.update_focusable_widgets()

    def toggle_podcast(self, checked):
        if self.main_window.podcast_dock is None and checked:
            self._create_podcast_dock()
        if self.main_window.podcast_dock:
            self.main_window.podcast_dock.setVisible(checked)
            if checked and self.main_window.podcast_widget:
                self.main_window.podcast_widget.setFocus()
            self.update_focusable_widgets()

    def _sync_float_action_for_dock(self, dock, action_attr):
        # Radio/Podcast docks are lazily created, and can come into existence
        # through paths other than the Panels toolbar's own Float toggle
        # (e.g. restore_dock_session() runs after the toolbar is built and
        # may create them directly) - wire the sync here, at the one true
        # creation point, so the toolbar toggle stays correct regardless of
        # what actually triggered creation.
        action = getattr(self.main_window, action_attr, None)
        if action is None:
            return

        def sync(floating):
            if action.isChecked() != floating:
                action.blockSignals(True)
                action.setChecked(floating)
                action.blockSignals(False)

        dock.topLevelChanged.connect(sync)
        action.setChecked(dock.isFloating())

        # A hidden pane shouldn't be floatable - floating an invisible dock
        # just makes an invisible floating window appear detached from
        # nothing the user asked to see. Track dock.isVisible() directly
        # (ground truth) rather than a "show" action's checked state, since
        # some show actions (e.g. Player's minimize_player_action) use
        # inverted checked semantics.
        action.setEnabled(dock.isVisible())
        dock.visibilityChanged.connect(action.setEnabled)

    def _create_radio_dock(self):
        if self.main_window.radio_dock is None:
            self.main_window.radio_widget = RadioBrowserWidget(self.main_window)
            self.main_window.radio_widget.play_requested.connect(self.main_window.urlOpened.emit)
            self.main_window.radio_dock = FloatableDockWidget(_("Radio Browser"), self.main_window)
            self.main_window.radio_dock.setObjectName("radioDock")
            self.main_window.radio_dock.setWidget(self.main_window.radio_widget)
            self.main_window.radio_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
            self.main_window.radio_dock.setFeatures(self._floatable_features())
            self._make_float_a_real_window(self.main_window.radio_dock)
            self._sync_float_action_for_dock(self.main_window.radio_dock, "float_radio_action")
            self.main_window.radio_dock.visibilityChanged.connect(self.main_window.menu_manager.update_radio_menu)
            self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.main_window.radio_dock)

    def _create_podcast_dock(self):
        if self.main_window.podcast_dock is None:
            self.main_window.podcast_widget = FeedWidget(self.main_window)
            self.main_window.podcast_widget.play_requested.connect(self.main_window.urlOpened.emit)
            self.main_window.podcast_dock = FloatableDockWidget(_("Podcasts"), self.main_window)
            self.main_window.podcast_dock.setObjectName("podcastDock")
            self.main_window.podcast_dock.setWidget(self.main_window.podcast_widget)
            self.main_window.podcast_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
            self.main_window.podcast_dock.setFeatures(self._floatable_features())
            self._make_float_a_real_window(self.main_window.podcast_dock)
            self._sync_float_action_for_dock(self.main_window.podcast_dock, "float_podcast_action")
            self.main_window.podcast_dock.visibilityChanged.connect(self.main_window.menu_manager.update_podcast_menu)
            self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.main_window.podcast_dock)

    def toggle_console_dock(self, checked):
        if not hasattr(self.main_window, 'debug_console_dock') or self.main_window.debug_console_dock is None:
            self.main_window.debug_console_dock = DebugConsoleDock(self.main_window)
            self._make_float_a_real_window(self.main_window.debug_console_dock)
            self.main_window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.main_window.debug_console_dock)
            if hasattr(self.main_window.debug_console_dock, 'visibilityChanged'):
                self.main_window.debug_console_dock.visibilityChanged.connect(self.main_window.menu_manager.update_console_menu)
        if checked:
            self.main_window.debug_console_dock.show()
            self.main_window.debug_console_dock.raise_()
        else:
            self.main_window.debug_console_dock.hide()

    def save_window_state(self):
        mw = self.main_window
        prefs.prefs['window_geometry'] = mw.saveGeometry().data().hex()
        prefs.prefs['window_state'] = mw.saveState().data().hex()
        prefs.save()

    def restore_window_state(self):
        mw = self.main_window
        if 'window_geometry' in prefs.prefs and prefs.prefs['window_geometry']:
            try:
                geometry = bytes.fromhex(prefs.prefs['window_geometry'])
                mw.restoreGeometry(geometry)
            except:
                pass

        if 'window_state' in prefs.prefs and prefs.prefs['window_state']:
            try:
                state = bytes.fromhex(prefs.prefs['window_state'])
                mw.restoreState(state)
            except:
                pass

        # player_dock's visible/floating end-state is already authoritative
        # from restoreState() above (and, before that, restore_dock_session()'s
        # dock_session.json-based visibility) - just sync the action's
        # checked-state display from it. A legacy 'player_visible' pref used
        # to re-force visibility here *after* restoreState(), which silently
        # discarded whatever floating state restoreState() had just restored
        # for the player dock specifically (no other dock had this override).
        if mw.minimize_player_action:
            mw.minimize_player_action.setChecked(not (self.player_dock.isVisible() if self.player_dock else True))

    def _all_docks(self):
        mw = self.main_window
        docks = [mw.recents_favorites_dock, mw.explorer_dock, mw.playlists_dock, self.player_dock]
        docks += [d for d in (mw.radio_dock, mw.podcast_dock, getattr(mw, 'debug_console_dock', None)) if d is not None]
        return docks

    def hide_floating_docks(self):
        # A floated QDockWidget is a separate top-level Qt window - hiding
        # MainWindow (e.g. to the system tray) doesn't hide it too, so it's
        # left behind, visible, with no main window backing it. Remember
        # which ones were floating+visible so they can come back exactly as
        # they were.
        self._hidden_floating_docks = [d for d in self._all_docks() if d.isFloating() and d.isVisible()]
        for dock in self._hidden_floating_docks:
            dock.hide()

    def restore_floating_docks(self):
        for dock in getattr(self, '_hidden_floating_docks', []):
            dock.show()
        self._hidden_floating_docks = []

    def update_focusable_widgets(self):
        self.main_window.focusable_widgets = []

        # Menu bar deliberately excluded: it's already reachable via Alt, and
        # having it in the F6/Shift+F6 cycle too interferes with focus (it
        # grabs an "active action" highlight that competes with the rest of
        # pane navigation).
        if hasattr(self.main_window, 'toolbar') and self.main_window.toolbar.isVisible():
            self.main_window.focusable_widgets.append(self.main_window.toolbar)

        if hasattr(self.main_window, 'panels_toolbar') and self.main_window.panels_toolbar.isVisible():
            self.main_window.focusable_widgets.append(self.main_window.panels_toolbar)

        dock_widgets = [
            (self.main_window.recents_favorites_dock, self.main_window.recents_and_favorites_widget),
            (self.main_window.explorer_dock, self.main_window.explorer_widget),
            (self.main_window.playlists_dock, self.main_window.playlists_widget),
        ]

        if self.main_window.radio_dock is not None:
            dock_widgets.append((self.main_window.radio_dock, self.main_window.radio_widget))
        if self.main_window.podcast_dock is not None:
            dock_widgets.append((self.main_window.podcast_dock, self.main_window.podcast_widget))

        for dock, widget in dock_widgets:
            if dock.isVisible() and widget:
                self.main_window.focusable_widgets.append(widget)

        if self.player_dock.isVisible():
            self.main_window.focusable_widgets.append(self.main_window.player_widget)

        if hasattr(self.main_window, 'status_bar') and self.main_window.status_bar.isVisible():
            self.main_window.focusable_widgets.append(self.main_window.status_bar)

from PySide6.QtWidgets import QDockWidget
from PySide6.QtCore import Qt
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

    def setup_dock_widgets(self):
        self.recents_favorites_dock = QDockWidget(_("Recents && Favorites"), self.main_window)
        self.recents_favorites_dock.setObjectName("recentsFavoritesDock")
        self.recents_favorites_dock.setWidget(self.main_window.recents_and_favorites_widget)
        self.recents_favorites_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.recents_favorites_dock.setFeatures(self._dock_features)
        self.recents_favorites_dock.visibilityChanged.connect(self.main_window.menu_manager.update_recents_favorites_menu)
        self.main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.recents_favorites_dock)
        self.main_window.recents_favorites_dock = self.recents_favorites_dock

        self.explorer_dock = QDockWidget(_("Explorer"), self.main_window)
        self.explorer_dock.setObjectName("explorerDock")
        self.explorer_dock.setWidget(self.main_window.explorer_widget)
        self.explorer_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.explorer_dock.setFeatures(self._dock_features)
        self.explorer_dock.setVisible(False)
        self.explorer_dock.visibilityChanged.connect(self.main_window.menu_manager.update_explorer_menu)
        self.main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.explorer_dock)
        self.main_window.explorer_dock = self.explorer_dock

        self.playlists_dock = QDockWidget(_("Playlists"), self.main_window)
        self.playlists_dock.setObjectName("playlistsDock")
        self.playlists_dock.setWidget(self.main_window.playlists_widget)
        self.playlists_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.playlists_dock.setFeatures(self._dock_features)
        self.playlists_dock.setVisible(False)
        self.playlists_dock.visibilityChanged.connect(self.main_window.menu_manager.update_playlists_menu)
        self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.playlists_dock)
        self.main_window.playlists_dock = self.playlists_dock

        self.player_dock = FloatableDockWidget(_("Player"), self.main_window)
        self.player_dock.setObjectName("playerDock")
        self.player_dock.setWidget(self.main_window.player_widget)
        self.player_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        # Floatable pilot dock for the dock-panels accessibility spike; the
        # other docks stay on the shared, non-floatable _dock_features.
        # Closable so a close button renders once floated - FloatableDockWidget
        # overrides closeEvent so it re-docks and hides instead of destroying.
        self.player_dock.setFeatures(
            self._dock_features
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self._make_float_a_real_window(self.player_dock)
        self.player_dock.visibilityChanged.connect(self.main_window.menu_manager.update_player_menu)
        self.main_window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.player_dock)
        self.main_window.player_dock = self.player_dock

        self.debug_console_dock = DebugConsoleDock(self.main_window)
        self.debug_console_dock.setObjectName("debugConsoleDock")
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

    def _create_radio_dock(self):
        if self.main_window.radio_dock is None:
            self.main_window.radio_widget = RadioBrowserWidget(self.main_window)
            self.main_window.radio_widget.play_requested.connect(self.main_window.urlOpened.emit)
            self.main_window.radio_dock = QDockWidget(_("Radio Browser"), self.main_window)
            self.main_window.radio_dock.setObjectName("radioDock")
            self.main_window.radio_dock.setWidget(self.main_window.radio_widget)
            self.main_window.radio_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
            self.main_window.radio_dock.setFeatures(self._dock_features)
            self.main_window.radio_dock.visibilityChanged.connect(self.main_window.menu_manager.update_radio_menu)
            self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.main_window.radio_dock)

    def _create_podcast_dock(self):
        if self.main_window.podcast_dock is None:
            self.main_window.podcast_widget = FeedWidget(self.main_window)
            self.main_window.podcast_widget.play_requested.connect(self.main_window.urlOpened.emit)
            self.main_window.podcast_dock = QDockWidget(_("Podcasts"), self.main_window)
            self.main_window.podcast_dock.setObjectName("podcastDock")
            self.main_window.podcast_dock.setWidget(self.main_window.podcast_widget)
            self.main_window.podcast_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
            self.main_window.podcast_dock.setFeatures(self._dock_features)
            self.main_window.podcast_dock.visibilityChanged.connect(self.main_window.menu_manager.update_podcast_menu)
            self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.main_window.podcast_dock)

    def toggle_console_dock(self, checked):
        if not hasattr(self.main_window, 'debug_console_dock') or self.main_window.debug_console_dock is None:
            self.main_window.debug_console_dock = DebugConsoleDock(self.main_window)
            self.main_window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.main_window.debug_console_dock)
            if hasattr(self.main_window.debug_console_dock, 'visibilityChanged'):
                self.main_window.debug_console_dock.visibilityChanged.connect(self.main_window.menu_manager.update_console_menu)
        if checked:
            self.main_window.debug_console_dock.show()
            self.main_window.debug_console_dock.raise_()
        else:
            self.main_window.debug_console_dock.hide()

    def update_focusable_widgets(self):
        self.main_window.focusable_widgets = []

        menu_bar = self.main_window.menuBar()
        if menu_bar is not None and menu_bar.isVisible():
            self.main_window.focusable_widgets.append(menu_bar)

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

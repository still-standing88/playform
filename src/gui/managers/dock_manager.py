from PySide6.QtWidgets import QDockWidget
from PySide6.QtCore import Qt, QTimer
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
                # setWindowFlags() always hides the widget as a side effect,
                # regardless of whether the flags actually changed - re-show
                # it only if it was actually visible beforehand. Without this
                # guard, a dock restored as floating-but-hidden (e.g. via
                # QMainWindow.restoreState()) gets forced visible here, which
                # is why floated panes could reappear on launch even though
                # they were left hidden last session.
                was_visible = dock.isVisible()
                dock.setWindowFlags(dock.windowFlags() | Qt.WindowType.Window)
                if was_visible:
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

        # Recents/Favorites, Explorer, Playlists (and Radio/Podcasts, tabified
        # onto the same group when they're lazily created below) are all
        # "browse one source at a time" panels - stacking them instead of
        # tabifying meant every one of them simultaneously visible added its
        # own minimum height to the window's total, which is what pushed the
        # combined minimum past the screen's available height in the first
        # place. Tabifying means only the active one's content actually
        # claims space; the rest wait behind a tab.
        self.main_window.tabifyDockWidget(self.recents_favorites_dock, self.explorer_dock)
        self.main_window.tabifyDockWidget(self.recents_favorites_dock, self.playlists_dock)

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
        self.main_window.tabifyDockWidget(self.player_dock, self.debug_console_dock)
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
        self._schedule_clamp_to_screen()

    def toggle_explorer(self, checked):
        if self.main_window.explorer_dock:
            self.main_window.explorer_dock.setVisible(checked)
            if checked and self.main_window.explorer_widget:
                self.main_window.explorer_widget.setFocus()
        self._schedule_clamp_to_screen()

    def toggle_player_minimize(self, checked):
        if self.player_dock:
            self.player_dock.setVisible(not checked)
            if not checked and self.main_window.player_widget:
                self.main_window.player_widget.setFocus()
        self.update_focusable_widgets()
        self._schedule_clamp_to_screen()

    def toggle_playlists(self, checked):
        if self.main_window.playlists_dock:
            self.main_window.playlists_dock.setVisible(checked)
            if checked and self.main_window.playlists_widget:
                self.main_window.playlists_widget.setFocus()
        self._schedule_clamp_to_screen()

    def toggle_radio(self, checked):
        if self.main_window.radio_dock is None and checked:
            self._create_radio_dock()
        if self.main_window.radio_dock:
            self.main_window.radio_dock.setVisible(checked)
            if checked and self.main_window.radio_widget:
                self.main_window.radio_widget.setFocus()
            self.update_focusable_widgets()
        self._schedule_clamp_to_screen()

    def toggle_podcast(self, checked):
        if self.main_window.podcast_dock is None and checked:
            self._create_podcast_dock()
        if self.main_window.podcast_dock:
            self.main_window.podcast_dock.setVisible(checked)
            if checked and self.main_window.podcast_widget:
                self.main_window.podcast_widget.setFocus()
            self.update_focusable_widgets()
        self._schedule_clamp_to_screen()

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
            self.main_window.tabifyDockWidget(self.recents_favorites_dock, self.main_window.radio_dock)

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
            self.main_window.tabifyDockWidget(self.recents_favorites_dock, self.main_window.podcast_dock)

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
        self._schedule_clamp_to_screen()

    def save_window_state(self):
        mw = self.main_window
        prefs.prefs['window_geometry'] = mw.saveGeometry().data().hex()
        prefs.prefs['window_state'] = mw.saveState().data().hex()
        prefs.save()

    def restore_window_state(self):
        mw = self.main_window
        self.had_saved_geometry = False
        if 'window_geometry' in prefs.prefs and prefs.prefs['window_geometry']:
            try:
                geometry = bytes.fromhex(prefs.prefs['window_geometry'])
                mw.restoreGeometry(geometry)
                self.had_saved_geometry = True
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

        self._schedule_clamp_to_screen()

    def _schedule_clamp_to_screen(self):
        # Deferred because the layout hasn't actually recalculated the
        # window's real size yet at the point a dock's visibility changes -
        # running this synchronously would check stale geometry.
        QTimer.singleShot(0, self.clamp_to_screen)

    # The window's own ideal, comfortable minimum - not necessarily what
    # any given screen can actually offer. Recomputed against the current
    # screen on every clamp_to_screen() pass rather than set once, so a
    # bigger monitor always gets the full 1200x800 back.
    IDEAL_MIN_WIDTH = 1200
    IDEAL_MIN_HEIGHT = 800

    def _resync_min_height(self, mw, available):
        # setMinimumSize() is a hard floor Qt enforces on every subsequent
        # resize() call, including the ones this method issues below - a
        # stale, too-tall explicit minimum silently overrides any resize()
        # asking for something shorter, no error, no signal, the window
        # just snaps back. This is what made clamp_to_screen()'s own
        # resize() calls look like no-ops in statusbar_debug.log: the main
        # window's minimumSize was still (1200, 800) while available height
        # was ~720. Keeping the explicit minimum itself in sync with the
        # current screen, not just the window's actual size, is what
        # actually lets it shrink.
        frame = mw.frameGeometry()
        geo = mw.geometry()
        frame_extra_w = frame.width() - geo.width()
        frame_extra_h = frame.height() - geo.height()
        # A small deliberate safety margin on the window's own target height,
        # not just a knife-edge fit against availableGeometry() - verified
        # live that even when the status bar's Qt-reported geometry showed
        # a mathematically exact fit (status_bar.y() + its height ==
        # mw.height(), to the pixel), it still rendered visibly clipped in
        # real screenshots. Windows 10/11 frameGeometry()/availableGeometry()
        # measurements can be a few pixels off from what's actually
        # composited (DWM's invisible resize border being the likely
        # culprit) - leaving the window itself a bit shorter than the
        # theoretical maximum absorbs that discrepancy instead of chasing
        # dock content floors that turned out not to be the real constraint.
        SCREEN_FIT_SAFETY_MARGIN = 16
        target_min_w = max(0, min(self.IDEAL_MIN_WIDTH, available.width() - frame_extra_w))
        target_min_h = max(0, min(self.IDEAL_MIN_HEIGHT, available.height() - frame_extra_h - SCREEN_FIT_SAFETY_MARGIN))
        mw.setMinimumSize(target_min_w, target_min_h)

        # Dock content floors (Explorer's, Player's accordion, the video
        # placeholder) are reset to their own ideal size first, then only
        # shrunk as far as this specific screen's remaining budget actually
        # demands - never mutated cumulatively, so unplugging from a small
        # screen restores the comfortable defaults instead of leaving them
        # permanently shrunk from whatever the smallest screen ever seen
        # last demanded. Doing this reset *before* the resize below matters:
        # resetting it after was what let Qt's own layout silently grow the
        # window straight back past a just-applied smaller size.
        player = getattr(mw, 'player_widget', None)
        if player is not None and hasattr(player, 'set_accordion_floor'):
            player.set_accordion_floor(player.IDEAL_ACCORDION_FLOOR)
        explorer = getattr(mw, 'explorer_widget', None)
        if explorer is not None and hasattr(explorer, 'set_content_floor'):
            explorer.set_content_floor(explorer.IDEAL_CONTENT_FLOOR)
        video_display = getattr(player, 'video_display', None) if player is not None else None
        if video_display is not None and hasattr(video_display, 'set_height_floor'):
            video_display.set_height_floor(video_display.IDEAL_HEIGHT_FLOOR)

        # A transient ceiling, not a permanent one - Qt's QMainWindowLayout
        # can silently grow the window past this resize() to satisfy its own
        # computed content minimum (verified live: minimumSize() stayed at
        # the requested value while the window's actual height grew past it
        # anyway, and resizeDocks() below can trigger the same growth).
        # Held through the whole resync chain (cleared in
        # _resync_status_bar_step once it actually terminates) rather than
        # cleared immediately, so this never becomes a standing restriction
        # that would stop the user resizing the window taller later (e.g.
        # after moving to a bigger monitor).
        mw.setMaximumHeight(target_min_h)
        mw.resize(target_min_w, target_min_h)

        QTimer.singleShot(0, lambda: self._resync_status_bar_step(mw, 0))

    def _resync_status_bar_step(self, mw, iteration):
        # mw.minimumSizeHint() proved unreliable as the signal to shrink
        # against - the panels toolbar's own minimumSizeHint() undercounts
        # its real two-row wrapped height (a known FlowLayout quirk already
        # hit elsewhere in this codebase). Measuring the status bar's own
        # actual on-screen position is ground truth instead of a
        # prediction. And a tight processEvents() loop within one call
        # doesn't work either - verified live that status_bar.y() stays
        # frozen at a stale, pre-shrink value no matter how many times
        # processEvents() is pumped inside the same call stack, but a
        # genuinely separate later invocation sees the correctly settled
        # position. Something in Qt's dock/toolbar layout defers the actual
        # recompute past what synchronous pumping can force (a reentrancy
        # guard, most likely) - chaining through QTimer.singleShot instead
        # gives it a real separate event-loop turn each step, which does
        # let it settle.
        status_bar = getattr(mw, 'status_bar', None)
        if status_bar is None or iteration >= 10:
            mw.setMaximumHeight(16777215)
            return
        STATUS_BAR_TARGET_H = 24
        visible_h = min(status_bar.height(), max(0, mw.height() - status_bar.y()))
        shortfall = STATUS_BAR_TARGET_H - visible_h
        if shortfall <= 0:
            mw.setMaximumHeight(16777215)
            return

        player = getattr(mw, 'player_widget', None)
        explorer = getattr(mw, 'explorer_widget', None)
        video_display = getattr(player, 'video_display', None) if player is not None else None
        cut_any = False
        if player is not None and hasattr(player, 'set_accordion_floor'):
            current = player.accordion_scroll.minimumHeight()
            reducible = current - player.MIN_ACCORDION_FLOOR
            if reducible > 0:
                cut = min(shortfall, reducible)
                player.set_accordion_floor(current - cut)
                cut_any = True
        if explorer is not None and hasattr(explorer, 'set_content_floor'):
            current = explorer.splitter_scroll.minimumHeight()
            reducible = current - explorer.MIN_CONTENT_FLOOR
            if reducible > 0:
                cut = min(shortfall, reducible)
                explorer.set_content_floor(current - cut)
                cut_any = True
        if video_display is not None and hasattr(video_display, 'set_height_floor'):
            current = video_display.placeholder_label.minimumHeight()
            reducible = current - video_display.MIN_HEIGHT_FLOOR
            if reducible > 0:
                cut = min(shortfall, reducible)
                video_display.set_height_floor(current - cut)
                cut_any = True

        # Lowering a dock's minimum doesn't by itself make the splitter
        # between docks give back the freed space - Qt's internal
        # dock-area splitter only redistributes on an active resize
        # trigger or an explicit request, not just because a minimum
        # changed somewhere underneath it. Explicitly asking each visible
        # dock to shrink to (as close to) nothing forces Qt to actively
        # recompute the split against the new, smaller minimums instead
        # of leaving it at whatever the splitter last happened to be.
        shrink_docks = []
        shrink_sizes = []
        for dock in (getattr(mw, 'explorer_dock', None), self.player_dock, getattr(mw, 'recents_favorites_dock', None)):
            if dock is not None and dock.isVisible() and not dock.isFloating():
                shrink_docks.append(dock)
                shrink_sizes.append(1)
        if shrink_docks:
            mw.resizeDocks(shrink_docks, shrink_sizes, Qt.Orientation.Vertical)

        if not cut_any:
            mw.setMaximumHeight(16777215)
            return
        QTimer.singleShot(0, lambda: self._resync_status_bar_step(mw, iteration + 1))

    def clamp_to_screen(self):
        # Growing dock/toolbar content can make QMainWindow taller (or
        # wider) than the current screen's available area, since Qt's
        # layout generally grows the window to satisfy combined minimum
        # sizes rather than violate them - pushing the status bar (always
        # at the window's own bottom edge, not the screen's) below what's
        # actually visible. restoreGeometry() only clamps this once, at
        # startup (see restore_window_state()) - this re-checks after
        # anything that can grow the window mid-session, i.e. any dock
        # being toggled visible.
        mw = self.main_window
        if mw.isFullScreen():
            return

        screen = mw.screen()
        if screen is None:
            return
        available = screen.availableGeometry()

        self._resync_min_height(mw, available)

        if mw.isMaximized():
            # restoreGeometry()/restoreState() can restore a maximized flag
            # saved from a previous session on a different (larger) screen -
            # Qt then reports isMaximized()=True without reconciling the
            # frame against *this* screen's availableGeometry, so the frame
            # still hangs off the current screen's edges (verified live via
            # statusbar_debug.log: frame height 831 while available height
            # was ~720-728, pushing the status bar off the bottom entirely).
            # Only trust the maximized state if it actually fits; otherwise
            # drop out of it and refit manually below, the same way
            # show_or_maximize() already avoids trusting showMaximized().
            if available.contains(mw.frameGeometry()):
                return
            mw.showNormal()

        # _resync_min_height() above already resized the window to fit (with
        # its own safety margin against the frame-measurement discrepancy
        # documented there) - recomputing and re-applying a *different*,
        # unmargined size here used to silently undo that: this ran
        # synchronously right after _resync_min_height() returned, before
        # the deferred status-bar-fit check ever got a chance to run,
        # putting the window right back to the too-tall size on every
        # single call. Only positioning (below) is still this function's
        # job now.
        frame = mw.frameGeometry()
        x = min(frame.x(), available.right() - frame.width() + 1)
        y = min(frame.y(), available.bottom() - frame.height() + 1)
        x = max(x, available.left())
        y = max(y, available.top())
        if (x, y) != (frame.x(), frame.y()):
            mw.move(x, y)

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

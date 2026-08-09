from PySide6.QtWidgets import QToolBar, QMenu, QDialog, QLabel, QWidget, QToolButton, QFrame, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from app_config.toolbar_config import toolbar_config
from gui.dialogs.toolbar_customize_dialog import ToolbarCustomizeDialog
from gui_controls.flow_layout import FlowLayout, FlowContainer

class ToolbarManager:
    def __init__(self, main_window):
        self.main_window = main_window

    def setup_panels_toolbar(self):
        mw = self.main_window
        # Seven pane groups (label + show/float button each) don't fit in a
        # single QToolBar row at ordinary window widths, and a QToolBar can't
        # wrap onto a second row - it's a fixed-height single line, so Qt
        # pushes overflow behind its own extension chevron, where the buttons
        # report isVisible() False and are unreachable by Tab (confirmed by
        # testing). A fixed N-row split has the same problem, just moved -
        # whichever row is fullest still can't shrink to fit. A FlowLayout
        # (Qt's own pattern for this - see gui_controls/flow_layout.py) wraps
        # onto as many rows as the available width actually needs, so every
        # button stays visible and reachable regardless of window size.
        mw.panels_toolbar = QToolBar(_("Panels"))
        mw.panels_toolbar.setObjectName("panelsToolbar")
        mw.panels_toolbar.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        mw.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        mw.addToolBar(Qt.ToolBarArea.TopToolBarArea, mw.panels_toolbar)

        self._panels_container = FlowContainer()
        self._panels_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._panels_flow = FlowLayout(self._panels_container, margin=2, h_spacing=6, v_spacing=4)
        mw.panels_toolbar.addWidget(self._panels_container)

        # Default Tab order follows widget-creation order across the WHOLE
        # window, not containment - without explicitly chaining these
        # buttons together, Tab escapes the toolbar into whatever other
        # widget happened to be constructed next (confirmed by testing:
        # it jumped straight into the Explorer search box after one hop).
        self._last_tab_widget = None
        self._first_tab_widget = None

        self._add_pane_group(_("Player"), mw.minimize_player_action, "player_dock", "float_player_action",
                              show_button_text=_("Minimize"))
        self._add_pane_group(_("Recents/Favorites"), mw.show_recents_favorites_action,
                              "recents_favorites_dock", "float_recents_favorites_action")
        self._add_pane_group(_("Explorer"), mw.show_explorer_action, "explorer_dock", "float_explorer_action")
        self._add_pane_group(_("Playlists"), mw.show_playlists_action, "playlists_dock", "float_playlists_action")
        self._add_pane_group(_("Radio"), mw.show_radio_action, "radio_dock", "float_radio_action",
                              ensure_dock=mw.dock_manager._create_radio_dock)
        self._add_pane_group(_("Podcasts"), mw.show_podcast_action, "podcast_dock", "float_podcast_action",
                              ensure_dock=mw.dock_manager._create_podcast_dock)
        self._add_pane_group(_("Multi Device Capture"), mw.show_multi_device_capture_action,
                              "multi_device_capture_dock", "float_multi_device_capture_action",
                              ensure_dock=mw.dock_manager._create_multi_device_capture_dock)
        self._add_pane_group(_("Console"), mw.show_console_dock_action, "debug_console_dock", "float_console_action")

        mw.panels_toolbar_first_widget = self._first_tab_widget

    @staticmethod
    def _apply_focus_policy(toolbar):
        # QToolBar.setFocusPolicy only makes the toolbar itself one Tab stop;
        # the QToolButtons addAction() creates default to NoFocus, so without
        # this they're mouse-only and invisible to Tab/keyboard navigation.
        for action in toolbar.actions():
            button = toolbar.widgetForAction(action)
            if button is not None:
                button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def ensure_panels_toolbar_break(self):
        # QMainWindow.restoreState() (called from restore_window_state, right
        # before this runs) can silently drop the break added in
        # setup_panels_toolbar() if it's restoring a layout saved before this
        # toolbar existed - re-assert it unconditionally afterward so an
        # upgrading user with an old saved window_state doesn't end up with
        # this toolbar squeezed into an overflow chevron.
        mw = self.main_window
        if not mw.toolBarBreak(mw.panels_toolbar):
            mw.insertToolBarBreak(mw.panels_toolbar)

    def _add_pane_group(self, label_text, show_action, dock_attr, float_action_attr, ensure_dock=None,
                         show_button_text=None):
        """Add a labeled [show/hide][float] button pair for one pane to the
        Panels toolbar's flow layout. dock_attr is looked up on main_window
        lazily (via getattr each time) so this works for docks not yet
        created, like Radio/Podcasts - ensure_dock creates the dock on first
        float."""
        mw = self.main_window
        flow = self._panels_flow

        if flow.count():
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.VLine)
            separator.setFrameShadow(QFrame.Shadow.Sunken)
            flow.addWidget(separator)

        flow.addWidget(QLabel(label_text))

        show_button = QToolButton()
        show_button.setDefaultAction(show_action)
        show_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        show_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        flow.addWidget(show_button)

        float_action = QAction(_("Float"), mw)
        float_action.setCheckable(True)
        setattr(mw, float_action_attr, float_action)

        float_button = QToolButton()
        float_button.setDefaultAction(float_action)
        float_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        float_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        flow.addWidget(float_button)

        # The group label already names the pane, so the show/hide button's
        # own full action text ("Show &Radio Browser") is redundant width -
        # shorten just this button's display text, leaving show_action.text()
        # (and its View-menu entry) untouched.
        show_button.setText(show_button_text or _("Show"))

        for button in (show_button, float_button):
            if self._first_tab_widget is None:
                self._first_tab_widget = button
            if getattr(self, "_last_tab_widget", None) is not None:
                QWidget.setTabOrder(self._last_tab_widget, button)
            self._last_tab_widget = button

        def get_dock():
            return getattr(mw, dock_attr, None)

        def on_toggled(checked):
            dock = get_dock()
            if dock is None and checked and ensure_dock is not None:
                # For lazily-created panes (Radio/Podcasts), ensure_dock's own
                # creation method wires the Float-toggle sync itself (via
                # DockManager._sync_float_action_for_dock), since that's the
                # one true creation point regardless of what triggers it.
                ensure_dock()
                dock = get_dock()
            if dock is not None and dock.isFloating() != checked:
                dock.setFloating(checked)

        float_action.toggled.connect(on_toggled)

        # Eagerly-created docks (everything except Radio/Podcasts) already
        # exist by the time this runs, so wire the sync directly here.
        dock = get_dock()
        if dock is not None:
            float_action.setChecked(dock.isFloating())
            dock.topLevelChanged.connect(lambda floating: self._sync_toggle(float_action, floating))

            # A hidden pane shouldn't be floatable - track dock.isVisible()
            # directly (ground truth) rather than show_action's checked
            # state, since Player's show_action (minimize_player_action) uses
            # inverted checked semantics (checked == minimized/hidden).
            float_action.setEnabled(dock.isVisible())
            dock.visibilityChanged.connect(float_action.setEnabled)
        else:
            # Lazily-created docks (Radio/Podcasts) don't exist yet - nothing
            # to float until they're first shown. DockManager's
            # _sync_float_action_for_dock takes over enabling/disabling once
            # ensure_dock() actually creates the dock.
            float_action.setEnabled(False)

    @staticmethod
    def _sync_toggle(action, checked):
        if action.isChecked() != checked:
            action.blockSignals(True)
            action.setChecked(checked)
            action.blockSignals(False)

    def setup_toolbar(self):
        self.main_window.toolbar = QToolBar(_("Main Toolbar"))
        self.main_window.toolbar.setObjectName("mainToolbar")
        self.main_window.toolbar.setMovable(False)
        self.main_window.toolbar.setFloatable(False)
        self.main_window.toolbar.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.main_window.toolbar.setIconSize(self.main_window.toolbar.iconSize())
        self.main_window.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.main_window.toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.main_window.toolbar.customContextMenuRequested.connect(self.show_toolbar_context_menu)
        self.main_window.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.main_window.toolbar)
        
        self.main_window.toolbar.addAction(self.main_window.open_file_action)
        self.main_window.toolbar.addAction(self.main_window.open_folder_action)
        self.main_window.toolbar.addAction(self.main_window.open_playlist_action)
        self.main_window.toolbar.addAction(self.main_window.open_url_action)
        self.main_window.toolbar.addSeparator()
        self.main_window.toolbar.addAction(self.main_window.play_pause_action)
        self.main_window.toolbar.addAction(self.main_window.stop_action)
        self.main_window.toolbar.addAction(self.main_window.mute_action)
        self.main_window.toolbar.addSeparator()
        self.main_window.toolbar.addAction(self.main_window.previous_action)
        self.main_window.toolbar.addAction(self.main_window.next_action)
        
        self.main_window.toolbar.addSeparator()
        self.load_toolbar_tools()
        self._apply_focus_policy(self.main_window.toolbar)

    def show_toolbar_context_menu(self, pos):
        menu = QMenu(self.main_window)
        customize_action = QAction(_("Customize Toolbar..."), self.main_window)
        customize_action.triggered.connect(self.open_toolbar_customize_dialog)
        menu.addAction(customize_action)
        menu.exec(self.main_window.toolbar.mapToGlobal(pos))
    
    def open_toolbar_customize_dialog(self):
        available_tools = toolbar_config.get_available_tools()
        selected_tools = toolbar_config.load_config()
        
        dialog = ToolbarCustomizeDialog(available_tools, selected_tools, self.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_tools = dialog.get_selected_tools()
            toolbar_config.save_config(new_tools)
            self.update_toolbar_tools()
    
    def load_toolbar_tools(self):
        selected_tools = toolbar_config.load_config()
        self.main_window.tool_actions_map = {
            'batch_converter': self.main_window.batch_converter_action,
            'extractor': self.main_window.extractor_action,
            'tag_editor': self.main_window.tag_editor_action,
            'thumbnail_generator': self.main_window.thumbnail_generator_action,
            'subtitle_converter': self.main_window.subtitle_converter_action,
            'subtitle_editor': self.main_window.subtitle_editor_action
        }
        
        for tool_id in selected_tools:
            if tool_id in self.main_window.tool_actions_map:
                self.main_window.toolbar.addAction(self.main_window.tool_actions_map[tool_id])
    
    def update_toolbar_tools(self):
        actions = self.main_window.toolbar.actions()
        for action in actions:
            if action in self.main_window.tool_actions_map.values():
                self.main_window.toolbar.removeAction(action)

        selected_tools = toolbar_config.load_config()
        for tool_id in selected_tools:
            if tool_id in self.main_window.tool_actions_map:
                self.main_window.toolbar.addAction(self.main_window.tool_actions_map[tool_id])
        self._apply_focus_policy(self.main_window.toolbar)

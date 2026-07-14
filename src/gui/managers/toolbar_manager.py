from PySide6.QtWidgets import QToolBar, QMenu, QDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from app_config.toolbar_config import toolbar_config
from gui.dialogs.toolbar_customize_dialog import ToolbarCustomizeDialog

class ToolbarManager:
    def __init__(self, main_window):
        self.main_window = main_window

    def setup_panels_toolbar(self):
        self.main_window.panels_toolbar = QToolBar(_("Panels"))
        self.main_window.panels_toolbar.setObjectName("panelsToolbar")
        self.main_window.panels_toolbar.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.main_window.panels_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.main_window.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.main_window.panels_toolbar)

        if self.main_window.minimize_player_action:
            self.main_window.panels_toolbar.addAction(self.main_window.minimize_player_action)

        player_dock = self.main_window.player_dock
        self.main_window.float_player_action = QAction(_("Float Player"), self.main_window)
        self.main_window.float_player_action.setCheckable(True)
        self.main_window.float_player_action.setChecked(player_dock.isFloating())
        self.main_window.float_player_action.toggled.connect(self._on_float_player_toggled)
        self.main_window.panels_toolbar.addAction(self.main_window.float_player_action)

        player_dock.topLevelChanged.connect(self._sync_float_player_action)

        # QToolBar.setFocusPolicy only makes the toolbar itself one Tab stop;
        # the QToolButtons addAction() creates default to NoFocus, so without
        # this they're mouse-only and invisible to Tab/keyboard navigation.
        for action in self.main_window.panels_toolbar.actions():
            button = self.main_window.panels_toolbar.widgetForAction(action)
            if button is not None:
                button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _on_float_player_toggled(self, checked):
        player_dock = self.main_window.player_dock
        if player_dock.isFloating() != checked:
            player_dock.setFloating(checked)

    def _sync_float_player_action(self, floating):
        action = self.main_window.float_player_action
        if action.isChecked() != floating:
            action.blockSignals(True)
            action.setChecked(floating)
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

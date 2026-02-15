from PySide6.QtWidgets import QToolBar, QMenu, QDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from app_config.toolbar_config import toolbar_config
from gui.toolbar_customize_dialog import ToolbarCustomizeDialog

class ToolbarManager:
    def __init__(self, main_window):
        self.main_window = main_window
        
    def setup_toolbar(self):
        self.main_window.toolbar = QToolBar("Main Toolbar")
        self.main_window.toolbar.setObjectName("mainToolbar")
        self.main_window.toolbar.setMovable(False)
        self.main_window.toolbar.setFloatable(False)
        self.main_window.toolbar.setIconSize(self.main_window.toolbar.iconSize())
        self.main_window.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.main_window.toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.main_window.toolbar.customContextMenuRequested.connect(self.show_toolbar_context_menu)
        self.main_window.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.main_window.toolbar)
        
        self.main_window.toolbar.addAction(self.main_window.open_file_action)
        self.main_window.toolbar.addAction(self.main_window.open_folder_action)
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
        customize_action = QAction("Customize Toolbar...", self.main_window)
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

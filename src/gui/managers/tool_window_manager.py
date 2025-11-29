from PySide6.QtWidgets import QMessageBox
from tools.batch_converter_ui import BatchConverterUI
from tools.extractor_ui import ExtractorUI
from tools.tag_editor_ui import TagEditorUI
from tools.thumbnail_generator_ui import ThumbnailGeneratorUI
from tools.subtitle_converter_ui import SubtitleConverterUI
from tools.subtitle_editor_ui import SubtitleEditorUI
from gui.tool_dialog import ToolDialog
from tools.logs_viewer_dialog import LogsViewerDialog
from utilities import signal_manager

class ToolWindowManager:
    def __init__(self, main_window):
        self.main_window = main_window
        
    def open_batch_converter(self):
        self.open_tool_dialog("batch_converter", BatchConverterUI(), "Batch Converter")
        
    def open_extractor(self):
        self.open_tool_dialog("extractor", ExtractorUI(), "Media Extractor")
        
    def open_tag_editor(self):
        self.open_tool_dialog("tag_editor", TagEditorUI(), "Tag Editor")
        
    def open_thumbnail_generator(self):
        self.open_tool_dialog("thumbnail_generator", ThumbnailGeneratorUI(), "Thumbnail Generator")
    
    def open_subtitle_converter(self):
        self.open_tool_dialog("subtitle_converter", SubtitleConverterUI(), "Subtitle Converter")
    
    def open_subtitle_editor(self):
        self.open_tool_dialog("subtitle_editor", SubtitleEditorUI(), "Subtitle Editor")
        
    def open_tool_dialog(self, tool_name, tool_widget, title):
        if self.main_window.active_tool_name and self.main_window.active_tool_name != tool_name:
            if self.main_window.active_tool_name in self.main_window.tool_dialogs:
                active_dialog = self.main_window.tool_dialogs[self.main_window.active_tool_name]
                if active_dialog.isVisible() or self.main_window.show_tool_button.isVisible():
                    QMessageBox.information(
                        self.main_window,
                        "Tool Already Open",
                        f"'{active_dialog.title}' is already open. Please close it before opening another tool.",
                        QMessageBox.StandardButton.Ok
                    )
                    return
        
        if tool_name in self.main_window.tool_dialogs:
            dialog = self.main_window.tool_dialogs[tool_name]
            dialog.show_dialog()
            self.main_window.show_tool_button.setVisible(False)
        else:
            dialog = ToolDialog(tool_widget, title, self.main_window)
            dialog.dialog_hidden.connect(lambda: self.on_tool_hidden(tool_name, title))
            dialog.finished.connect(lambda: self.on_tool_closed(tool_name))
            self.main_window.tool_dialogs[tool_name] = dialog
            dialog.show_dialog()
        
        self.main_window.active_tool_name = tool_name
        signal_manager.statusbar_message.emit(f"Opened {title}")
    
    def on_tool_hidden(self, tool_name, title):
        self.main_window.show_tool_button.setText(f"Show {title}")
        self.main_window.show_tool_button.setVisible(True)
        signal_manager.statusbar_message.emit(f"{title} hidden")
    
    def on_tool_closed(self, tool_name):
        if tool_name in self.main_window.tool_dialogs:
            del self.main_window.tool_dialogs[tool_name]
        if self.main_window.active_tool_name == tool_name:
            self.main_window.active_tool_name = None
        self.main_window.show_tool_button.setVisible(False)
        signal_manager.statusbar_message.emit("Tool closed")
    
    def show_hidden_tool(self):
        if self.main_window.active_tool_name and self.main_window.active_tool_name in self.main_window.tool_dialogs:
            dialog = self.main_window.tool_dialogs[self.main_window.active_tool_name]
            dialog.show_dialog()
            self.main_window.show_tool_button.setVisible(False)
            signal_manager.statusbar_message.emit(f"Showing {dialog.title}")

    def has_active_tools(self):
        for tool_name, dialog in self.main_window.tool_dialogs.items():
            if dialog.is_tool_active():
                return True
        return False
    
    def get_active_tool_names(self):
        active_tools = []
        for tool_name, dialog in self.main_window.tool_dialogs.items():
            if dialog.is_tool_active():
                active_tools.append(dialog.title)
        return active_tools
    
    def confirm_close_with_active_tools(self):
        active_tools = self.get_active_tool_names()
        if not active_tools:
            return True
        
        tools_text = ", ".join(active_tools)
        reply = QMessageBox.question(
            self.main_window,
            "Active Tools",
            f"The following tools are currently active:\n{tools_text}\n\n"
            "Closing the application will stop these processes. Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        return reply == QMessageBox.StandardButton.Yes

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QLabel, QListWidgetItem
)
from PySide6.QtCore import Qt


class ToolbarCustomizeDialog(QDialog):
    
    def __init__(self, available_tools, selected_tools, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Customize Toolbar")
        self.setModal(True)
        self.resize(600, 400)
        
        self.available_tools = available_tools
        self.selected_tools = selected_tools.copy()
        
        self.setup_ui()
        self.populate_lists()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        info_label = QLabel("Select tools to display on the toolbar:")
        layout.addWidget(info_label)
        
        lists_layout = QHBoxLayout()
        
        available_layout = QVBoxLayout()
        available_label = QLabel("Available Tools:")
        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        available_layout.addWidget(available_label)
        available_layout.addWidget(self.available_list)
        lists_layout.addLayout(available_layout)
        
        buttons_layout = QVBoxLayout()
        buttons_layout.addStretch()
        self.add_button = QPushButton("Add →")
        self.add_button.clicked.connect(self.add_selected)
        buttons_layout.addWidget(self.add_button)
        
        self.remove_button = QPushButton("← Remove")
        self.remove_button.clicked.connect(self.remove_selected)
        buttons_layout.addWidget(self.remove_button)
        
        buttons_layout.addSpacing(20)
        
        self.move_up_button = QPushButton("Move Up")
        self.move_up_button.clicked.connect(self.move_up)
        buttons_layout.addWidget(self.move_up_button)
        
        self.move_down_button = QPushButton("Move Down")
        self.move_down_button.clicked.connect(self.move_down)
        buttons_layout.addWidget(self.move_down_button)
        
        buttons_layout.addStretch()
        lists_layout.addLayout(buttons_layout)
        
        selected_layout = QVBoxLayout()
        selected_label = QLabel("Toolbar Tools:")
        self.selected_list = QListWidget()
        self.selected_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        selected_layout.addWidget(selected_label)
        selected_layout.addWidget(self.selected_list)
        lists_layout.addLayout(selected_layout)
        
        layout.addLayout(lists_layout)
        
        dialog_buttons_layout = QHBoxLayout()
        dialog_buttons_layout.addStretch()
        
        self.reset_button = QPushButton("Reset to Default")
        self.reset_button.clicked.connect(self.reset_to_default)
        dialog_buttons_layout.addWidget(self.reset_button)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        dialog_buttons_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        dialog_buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(dialog_buttons_layout)
    
    def populate_lists(self):
        self.available_list.clear()
        self.selected_list.clear()
        
        for tool_id, tool_name in self.available_tools.items():
            if tool_id not in self.selected_tools:
                item = QListWidgetItem(tool_name)
                item.setData(Qt.ItemDataRole.UserRole, tool_id)
                self.available_list.addItem(item)
        
        for tool_id in self.selected_tools:
            if tool_id in self.available_tools:
                tool_name = self.available_tools[tool_id]
                item = QListWidgetItem(tool_name)
                item.setData(Qt.ItemDataRole.UserRole, tool_id)
                self.selected_list.addItem(item)
    
    def add_selected(self):
        selected_items = self.available_list.selectedItems()
        for item in selected_items:
            tool_id = item.data(Qt.ItemDataRole.UserRole)
            if tool_id not in self.selected_tools:
                self.selected_tools.append(tool_id)
        self.populate_lists()
    
    def remove_selected(self):
        selected_items = self.selected_list.selectedItems()
        for item in selected_items:
            tool_id = item.data(Qt.ItemDataRole.UserRole)
            if tool_id in self.selected_tools:
                self.selected_tools.remove(tool_id)
        self.populate_lists()
    
    def move_up(self):
        current_row = self.selected_list.currentRow()
        if current_row > 0:
            tool_id = self.selected_tools.pop(current_row)
            self.selected_tools.insert(current_row - 1, tool_id)
            self.populate_lists()
            self.selected_list.setCurrentRow(current_row - 1)
    
    def move_down(self):
        current_row = self.selected_list.currentRow()
        if current_row < len(self.selected_tools) - 1 and current_row >= 0:
            tool_id = self.selected_tools.pop(current_row)
            self.selected_tools.insert(current_row + 1, tool_id)
            self.populate_lists()
            self.selected_list.setCurrentRow(current_row + 1)
    
    def reset_to_default(self):
        self.selected_tools = []
        self.populate_lists()
    
    def get_selected_tools(self):
        return self.selected_tools

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListView, 
                               QLineEdit, QPushButton, QLabel, QSplitter, QMessageBox)
from PySide6.QtCore import Qt, QModelIndex, Signal
from PySide6.QtGui import QKeySequence, QKeyEvent, QStandardItemModel, QStandardItem
from gui_controls.list_control import Listctrl, ListItem
from app_config import key_config
import re

class KeyCaptureEdit(QLineEdit):
    keySequenceCaptured = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Press keys to capture hotkey...")
        self.setReadOnly(True)
        self.captured_sequence = ""
        
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()
        
        if key in (Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return
            
        sequence_parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            sequence_parts.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            sequence_parts.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            sequence_parts.append("Shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            sequence_parts.append("Win")
            
        key_name = QKeySequence(key).toString()
        if key_name:
            sequence_parts.append(key_name)
            
        self.captured_sequence = "+".join(sequence_parts)
        self.setText(self.captured_sequence)
        self.keySequenceCaptured.emit(self.captured_sequence)
        
    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self.captured_sequence:
            self.keySequenceCaptured.emit(self.captured_sequence)

class HotkeysDialog(QDialog):
    def __init__(self, parent=None, reset_callback=None):
        super().__init__(parent)
        self.reset_callback = reset_callback
        self.current_category = None
        self.current_hotkey_row = -1
        self.key_capture_edit = None
        
        self.setWindowTitle("Hotkeys Configuration")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(800, 600)
        self.setMinimumSize(600, 400)
        
        self.setup_ui()
        self.populate_categories()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        self.category_model = QStandardItemModel()
        self.category_list = QListView()
        self.category_list.setModel(self.category_model)
        self.category_list.setMaximumWidth(200)
        self.category_list.selectionModel().currentChanged.connect(self.category_changed)
        
        self.hotkeys_list = Listctrl()
        self.hotkeys_list.column(0, "Action")
        self.hotkeys_list.column(1, "Shortcut")
        
        splitter.addWidget(self.category_list)
        splitter.addWidget(self.hotkeys_list)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        button_layout = QHBoxLayout()
        
        self.reset_button = QPushButton("Reset to Default")
        self.reset_button.clicked.connect(self.reset_to_default)
        
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_changes)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
        
        self.hotkeys_list.itemClicked.connect(self.hotkey_item_clicked)
        
    def populate_categories(self):
        self.category_model.clear()
        for category in key_config.key_dict.keys():
            item = QStandardItem(category)
            item.setData(category, Qt.ItemDataRole.UserRole)
            self.category_model.appendRow(item)
            
    def category_changed(self, current: QModelIndex, previous: QModelIndex):
        if not current.isValid():
            return
            
        category = current.data(Qt.ItemDataRole.UserRole)
        self.current_category = category
        self.populate_hotkeys(category)
        
    def populate_hotkeys(self, category):
        self.hotkeys_list.clearAll()
        
        if category not in key_config.key_config:
            return
            
        self.hotkeys_list.column(0, "Action")
        self.hotkeys_list.column(1, "Shortcut")
        
        for action, shortcut in key_config.key_config[category].items():
            self.hotkeys_list.appendRow({
                "0": action,
                "1": shortcut
            })
            
    def hotkey_item_clicked(self, item):
        if not self.current_category:
            return
            
        row = self.hotkeys_list.row(item)
        if row == 0:
            return
            
        self.current_hotkey_row = row
        
        if self.key_capture_edit:
            self.key_capture_edit.deleteLater()
            
        self.key_capture_edit = KeyCaptureEdit(self)
        self.key_capture_edit.keySequenceCaptured.connect(self.update_hotkey)
        
        if isinstance(item, ListItem):
            shortcut_label = item.Widget.labels.get("1_label")
            if shortcut_label:
                rect = shortcut_label.geometry()
                self.key_capture_edit.setGeometry(rect)
                self.key_capture_edit.show()
                self.key_capture_edit.setFocus()
                
    def update_hotkey(self, sequence):
        if not self.current_category or self.current_hotkey_row == -1:
            return
            
        if not key_config.is_valid_hotkey(sequence):
            QMessageBox.warning(self, "Invalid Hotkey", 
                              "The entered hotkey sequence is not valid.")
            return
            
        item = self.hotkeys_list.item(self.current_hotkey_row)
        if item and isinstance(item, ListItem):
            action = item.Widget.columns[0]
            
            key_config.key_config[self.current_category][action] = sequence
            
            self.hotkeys_list.editColumn(self.current_hotkey_row, 1, sequence)
            
        if self.key_capture_edit:
            self.key_capture_edit.hide()
            
    def reset_to_default(self):
        reply = QMessageBox.question(self, "Reset to Default",
                                   "Are you sure you want to reset all hotkeys to default?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            key_config.keysToDefault()
            if self.current_category:
                self.populate_hotkeys(self.current_category)
                
    def apply_changes(self):
        key_config.saveConfig()
        key_config.apply_global_hotkeys()
        if self.reset_callback:
            self.reset_callback()
            
    def accept(self):
        self.apply_changes()
        super().accept()
        super().accept()

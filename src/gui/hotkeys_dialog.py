from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QKeySequenceEdit, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from app_config import key_config

class HotkeysDialog(QDialog):
    def __init__(self, parent=None, reset_callback=None):
        super().__init__(parent)
        self.reset_callback = reset_callback
        self.current_editor = None
        self.current_editor_item = None
        self.setWindowTitle("Hotkeys Configuration")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(700, 500)
        self.setMinimumSize(600, 400)
        self.setup_ui()
        self.populate_tree()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Action", "Shortcut"])
        self.tree.setAlternatingRowColors(True)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.keyPressEvent = self.tree_key_press_event
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.tree.header().setSectionsMovable(False)
        self.tree.header().setSectionsClickable(False)
        layout.addWidget(self.tree)

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

    def tree_key_press_event(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            current_item = self.tree.currentItem()
            if current_item and current_item.parent() is not None:
                self.start_editing(current_item, 1)
                return
        QTreeWidget.keyPressEvent(self.tree, event)

    def populate_tree(self):
        self.tree.clear()
        for category_name in key_config.key_dict.keys():
            category_item = QTreeWidgetItem(self.tree, [category_name, ""])
            category_item.setFlags(category_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            category_item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, f"Category: {category_name}")
            if category_name in key_config.key_config:
                for action, shortcut in key_config.key_config[category_name].items():
                    action_item = QTreeWidgetItem(category_item, [action, shortcut])
                    action_item.setData(0, Qt.ItemDataRole.UserRole, category_name)
                    desc = f"{action} in {category_name}, current shortcut: {shortcut if shortcut else 'none'}"
                    action_item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc)
                    action_item.setData(1, Qt.ItemDataRole.AccessibleDescriptionRole, desc)
                    action_item.setFlags(action_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tree.addTopLevelItem(category_item)
            category_item.setExpanded(True)
        self.tree.header().setSectionsMovable(False)
        self.tree.header().setSectionsClickable(False)

    def on_item_clicked(self, item, column):
        if item.parent() is not None and column == 1:
            self.start_editing(item, column)

    def on_item_double_clicked(self, item, column):
        if item.parent() is not None and column == 1:
            self.start_editing(item, column)

    def start_editing(self, item, column):
        if column != 1 or item.parent() is None:
            return
        
        if self.current_editor is not None:
            self.finish_editing()
        
        existing_text = item.text(1)
        editor = QKeySequenceEdit()
        editor.setKeySequence(QKeySequence(existing_text))
        editor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        editor.setAccessibleDescription("Shortcut editor. Press the desired key combination; press Enter or change focus to accept.")
        editor.editingFinished.connect(self.finish_editing)
        
        self.current_editor = editor
        self.current_editor_item = item
        self.tree.setItemWidget(item, 1, editor)
        editor.setFocus()

    def finish_editing(self):
        if self.current_editor is None or self.current_editor_item is None:
            return
        
        new_seq = self.current_editor.keySequence().toString()
        item = self.current_editor_item
        parent = item.parent()
        
        if new_seq and parent is not None:
            category = parent.text(0)
            action_text = item.text(0)
            key_config.key_config[category][action_text] = new_seq
            item.setText(1, new_seq)
            desc = f"{action_text} in {category}, current shortcut: {new_seq}"
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc)
            item.setData(1, Qt.ItemDataRole.AccessibleDescriptionRole, desc)
        
        try:
            self.tree.setItemWidget(item, 1, None)
        except Exception:
            pass
        
        self.current_editor.deleteLater()
        self.current_editor = None
        self.current_editor_item = None

    def reset_to_default(self):
        reply = QMessageBox.question(
            self,
            "Reset to Default",
            "Are you sure you want to reset all hotkeys to default?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            key_config.keysToDefault()
            self.populate_tree()

    def apply_changes(self):
        key_config.saveConfig()
        key_config.apply_global_hotkeys()
        if self.reset_callback:
            self.reset_callback()

    def accept(self):
        if self.current_editor:
            self.finish_editing()
        self.apply_changes()
        super().accept()

    def reject(self):
        if self.current_editor:
            try:
                self.tree.setItemWidget(self.current_editor_item, 1, None)
            except Exception:
                pass
            self.current_editor.deleteLater()
            self.current_editor = None
            self.current_editor_item = None
        super().reject()

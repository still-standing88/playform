import os
from PySide6.QtWidgets import QListWidget, QMenu, QMessageBox
from PySide6.QtCore import Signal, Qt, Slot
from PySide6.QtGui import QAction
from app_db import UserFiles
from utilities.util_gui import contextMenu, messageBox


class RecentsWidget(QListWidget):
    itemRequested = Signal(str)
    
    def __init__(self, user_db: UserFiles, parent=None):
        super().__init__(parent)
        self.user_db = user_db
        self.max_recent_files = 50
        self.path_mapping = {}
        self.setAccessibleName("Recent files list")
        self.setAccessibleDescription("List of recently opened media files")
        self.setAlternatingRowColors(True)
        self.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setToolTip("Double-click or press Enter on a file to open it")
        
        self.load_recents()
        
    def load_recents(self):
        self.clear()
        self.path_mapping.clear()
        try:
            recents = self.user_db.get_recents(self.max_recent_files)
            for recent_path in recents:
                filename = os.path.basename(recent_path)
                self.path_mapping[filename] = recent_path
                self.addItem(filename)
        except Exception as e:
            print(f"Error loading recents: {e}")
    
    def add_recent(self, file_path: str):
        try:
            self.user_db.add_recent(file_path)
            filename = os.path.basename(file_path)
            
            for i in range(self.count()):
                if self.item(i).text() == filename:
                    old_filename = self.takeItem(i).text()
                    if old_filename in self.path_mapping:
                        del self.path_mapping[old_filename]
                    break
            
            self.path_mapping[filename] = file_path
            self.insertItem(0, filename)
            
            while self.count() > self.max_recent_files:
                removed_item = self.takeItem(self.count() - 1)
                if removed_item and removed_item.text() in self.path_mapping:
                    del self.path_mapping[removed_item.text()]
                
        except Exception as e:
            messageBox("Error", f"Failed to add recent file: {e}")
    
    @Slot()
    def clear_recents(self):
        reply = QMessageBox.question(self, "Clear Recent Files", 
                                   "Are you sure you want to clear all recent files?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.user_db.clear_recents()
                self.clear()
                self.path_mapping.clear()
            except Exception as e:
                messageBox("Error", f"Failed to clear recent files: {e}")
    
    def show_context_menu(self, position):
        menu = QMenu(self)
        
        clear_action = QAction("Clear All Recent Files", self)
        clear_action.triggered.connect(self.clear_recents)
        menu.addAction(clear_action)
        
        menu.exec(self.mapToGlobal(position))
    
    @Slot(object)
    def on_item_activated(self, item):
        if item:
            filename = item.text()
            if filename in self.path_mapping:
                self.itemRequested.emit(self.path_mapping[filename])
    
    def get_recent_files_list(self):
        return [self.path_mapping.get(self.item(i).text(), self.item(i).text()) for i in range(min(10, self.count())) if self.item(i).text() in self.path_mapping]

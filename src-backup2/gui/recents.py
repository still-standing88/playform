from PySide6.QtWidgets import QListWidget, QMenu, QMessageBox
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction
from app_db import UserFiles
from utilities.util_gui import contextMenu, messageBox


class RecentsWidget(QListWidget):
    itemRequested = Signal(str)
    
    def __init__(self, user_db: UserFiles, parent=None):
        super().__init__(parent)
        self.user_db = user_db
        self.max_recent_files = 50
        self.setAccessibleName("Recent files list")
        self.setAccessibleDescription("List of recently opened media files")
        self.setAlternatingRowColors(True)
        self.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        
        contextMenu(self, self.show_context_menu)
        self.itemDoubleClicked.connect(self.on_item_activated)
        
        self.load_recents()
        
    def load_recents(self):
        self.clear()
        try:
            recents = self.user_db.get_recents(self.max_recent_files)
            for recent_path in recents:
                self.addItem(recent_path)
        except Exception as e:
            print(f"Error loading recents: {e}")
    
    def add_recent(self, file_path: str):
        try:
            self.user_db.add_recent(file_path)
            for i in range(self.count()):
                if self.item(i).text() == file_path:
                    self.takeItem(i)
                    break
            
            self.insertItem(0, file_path)
            
            while self.count() > self.max_recent_files:
                self.takeItem(self.count() - 1)
                
        except Exception as e:
            messageBox("Error", f"Failed to add recent file: {e}")
    
    def clear_recents(self):
        reply = QMessageBox.question(self, "Clear Recent Files", 
                                   "Are you sure you want to clear all recent files?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.user_db.clear_recents()
                self.clear()
            except Exception as e:
                messageBox("Error", f"Failed to clear recent files: {e}")
    
    def show_context_menu(self, position):
        menu = QMenu(self)
        
        clear_action = QAction("Clear All Recent Files", self)
        clear_action.triggered.connect(self.clear_recents)
        menu.addAction(clear_action)
        
        menu.exec(self.mapToGlobal(position))
    
    def on_item_activated(self, item):
        if item:
            self.itemRequested.emit(item.text())
    
    def get_recent_files_list(self):
        return [self.item(i).text() for i in range(min(10, self.count()))]

import os
from PySide6.QtWidgets import QListWidget, QMenu, QMessageBox
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QAction
from app_db import UserFiles
from utilities.util_gui import contextMenu, messageBox


class FavoritesWidget(QListWidget):
    itemRequested = Signal(str)
    
    def __init__(self, user_db: UserFiles, parent=None):
        super().__init__(parent)
        self.user_db = user_db
        self.path_mapping = {}
        self.setAccessibleName("Favorites list")
        self.setAccessibleDescription("List of favorite media files")
        self.setAlternatingRowColors(True)
        self.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        
        contextMenu(self, self.show_context_menu)
        self.itemDoubleClicked.connect(self.on_item_activated)
        self.itemActivated.connect(self.on_item_activated)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setToolTip("Double-click or press Enter on a file to open it")

        self.load_favorites()
        
    def load_favorites(self):
        self.clear()
        self.path_mapping.clear()
        try:
            favorites = self.user_db.get_favorites()
            for fav_path in favorites:
                filename = os.path.basename(fav_path)
                self.path_mapping[filename] = fav_path
                self.addItem(filename)
        except Exception as e:
            print(f"Error loading favorites: {e}")
    
    def add_favorite(self, file_path: str):
        try:
            self.user_db.add_favorite(file_path)
            filename = os.path.basename(file_path)
            self.path_mapping[filename] = file_path
            self.addItem(filename)
        except Exception as e:
            messageBox("Error", f"Failed to add favorite: {e}")
    
    def remove_favorite(self, file_path: str):
        try:
            self.user_db.remove_favorite(file_path)
            filename_to_remove = None
            for filename, path in self.path_mapping.items():
                if path == file_path:
                    filename_to_remove = filename
                    break
            
            if filename_to_remove:
                for i in range(self.count()):
                    if self.item(i).text() == filename_to_remove:
                        self.takeItem(i)
                        break
                del self.path_mapping[filename_to_remove]
        except Exception as e:
            messageBox("Error", f"Failed to remove favorite: {e}")
    
    def clear_favorites(self):
        reply = QMessageBox.question(self, "Clear Favorites", 
                                   "Are you sure you want to clear all favorites?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.user_db.clear_favorites()
                self.clear()
                self.path_mapping.clear()
            except Exception as e:
                messageBox("Error", f"Failed to clear favorites: {e}")
    
    def show_context_menu(self, position):
        menu = QMenu(self)
        
        clear_action = QAction("Clear All Favorites", self)
        clear_action.triggered.connect(self.clear_favorites)
        menu.addAction(clear_action)
        
        if self.itemAt(position):
            menu.addSeparator()
            remove_action = QAction("Remove from Favorites", self)
            remove_action.triggered.connect(self.remove_current_favorite)
            menu.addAction(remove_action)
        
        menu.exec(self.mapToGlobal(position))
    
    def remove_current_favorite(self):
        current_item = self.currentItem()
        if current_item:
            filename = current_item.text()
            if filename in self.path_mapping:
                self.remove_favorite(self.path_mapping[filename])
    
    def on_item_activated(self, item):
        if item:
            filename = item.text()
            if filename in self.path_mapping:
                self.itemRequested.emit(self.path_mapping[filename])

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
        self.setAccessibleName("Favorites list")
        self.setAccessibleDescription("List of favorite media files")
        self.setAlternatingRowColors(True)
        self.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        
        contextMenu(self, self.show_context_menu)
        self.itemDoubleClicked.connect(self.on_item_activated)
        
        self.load_favorites()
        
    def load_favorites(self):
        self.clear()
        try:
            favorites = self.user_db.get_favorites()
            for fav_path in favorites:
                self.addItem(fav_path)
        except Exception as e:
            print(f"Error loading favorites: {e}")
    
    def add_favorite(self, file_path: str):
        try:
            self.user_db.add_favorite(file_path)
            self.addItem(file_path)
        except Exception as e:
            messageBox("Error", f"Failed to add favorite: {e}")
    
    def remove_favorite(self, file_path: str):
        try:
            self.user_db.remove_favorite(file_path)
            for i in range(self.count()):
                if self.item(i).text() == file_path:
                    self.takeItem(i)
                    break
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
            self.remove_favorite(current_item.text())
    
    def on_item_activated(self, item):
        if item:
            self.itemRequested.emit(item.text())

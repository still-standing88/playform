from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PySide6.QtCore import Signal
from app_db import UserFiles
from .favorites import FavoritesWidget
from .recents import RecentsWidget


class RecentsAndFavoritesWidget(QWidget):
    itemRequested = Signal(str)
    
    def __init__(self, user_db: UserFiles, parent=None):
        super().__init__(parent)
        self.user_db = user_db
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("recentsAndFavoritesTabWidget")
        
        self.favorites_widget = FavoritesWidget(self.user_db, self)
        self.favorites_widget.itemRequested.connect(self.itemRequested.emit)
        self.tab_widget.addTab(self.favorites_widget, "Favorites")
        
        self.recents_widget = RecentsWidget(self.user_db, self)
        self.recents_widget.itemRequested.connect(self.itemRequested.emit)
        self.tab_widget.addTab(self.recents_widget, "Recents")
        
        layout.addWidget(self.tab_widget)
    
    def add_favorite(self, file_path: str):
        self.favorites_widget.add_favorite(file_path)
    
    def remove_favorite(self, file_path: str):
        self.favorites_widget.remove_favorite(file_path)
    
    def load_favorites(self):
        self.favorites_widget.load_favorites()
    
    def add_recent(self, file_path: str):
        self.recents_widget.add_recent(file_path)
    
    def load_recents(self):
        self.recents_widget.load_recents()
    
    def get_recent_files_list(self):
        return self.recents_widget.get_recent_files_list()

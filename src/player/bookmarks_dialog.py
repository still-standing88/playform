from typing import List
from PySide6.QtWidgets import QDialog, QListWidget, QDialogButtonBox, QVBoxLayout, QMenu
from PySide6.QtCore import Qt, Signal


class BookmarksDialog(QDialog):
    deleteRequested = Signal(int)
    clearAllRequested = Signal()


    def __init__(self, bookmarks: List[float], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bookmarks")
        self.setModal(True)
        self.resize(300, 400)
        
        layout = QVBoxLayout(self)
        
        self.bookmarks_list = QListWidget(self)
        for i, bookmark in enumerate(bookmarks):
            minutes = int(bookmark // 60)
            seconds = int(bookmark % 60)
            self.bookmarks_list.addItem(f"Mark {i+1}: {minutes:02d}:{seconds:02d}")
        self.bookmarks_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bookmarks_list.customContextMenuRequested.connect(self._open_context_menu)
        
        layout.addWidget(self.bookmarks_list)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_selected_bookmark_index(self):
        current_row = self.bookmarks_list.currentRow()
        return current_row if current_row >= 0 else None

    def _open_context_menu(self, pos):
        menu = QMenu(self)
        delete_action = menu.addAction("Delete selected")
        clear_action = menu.addAction("Clear all")
        action = menu.exec(self.bookmarks_list.mapToGlobal(pos))
        if action == delete_action:
            idx = self.get_selected_bookmark_index()
            if idx is not None:
                self.deleteRequested.emit(idx)
        elif action == clear_action:
            self.clearAllRequested.emit()

    def remove_bookmark_at(self, index:int):
        if 0 <= index < self.bookmarks_list.count():
            item = self.bookmarks_list.takeItem(index)
            del item

    def clear_all(self):
        self.bookmarks_list.clear()
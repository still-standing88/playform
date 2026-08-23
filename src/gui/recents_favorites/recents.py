import os
from PySide6.QtWidgets import QListWidget, QMenu, QMessageBox
from PySide6.QtCore import Signal, Qt, Slot
from PySide6.QtGui import QAction
from app_db import UserFiles
from app_db.user_db import FileCategory
from utilities.util_gui import contextMenu, messageBox


class RecentsWidget(QListWidget):
    itemRequested = Signal(str)
    
    def __init__(self, user_db: UserFiles, parent=None):
        super().__init__(parent)
        self.user_db = user_db
        self.max_recent_files = 50
        self.path_mapping = {}
        self.setAccessibleName(_("Recent files list"))
        self.setAccessibleDescription(_("List of recently opened media files"))
        self.setAlternatingRowColors(True)
        self.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setToolTip(_("Double-click or press Enter on a file to open it"))

        contextMenu(self, self.show_context_menu)
        self.itemDoubleClicked.connect(self.on_item_activated)
        self.itemActivated.connect(self.on_item_activated)

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
            messageBox(_("Error"), _("Error loading recents: {error}").format(error=e))
    
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
            messageBox(_("Error"), _("Failed to add recent file: {error}").format(error=e))

    @Slot()
    def clear_recents(self):
        reply = QMessageBox.question(self, _("Clear Recent Files"),
                                   _("Are you sure you want to clear all recent files?"),
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.user_db.clear_recents()
                self.clear()
                self.path_mapping.clear()
            except Exception as e:
                messageBox(_("Error"), _("Failed to clear recent files: {error}").format(error=e))

    @Slot()
    def remove_current_recent(self):
        item = self.currentItem()
        if item is None:
            return
        path = self.path_mapping.get(item.text())
        if not path:
            return
        try:
            self.user_db.remove_recent(path)
            self.takeItem(self.row(item))
            if item.text() in self.path_mapping:
                del self.path_mapping[item.text()]
        except Exception as e:
            messageBox(_("Error"), _("Failed to remove recent file: {error}").format(error=e))

    @Slot()
    def clear_nonexistent_recents(self):
        try:
            removed = self.user_db.prune_missing(FileCategory.RECENT)
            self.load_recents()
            messageBox(_("Clear Nonexistent"), _("{count} missing entr(y/ies) removed.").format(count=removed))
        except Exception as e:
            messageBox(_("Error"), _("Failed to prune recents: {error}").format(error=e))

    def show_context_menu(self, position):
        menu = QMenu(self)

        remove_action = QAction(_("Remove This Track"), self)
        remove_action.setEnabled(self.currentItem() is not None)
        remove_action.triggered.connect(self.remove_current_recent)
        menu.addAction(remove_action)

        clear_missing_action = QAction(_("Clear Nonexistent Tracks"), self)
        clear_missing_action.triggered.connect(self.clear_nonexistent_recents)
        menu.addAction(clear_missing_action)

        menu.addSeparator()

        clear_action = QAction(_("Clear All Recent Files"), self)
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

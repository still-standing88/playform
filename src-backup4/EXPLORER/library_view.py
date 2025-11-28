import os

from typing import Optional, Callable, List
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu
from PySide6.QtCore import Qt as qt

from utilities.util_gui import  contextMenu, messageBox, menuItem
from app_db import UserFiles
from .library_dialogs import NewDialog, EditDialog


class LibraryView(QTreeWidget):


    def __init__(self, user_db:UserFiles, parent, **kw):
        self._user_db:UserFiles = user_db
        super().__init__(parent)
        self.navigate_callback:Optional[Callable[[str], None]] = kw.get("navigate_callback", None)
        self.itemClicked.connect(self.navigateTo)
        self.itemActivated.connect(self.navigateTo)

        contextMenu(self, self.context_menu)
        self.setColumnCount(1)
        self.setHeaderLabels(['folder'])

        self._folder_paths:List[str] = []
        self.lib = QTreeWidgetItem(self)
        self.lib.setText(0, 'library')
        self.insertTopLevelItem(0, self.lib)
        self.listContents()


    def add_path(self, path:str):
        if path in self._folder_paths:
            messageBox('path in library', 'this path already existsin the library')
            return 0

        self._user_db.add_library_folder(path)
        self.listContents()

    def new(self):
        d = NewDialog(self.add_callback, self.parent())
        d.exec()

    def modify(self):
        path = self.currentItem().text(0)
        if path in self._folder_paths:
            d = EditDialog(self.edit_callback, self.parent, path)
            d.exec()

    def delete(self):
        current_item = self.currentItem()
        if current_item and current_item.text(0) != "library":
            item_name = current_item.text(0)
            # Find the full path from _folder_paths based on basename
            item_path = None
            for path in self._folder_paths:
                if os.path.basename(path) == item_name:
                    item_path = path
                    break
            
            if item_path:
                self.lib.takeChild(self.lib.indexOfChild(current_item))
                self._user_db.remove_library_folder(item_path)

    def navigateTo(self):
        current_item = self.currentItem()
        if current_item is None or current_item.text(0) == "library":
            return
            
        item_name = current_item.text(0)
        item_path = None
        for path in self._folder_paths:
            if os.path.basename(path) == item_name:
                item_path = path
                break
                
        if self.navigate_callback is not None and item_path is not None:
            self.navigate_callback(item_path)

    def add_callback(self, path:str):
        if os.path.exists(path) == False:
            messageBox('error', 'path not found')
            return 0

        name = os.path.basename(path)
        if path in self._folder_paths:
            messageBox('error', 'path already exists')
            return 0

        self._user_db.add_library_folder(path)
        self.listContents()
        self.setCurrentItem(self.findItems(os.path.basename(path), qt.MatchFlag.MatchExactly, 0)[0])

    def edit_callback(self, path:str):
        if os.path.exists(path) == False:
            messageBox('error', 'path not found')
            return 0


        self.listContents()
        name = os.path.basename(path)
        self.setCurrentItem(self.findItems(os.path.basename(path), qt.MatchFlag.MatchExactly, 0)[0])


    def listContents(self):
        self._folder_paths.clear()
        self.Clear()
        self._folder_paths = self._user_db.get_library_folders()

        for item in self._folder_paths:
            folder = QTreeWidgetItem(self.lib)
            folder.setText(0, os.path.basename(item))
            self.lib.addChild(folder)

    def Clear(self):
        while self.lib.childCount() > 0:
            item = self.lib.child(0)
            self.lib.removeChild(item)

    def clear_library(self):
        self.clear()
        self._folder_paths.clear()
        self._user_db.clear_library_folders()

    def context_menu(self, event):
        item = self.currentItem().text(0)
        menu = QMenu()
        menuItem(menu, 'Add new', self.new, self)
        if self.currentItem().text(0) != "library":
            #menuItem(menu, 'modify path', self.modify, self)
            menuItem(menu, 'Remove', self.delete, self)
            menuItem(menu, 'Clear library', self.clear_library, self)
        menu.exec()

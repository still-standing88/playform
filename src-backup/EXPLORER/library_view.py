import os

from typing import Optional, Callable, List
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu
from PySide6.QtCore import Qt as qt

from utilities.util_gui import  contextMenu, messageBox, menuItem
from app_db import UserFiles
from library_dialogs import NewDialog, EditDialog


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
        item_path = self.currentItem().text(0)
        self.lib.takeChild(self.lib.indexOfChild(self.currentItem()))
        self._user_db.remove_library_folder(item_path)

    def navigateTo(self):
        name = self.currentItem().text(0)
        if self.navigate_callback is not None:
            self.navigate_callback(name)

    def add_callback(self, path:str):
        if os.path.exists(path) == False:
            messageBox('error', 'path not found')
            return 0

        name = os.path.basename(path)
        if path in self.folder_paths:
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
        self.folder_paths = self._user_db.get_library_folders()
        for item in self._folder_paths:
            folder = QTreeWidgetItem(self.lib)
            folder.setText(0, os.path.basename(item))
            self.lib.addChild(folder)

    def Clear(self):
        count = self.lib.childCount()
        for index in range(0, count + 1):
            item = self.lib.child(index)
            self.lib.removeChild(item)

    def clear_library(self):
        self.clear()
        self.folder_paths.clear()
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

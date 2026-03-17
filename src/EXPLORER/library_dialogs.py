import os

from typing import Optional, Callable
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, 
QFileDialog, QTextEdit, QPlainTextEdit, QLabel, QPushButton, )
from PySide6.QtCore import Qt as qt, Slot


class libraryDialog(QDialog):


    def __init__(self, title, parent = None, path = None, on_confirm_callback:Optional[Callable[[str], None]] = None):
        self.path:Optional[str] = path
        self.title = title
        self.on_confirm_callback = on_confirm_callback

        super().__init__(parent)
        self.setWindowModality(qt.WindowModality.WindowModal)
        self.setWindowTitle(self.title)

        self.ui()
        self.layout()


    def ui(self):
        self.pathLabel = QLabel(_("path"), self)
        self.path_field = QPlainTextEdit(self)
        self.path_field.setReadOnly(False)
        self.path_field.setTabChangesFocus(True)
        self.brows_button = QPushButton(_("Browse"), self)
        self.confirm_button = QPushButton(_("confirm"), self)
        self.cancel_button = QPushButton(_("cancel"), self)
        self.brows_button.clicked.connect(self.onBrows)
        self.confirm_button.clicked.connect(self.onConfirm)
        self.cancel_button.clicked.connect(self.close)

    def layout(self):
        self.Layout = QVBoxLayout(self)
        topLayout = QHBoxLayout()
        pathLayout = QVBoxLayout()
        pathLayout.addWidget(self.pathLabel)
        pathLayout.addWidget(self.path_field)
        topLayout.addLayout(pathLayout)
        topLayout.addWidget(self.brows_button)
        self.Layout.addLayout(topLayout)
        bottomLayout = QHBoxLayout()
        bottomLayout.addWidget(self.confirm_button)
        bottomLayout.addWidget(self.cancel_button)
        self.Layout.addLayout(bottomLayout)

    @Slot()
    def onBrows(self):
        path_dialog = QFileDialog.getExistingDirectory(self)
        if path_dialog:
            self.path = path_dialog
            self.path_field.setPlainText(path_dialog)

    @Slot()
    def onConfirm(self):
        entered_path = self.path_field.toPlainText().strip()
        self.path = entered_path
        if self.on_confirm_callback:
            self.on_confirm_callback(entered_path)
        self.close()


class NewDialog(libraryDialog):


    def __init__(self, on_confirm_callback, parent=None,path=None):
        super().__init__(_("Add new path to library"), parent, path, on_confirm_callback)


class EditDialog(libraryDialog):

    def __init__(self, on_confirm_callback, parent=None,path=None):
        super().__init__(_("Add existing path"), parent, path, on_confirm_callback)
        self.path_field.setPlainText(self.path or "")

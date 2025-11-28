import os
from PySide6.QtWidgets import (QDialog, QFileDialog, QVBoxLayout, QHBoxLayout,
QLabel, QPushButton, QPlainTextEdit, QListWidget, QToolButton)
from PySide6.QtCore import Qt as qt
from common_controls import CancelButton, ConfirmButton


class InfoDialog(QDialog):


    def __init__(self,title,text,parent):
       super().__init__(parent)
       self.text = text
       self.setWindowModality(qt.WindowModality.WindowModal)
       self.setWindowTitle(title)
       self.ui()
       self.Layout()

    def ui(self):
       self.text_field = QPlainTextEdit(self)
       self.close_button = QPushButton("Close",self)
       self.text_field.setReadOnly(True)
       self.text_field.setTabChangesFocus(True)
       self.text_field.setPlainText(self.text)
       self.close_button.clicked.connect(self.close)
       self.close_button.setShortcut("Alt+C")

    def Layout(self):
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.addWidget(self.text_field)
        self.mainLayout.addWidget(self.close_button)

class FileDialog(QDialog):


    def __init__(self,title, flags, parent=None):
        self.title = title
        self.files = []
        self.flags = flags
        self.fd = QFileDialog()

        self.fd.setFileMode(QFileDialog.fileMode.ExistingFiles)
        self.fd.setNameFilter(self.flags)

        super().__init__(parent)
        self.setWindowTitle(self.title)
        self.setWindowModality(qt.WindowModality.WindowModal)
        self.ui()
        self.Layout()
        self.setLayout(self.mainLayout)


    def ui(self):
        self.files_list = QListWidget(self)
        self.browse_btn = QToolButton(self)
        self.browse_btn.setText("browse")
        self.confirm_btn = ConfirmButton("Confirm",self)
        self.cancel_btn = CancelButton("Cancel",)
        self.browse_btn.clicked.connect(self.onbrowse)
        self.confirm_btn.clicked.connect(self.onConfirm)
        self.cancel_btn.clicked.connect(self.close)

    def Layout(self):
        self.mainLayout = QVBoxLayout()
        self.mainLayout.addWidget(self.files_list)
        self.mainLayout.addWidget(self.browse_btn)
        bottom_btn_layout = QHBoxLayout()
        bottom_btn_layout.addWidget(self.confirm_btn)
        bottom_btn_layout.addWidget(self.cancel_btn)
        self.mainLayout.addLayout(bottom_btn_layout)


    def onbrowse(self):
        if self.fd.exec() == QDialog.DialogCode.Accepted:
            selected = self.fd.selectedFiles()
            if len(selected) >0:
                for file in selected:
                    self.files.append(file)
                self.updateList()
            self.fd.selectedFiles().clear()

    def updateList(self):
        self.files_list.clear()
        for file in self.files:
            self.files_list.addItem(os.path.basename(file))

    def onConfirm(self):
        self.close()

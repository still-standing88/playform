from PySide6.QtWidgets import QApplication, QWidget, QMenu, QMessageBox
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt as qt

def menuItem(menu:QMenu, item:str, method,parent:QWidget):
    menu_item = QAction(item,parent)
    menu_item.triggered.connect(method)
    menu.addAction(menu_item)

def contextMenu(widget:QWidget,method):
    widget.setContextMenuPolicy(qt.ContextMenuPolicy.CustomContextMenu)
    widget.customContextMenuRequested.connect(method)

def messageBox(title,message):
    msg_box = QMessageBox()
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.exec()

def hasFocus(object): return QApplication.focusObject() == object

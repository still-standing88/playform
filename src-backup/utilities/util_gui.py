def menuItem(menu,item,method,parent):
    menu_item = QAction(item,parent)
    menu_item.triggered.connect(method)
    menu.addAction(menu_item)

def contextMenu(widget,method):
    widget.setContextMenuPolicy(qt.CustomContextMenu)
    widget.customContextMenuRequested.connect(method)

def messageBox(title,message):
    msg_box = QMessageBox()
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.exec()

def hasFocus(object): return QApplication.focusObject() == object

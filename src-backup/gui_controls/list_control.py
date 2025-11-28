from PySide6.QtWidgets import (QLabel, QListWidget, QListWidgetItem, QWidget,
QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame, QSpacerItem
, QListView, QAbstractItemView)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont


class HeaderWidget(QWidget):


    def __init__(self, parent=None):

        super().__init__(parent)
        self.headers = []
        self.labels = {}
        self._layout = QHBoxLayout(self)
        self._layout.setSpacing(10)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self.setStyleSheet("""
            background-color: #3498db;
            color: #fff;
            padding: 10px;
            font-weight: bold;
            border-bottom: 2px solid #2980b9;
        """)
        self.headerStyle = """
            color: #fff;
            font-weight: bold;
        """


class ListHeader(QListWidgetItem):


    def __init__(self, parent=None):
        self.parent = parent
        super().__init__()
        self.Widget = HeaderWidget()
        if self.parent:
            self.parent.addItem(self)
            self.parent.setItemWidget(self, self.Widget)
        self.setSizeHint(self.Widget.sizeHint())
        self.setFlags(self.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        self.Widget.setMinimumHeight(50)
        self.Widget.setMinimumWidth(200)

    def insertHeader(self, index, name):
        self.Widget.headers.insert(int(index), name)
        label = QLabel(name)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setFont(QFont("Arial", 12))
        label.setStyleSheet(self.Widget.headerStyle)
        self.Widget._layout.addWidget(label)
        self.Widget.labels[f"{name}_label"] = label

    def removeHeader(self, index):
        header = self.Widget.headers.pop(int(index))
        label = self.Widget.labels.pop(f"{header}_label")
        self.Widget._layout.removeWidget(label)
        label.deleteLater()


class ItemWidget(QWidget):


    def __init__(self, parent=None):
        super().__init__(parent)
        self.columns = []
        self.labels = {}
        self._layout = QHBoxLayout(self)
        self._layout.setSpacing(10)
        self._layout.setContentsMargins(5, 5, 5, 5)

        self.setStyleSheet("""
            background-color: #ecf0f1;
            padding: 10px;
            border-left: 1px solid lightgray;
            border-right: 1px solid lightgray;
            border-top: 1px solid lightgray;
            border-bottom: 1px solid #bdc3c7;
        """)
        self.columnStyle = """
            color: #333;
            font-weight: bold;
        """


class ListItem(QListWidgetItem):


    def __init__(self, parent=None):

        self.parent = parent
        super().__init__()
        self.Widget = ItemWidget()
        self.setSizeHint(self.Widget.sizeHint())
        if self.parent:
            self.parent.addItem(self)
            self.parent.setItemWidget(self, self.Widget)
        self.Widget.setMinimumHeight(50)
        self.Widget.setMinimumWidth(200)

    def insertColumn(self, index, name):
        self.Widget.columns.insert(int(index), name)
        label = QLabel(name)
        label.setStyleSheet(self.Widget.columnStyle)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setFont(QFont("Arial", 12))
        self.Widget._layout.addWidget(label)
        self.Widget._layout.update()
        self.Widget.labels[f"{name}_label"] = label

    def editColumn(self,index,text):
        column = self.Widget.columns[index]
        label = self.Widget.labels[f"{column}_label"]
        self.Widget.labels[f"{text}_label"] = label
        del self.Widget.labels[f"{column}_label"]
        self.Widget.columns[index] = text

        label.setText(text)
        print(label.text())

    def removeColumn(self, index):
        column = self.Widget.columns.pop(index)
        label = self.Widget.labels.pop(f"{column}_label")
        self.Widget._layout.removeWidget(label)
        self.Widget._layout.update()
        label.deleteLater()


class Listctrl(QListWidget):


    def __init__(self, parent=None):
        super().__init__(parent)
        self.headers = ListHeader(self)
        self.setViewMode(QListView.ViewMode.ListMode)

    def viewOptions(self):
        return super().viewOptions() # type:ignore

    def column(self, index, name):
        self.headers.insertHeader(index, name)
        self.updateDiscription()

    def removeColumn(self, index):
        count = self.count() - 1
        self.headers.removeHeader(index)
        for n in range(1, count + 1):
            item = self.item(n)
            if item and isinstance(item, ListItem):
                item.removeColumn(index)
        self.updateDiscription()

    def editColumn(self,row,column,text):
        item = self.item(row)
        if item and isinstance(item, ListItem):
            item.editColumn(column,text)
            text_desc = ""
            for col in self.headers.Widget.headers:
                text_desc+=f"{item.Widget.columns[self.headers.Widget.headers.index(col)]}, "
            item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, text_desc[0:len(text_desc) - 2])

    def appendRow(self, columns):
        text = ""
        item = ListItem(self)
        for column in columns:
            item.insertColumn(column, columns[column])
            text += f"{self.headers.Widget.headers[int(column)]}: {columns[column]},"
        item.setData(Qt.ItemDataRole.AccessibleDescriptionRole, text[0:len(text) - 1])
        self.updateDiscription()
        return item

    def removeRow(self, index):
        item = self.item(index)
        widget = self.itemWidget(item)
        self.removeItemWidget(item)
        self.takeItem(index)
        del item
        self.updateDiscription()

    def clearAll(self):
        column_count = len(self.headers.Widget.headers)
        row_count = self.count()
        if column_count>0:
            for n in range(0, column_count):
                    self.headers.removeHeader(column_count-1-n)
        if self.getRowCount()>0:
            for n in range(1, row_count+1):
                index = row_count-n
                if index == 0: break
                self.removeRow(index)
        self.updateDiscription()

    def indexFromColumn(self, name):
        current_item = self.currentItem()
        if current_item and isinstance(current_item, ListItem):
            return current_item.Widget.columns.index(name)
        return -1

    def columnFromIndex(self, index):
        current_item = self.currentItem()
        if current_item and isinstance(current_item, ListItem):
            return current_item.Widget.columns[index]
        return ""

    def getCurrentRowIndex(self):
        return self.row(self.currentItem())

    def getColumnCount(self):
        return len(self.headers.Widget.headers)

    def getRowCount(self):
        return self.count() - 1

    def updateDiscription(self):
        self.setAccessibleDescription(f"list view with {self.getColumnCount()} columns and {self.getRowCount()} rows")

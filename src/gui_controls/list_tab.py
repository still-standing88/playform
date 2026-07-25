from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
                               QListWidgetItem, QFrame, QSizePolicy, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

class TabInfo(QListWidgetItem):


    def __init__(self, name, widget, parent=None):
        super().__init__(parent)
        self.name = name
        self.widget = widget
        self._activated = False
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable)
        self.setCheckState(Qt.Unchecked)
        self.setTabLabel(self.name)
        
    def setTabLabel(self, text):
        self.name = text
        self.setText(self.name)
        
    def tabLabel(self):
        return self.name
        
    def setActivated(self, state):
        if isinstance(state, bool):
            if state:
                self.setCheckState(Qt.Checked)
            else:
                self.setCheckState(Qt.Unchecked)
            self._activated = state
        else:
            raise TypeError("state must be bool")
            
    def is_activated(self):
        return self._activated

class ListTabCtrl(QWidget):
    tabChanged = Signal(object, object)
    tabActivated = Signal()

    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.labels = []
        self.current_widget = None
        self.ui()
        self.layout_widgets()
        self.setLayout(self.main_layout)
        
    def ui(self):
        self.tabLabels = QListWidget(self)
        self.tabLabels.setViewMode(QListWidget.ListMode)
        self.tabLabels.setFlow(QListWidget.LeftToRight)
        self.tabLabels.setMovement(QListWidget.Static)
        
        self.tabLabels.setWrapping(False)
        self.tabLabels.setResizeMode(QListWidget.Adjust)
        
        self.tabLabels.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tabLabels.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.tabLabels.setFixedHeight(60)
        
        self.tabLabels.setSpacing(2)
        self.tabLabels.setGridSize(self.tabLabels.sizeHint())
        
        self.tabLabels.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.tabLabels.itemChanged.connect(self.onState)
        self.tabLabels.currentItemChanged.connect(self.onTabChange)
        
        self.line = QFrame(self)
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)
        self.line.setFixedHeight(2)
        
        self.tabView = QWidget(self)
        self.tabView.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
    def layout_widgets(self):
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)
        
        self.main_layout.addWidget(self.tabLabels)
        self.main_layout.addWidget(self.line)
        self.main_layout.addWidget(self.tabView, 1)
        
        self.tabLayout = QVBoxLayout(self.tabView)
        self.tabLayout.setContentsMargins(0, 0, 0, 0)
        
    def onState(self, item):
        # The checkbox is purely an enabled/disabled flag (e.g. "is this
        # audio effect applied") -- it does not affect which panel is
        # visible. Panel visibility follows selection only, like a normal
        # tab control; see onTabChange.
        if item is not None:
            if item.checkState() == Qt.CheckState.Checked:
                item.setActivated(True)
            elif item.checkState() == Qt.CheckState.Unchecked:
                item.setActivated(False)
            self.tabActivated.emit()

    def showTabWidget(self, widget):
        self.clearTabLayout()
        self.tabLayout.addWidget(widget)
        widget.show()
        self.current_widget = widget

    def hideTabWidget(self, widget):
        if widget is self.current_widget:
            self.clearTabLayout()
            self.current_widget = None

    def clearTabLayout(self):
        while self.tabLayout.count():
            child = self.tabLayout.takeAt(0)
            if child.widget():
                child.widget().hide()

    def onTabChange(self, current, previous):
        if current is not None and getattr(current, 'widget', None):
            self.showTabWidget(current.widget)
        elif self.current_widget:
            self.hideTabWidget(self.current_widget)
        self.tabChanged.emit(current, previous)
        
    def currentTab(self):
        return self.tabLabels.currentItem()
        
    def tabCount(self):
        return self.tabLabels.count()
        
    def addTab(self, label, widget):
        tab = TabInfo(label, widget, self.tabLabels)
        widget.setParent(self.tabView)
        widget.hide()
        self.labels.append(label)
        self.tabLabels.addItem(tab)
        
        item_size = self.tabLabels.sizeHintForIndex(self.tabLabels.indexFromItem(tab))
        tab.setSizeHint(item_size)
        
    def removeTab(self, index):
        if 0 <= index < self.tabCount():
            tab = self.tabLabels.item(index)
            if tab:
                if tab.name in self.labels:
                    self.labels.remove(tab.name)
                
                if hasattr(tab, 'widget') and tab.widget:
                    if tab.widget == self.current_widget:
                        self.current_widget = None
                    tab.widget.deleteLater()
                
                self.tabLabels.takeItem(index)
                
    def deleteTabs(self):
        if self.tabCount() > 0:
            for i in range(self.tabCount() - 1, -1, -1):
                self.removeTab(i)
            self.labels.clear()
            self.current_widget = None
            
    def indexOfTab(self, name):
        try:
            return self.labels.index(name)
        except ValueError:
            return -1
            
    def getTab(self, index):
        if 0 <= index < self.tabCount():
            return self.tabLabels.item(index)
        return None
        
    def sizeHint(self):
        from PySide6.QtCore import QSize
        return self.tabLabels.sizeHint() + self.tabView.sizeHint()
        
    def minimumSizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(300, 150)
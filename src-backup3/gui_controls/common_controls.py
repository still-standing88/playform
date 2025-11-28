from PySide6.QtWidgets import QLabel, QToolTip, QPushButton, QToolButton
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer, QRect
from PySide6.QtCore import Qt as qt


class TextLabel(QLabel):


    def __init__(self,text,parent):
        super().__init__(parent)
        self.setText(text)
        self.setFocusPolicy(qt.FocusPolicy.TabFocus)

class ConfirmButton(QToolButton):


    def __init__(self,label,parent=None):
        super().__init__(parent)
        self.setText(label)
        self.setIcon(QIcon.fromTheme("dialog-ok"))

class CancelButton(QToolButton):


    def __init__(self,label,parent=None):
        super().__init__(parent)
        self.setText(label)
        self.setIcon(QIcon.fromTheme("dialog-cancel"))

class ToolTip(QToolTip):


    def __init__(self,text,pos,duration,widget,parent=None):
        super().__init__()
        self.parent = parent
        self.text = text
        self.duration = duration
        self.position = pos
        self.show_text(self.position,self.text,self.duration)

    def show_text(self,position,txt,dur):
        self.showText(position,txt,self.parent,QRect(15,30,40,60),dur)
        QTimer.singleShot(self.duration,self.deleteInstance)

    def deleteInstance(self):
        del self


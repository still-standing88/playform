import sys
sys.path.appen("..")

from PySide6.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QListWidget,
QMenu, QPushButton, QRadioButton, QComboBox, QLabel, QButtonGroup)
from PySide6.QtCore import Qt as qt

from utilities.util_gui import contextMenu, menuItem
from utilities import hexify,dehexify, converttime, numberList
from utilities.util_structs import timeForm
from GUIControls.commen_controls import confirmButton, cancelButton
import prefs

bms_path = f"{prefs.current_path}/bookmarks.json"
marks = {}

def processData(path,mode,data="", target=""):
    if mode == "read":
        with open(path,"r") as file:
            tstrS = file.readlines()
            tstr = []
            for line in range(0,len(tstrS)-1+1):
                if tstrS[line]: tstr.append(dehexify(tstrS[line]))
        dstr = ""
        for line in tstr:
            dstr += line+"\n"
            pstr = json.loads(dstr)
            global marks
            marks = pstr
    elif mode == "write":
        with open(path,"w") as file:
            tstr = hexify(json.dumps(data))
            file.write(tstr)
    elif mode == "delete":
        with open(path,"w") as file:
            file.write("")

def save():        
    processData(bms_path,"write",marks)

def initialize():
    if os.path.exists(bms_path) == True:
        processData(bms_path,"read",marks)
    elif os.path.exists(bms_path) == False:
        save()


class newDialog(QDialog):
    def __init__(self,parent=None):
        self.parent = parent
        super().__init__(self.parent)
        self.setWindowTitle("add a new mark at position")
        self.values()
        self.ui()
        self.Layout()
        self.setLayout(self.layout)

    def ui(self):
        self.position_label = QLabel("insert at: ",self)
        self.button_group = QButtonGroup()
        self.current_position_radio = QRadioButton("Current Position",self)
        self.current_position_radio.v= 1
        self.button_group.addButton(self.current_position_radio)
        self.custom_position_radio = QRadioButton("Custom Position",self)
        self.custom_position_radio.v = 2
        self.button_group.addButton(self.custom_position_radio)
        if self.hours >0:
            self.hours_label = QLabel("hours",self)
            self.hours_box = QComboBox(self)
        self.minutes_label = QLabel("minutes",self)
        self.minutes_box = QComboBox(self)
        self.seconds_label = QLabel("seconds",self)
        self.seconds_box = QComboBox(self)
        self.confirm_button = confirmButton("confirm",self)
        self.cancel_button = cancelButton("cancel",self)
        if self.hours >0:
            self.hours_box.addItems(numberList(0,self.hours,"2"))
        self.minutes_box.addItems(numberList(0,self.minutes,"2"))
        self.seconds_box.addItems(numberList(0,self.seconds,"2"))
        if hasattr(self,"hours_box") == True: self.hours_box.currentIndexChanged.connect(self.hoursBox)
        self.minutes_box.currentIndexChanged.connect(self.minutesBox)
        self.button_group.buttonClicked.connect(self.onPosition)
        self.confirm_button.clicked.connect(self.onConfirm)
        self.cancel_button.clicked.connect(self.close)
        if hasattr(self,"hours_box") == True: self.hours_box.hide()
        self.minutes_box.hide()
        self.seconds_box.hide()

    def Layout(self):
        self.layout = QVBoxLayout()
        hb1l = QHBoxLayout()
        hb1l.addWidget(self.current_position_radio)
        hb1l.addWidget(self.custom_position_radio)
        self.layout.addLayout(hb1l)
        if self.hours >0:
            hb2l = QHBoxLayout()
            hb2l.addWidget(self.hours_label)
            hb2l.addWidget(self.hours_box)
            self.layout.addLayout(hb2l)
        hb3l = QHBoxLayout()
        hb3l.addWidget(self.minutes_label)
        hb3l.addWidget(self.minutes_box)
        self.layout.addLayout(hb3l)
        hb4l = QHBoxLayout()
        hb4l.addWidget(self.seconds_label)
        hb4l.addWidget(self.seconds_box)
        self.layout.addLayout(hb4l)
        hb5l = QHBoxLayout()
        hb5l.addWidget(self.confirm_button)
        hb5l.addWidget(self.cancel_button)
        self.layout.addLayout(hb5l)

    def onPosition(self):
        if self.button_group.checkedButton().v == 1:
            self.v = 1
            if hasattr(self,"hours_box") == True: self.hours_box.hide()
            self.minutes_box.hide()
            self.seconds_box.hide()
        elif self.button_group.checkedButton().v == 2:
            self.v=2
            if hasattr(self,"hours_box") == True: self.hours_box.show()
            self.minutes_box.show()
            self.seconds_box.show()

    def onConfirm(self):
        if self.v == 1:
            self.pos = self.currentPosition
        elif self.v == 2:
            if hasattr(self,"hours_box") == True: self.hours = int(self.hours_box.currentText())
            self.minutes = int(self.minutes_box.currentText())
            self.seconds = int(self.seconds_box.currentText())
            self.pos = int(self.hours*3600)+int(self.minutes*60)+int(self.seconds)
        l = list(marks[self.parent.name].keys())
        marks[self.parent.name][str(len(l)+1)] = self.pos
        self.close()
        save()

    def hoursBox(self,ind):
        if int(self.hours_box.currentText()) == self.hours:
            self.minutes_box.clear()
            self.minutes_box.addItems(numberList(0,self.minutes,"2"))
        elif int(self.hours_box.currentText()) < self.hours:
            self.minutes_box.clear()
            self.minutes_box.addItems(numberList(0,59,"2"))

    def minutesBox(self):
        if int(self.minutes_box.currentText()) == self.minutes:
            self.seconds_box.clear()
            self.seconds_box.addItems(numberList(0,self.seconds,"2"))
        elif int(self.minutes_box.currentText()) < self.minutes:
            self.seconds_box.clear()
            self.seconds_box.addItems(numberList(0,59,"2"))

    def values(self):
        mtype = str(self.parent.type)
        t = getattr(self.parent.controls.selector,mtype)["gettime"]()
        self.currentPosition = t["position"]
        ts = timeForm(t["length"])
        self.hours = ts.hours
        self.minutes = ts.minutes
        self.seconds = ts.seconds


class editDialog(QDialog):
    def __init__(self,mark,parent=None):
        self.parent = parent
        self.mark = mark
        super().__init__(self.parent)
        self.setWindowModality(qt.WindowModal)
        self.setWindowTitle("edit mark position")
        self.values()
        self.ui()
        self.Layout()
        self.setLayout(self.layout)


    def ui(self):
        if self.hours >0:
            self.hours_label = QLabel("hours",self)
            self.hours_box = QComboBox(self)
        self.minutes_label = QLabel("minutes",self)
        self.minutes_box = QComboBox(self)
        self.seconds_label = QLabel("seconds",self)
        self.seconds_box = QComboBox(self)
        self.confirm_button = QPushButton("confirm",self)
        self.cancel_button = QPushButton("cancel",self)
        self.confirm_button.clicked.connect(self.onConfirm)
        self.cancel_button.clicked.connect(self.close)

        if self.hours >0:
            self.hours_box.addItems(numberList(0,self.hours,"2"))
        self.minutes_box.addItems(numberList(0,self.minutes,"2"))
        self.seconds_box.addItems(numberList(0,self.seconds,"2"))
        if hasattr(self,"hours_box") == True: self.hours_box.currentIndexChanged.connect(self.hoursBox)
        self.minutes_box.currentIndexChanged.connect(self.minutesBox)

    def Layout(self):
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.position_label)
        if self.hours >0:
            hb2l = QHBoxLayout()
            hb2l.addWidget(self.hours_label)
            hb2l.addWidget(self.hours_box)
            self.layout.addLayout(hb2l)

        hb3l = QHBoxLayout()
        hb3l.addWidget(self.minutes_label)
        hb3l.addWidget(self.minutes_box)
        self.layout.addLayout(hb3l)
        hb4l = QHBoxLayout()
        hb4l.addWidget(self.seconds_label)
        hb4l.addWidget(self.seconds_box)
        self.layout.addLayout(hb4l)
        hb5l = QHBoxLayout()
        hb5l.addWidget(self.confirm_button)
        hb5l.addWidget(self.cancel_button)
        self.layout.addLayout(hb5l)

    def onConfirm(self):
        if hasattr(self,"hours_box") == True: self.hours = int(self.hours_box.currentText())
        self.minutes = int(self.minutes_box.currentText())
        self.seconds = int(self.seconds_box.currentText())
        self.pos = int(self.hours*3600)+int(self.minutes*60)+int(self.seconds)
        l = list(marks[self.parent.name].keys())
        marks[self.parent.name][self.mark] = self.post
        self.close()
        save()

    def hoursBox(self,ind):
        if int(self.hours_box.currentText()) == self.hours:
            self.minutes_box.clear()
            self.minutes_box.addItems(numberList(0,self.minutes,"2"))
        elif int(self.hours_box.currentText()) < self.hours:
            self.minutes_box.clear()
            self.minutes_box.addItems(numberList(0,59,"2"))

    def minutesBox(self):
        if int(self.minutes_box.currentText()) == self.minutes:
            self.seconds_box.clear()
            self.seconds_box.addItems(numberList(0,self.seconds,"2"))
        elif int(self.minutes_box.currentText()) < self.minutes:
            self.seconds_box.clear()
            self.seconds_box.addItems(numberList(0,59,"2"))

    def values(self):
        mtype = str(self.parent.type)
        t = getattr(self.parent.controls.selector,mtype)["gettime"]()
        self.currentPosition = t["position"]
        ts = timeForm(t["length"])
        self.hours = ts.hours
        self.minutes = ts.minutes
        self.seconds = ts.seconds


class marksDialog(QDialog):
    def __init__(self,parent=None):
        self.parent = parent
        super().__init__(self.parent)
        self.setWindowModality(qt.WindowModal)
        self.setWindowTitle("Bookmarks")
        self.ui()
        self.Layout()
        self.setLayout(self.layout)

    def ui(self):
        self.marks_list = marksList(self)

    def Layout(self):
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.marks_list)

class marksList(QListWidget):
    def __init__(self,parent=None):
        self.parent = parent
        super().__init__(self.parent)
        self.listMarks()
        contextMenu(self,self.context_menu)
        self.itemActivated.connect(self.onClick)
        self.itemClicked.connect(self.onClick)


    def listMarks(self):
        filename = self.parent.parent.name
        self.clear()
        l = list(marks[filename].keys())
        self.addItems(l)

    def onClick(self):
        item = self.currentItem()
        filename = self.parent.parent.name
        mark = marks[filename][item.text()]
        if item is not None and item.text() in marks[filename]:
            self.parent.parent.controls.selector.setProperty(self.parent.parent.controls.format,"time",mark)

    def delMark(self):
        item = self.currentItem()
        filename = self.parent.parent.name
        if item is not None and item.text() in marks[filename]:
            del marks[filename][item.text()]
            self.takeItem(self.row(item))
            save()

    def addNew(self):
        self.parent.parent.newMark()

    def editMark(self):
        d = editDialog(self.currentItem().text(),self.parent.parent)

    def clearAll(self):
        filename = self.parent.parent.name
        filemarks = list(marks[filename].keys())
        if len(filemarks)>0:
            marks[filename].clear()
            self.clear()
            save()

    def context_menu(self):
        popup = QMenu("Actions")
        menuItem(popup,"add new mark",self.addNew,self)
#        menuItem(popup,"edit position",self.editMark,self)
        menuItem(popup,"delete",self.delMark,self)
        menuItem(popup,"clear all",self.clearAll,self)
        popup.exec_(self.mapToGlobal(self.rect().bottomLeft()))

    def keyPressEvent(self,event):
        key = event.key()
        if key == qt.Key_Delete:
            self.delMark()
        else:
            super().keyPressEvent(event)

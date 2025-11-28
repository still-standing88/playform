import os, sys

from PySide6.QtWidgets import QDialog, QVBoxLayout,QHBoxLayout, QTextEdit, QListWidget
from PySide6.QtCore import Qt as qt
from GUIControls.commen_controls import listctrl, confirmButton, cancelButton
from utilities import messageBox


class hotkeyField(QTextEdit):
    def __init__(self,text,row,parent=None):
        self.row = row
        self.parent = parent
        super().__init__(self.parent)
        self.parent.middleLayout.addWidget(self)
        self.setTabChangesFocus(True)
        self.setPlainText(text)
        self.setFocus()

    def onEdit(self):

        sequence = str(self.toPlainText())
        isValid = is_valid_hotkey(sequence)
        if isValid == True:
            modifyKey(self.parent.hotkey_sections.currentItem().text(),self.parent.hotkeys_list.columnFromIndex(1),sequence)
            self.parent.hotkeys_list.editColumn(self.row,0,sequence)
        else:
            messageBox("Error",f"Invalid hotkey sequence{sequence}")
            return
        self.destroy()

    def destroy(self):
        self.parent.middleLayout.removeWidget(self)
        self.deleteLater
        self.close()

    def keyPressEvent(self, e):
        key = e.key()
        if key==qt.Key_Escape:
            self.destroy()
        elif key == qt.Key_Return or key == qt.Key_Enter: self.onEdit()
        else:
            return super().keyPressEvent(e)


class keysDialog(QDialog):
    def __init__(self,parent=None):
        self.parent = parent
        super().__init__(self.parent)
        self.setWindowModality(qt.WindowModal)
        self.setWindowTitle("Hotkey Prefrences")
        self.ui()
        self.Layout()


    def ui(self):
        self.hotkey_sections = QListWidget(self)
        self.hotkeys_list = listctrl(self)
        self.confirm_btn = confirmButton("Confirm",self)
        self.cancel_btn = cancelButton("Cancel",self)
        for section in key_config.sections():
            self.hotkey_sections.addItem(section)
        self.hotkey_sections.currentItemChanged.connect(self.onSections)
        self.hotkeys_list.column(0,"Sequence")
        self.hotkeys_list.column(1,"Description")
        self.hotkeys_list.itemActivated.connect(self.editHotkey)
        self.hotkeys_list.itemClicked.connect(self.editHotkey)
        self.confirm_btn.clicked.connect(self.onConfirm)
        self.cancel_btn.clicked.connect(self.close)

    def Layout(self):
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.hotkey_sections)
        self.layout.addWidget(self.hotkeys_list)
        self.layout.addStretch()
        self.middleLayout = QVBoxLayout()
        self.layout.addLayout(self.middleLayout)
        bottomLayout = QHBoxLayout()
        bottomLayout.addWidget(self.confirm_btn)
        bottomLayout.addWidget(self.cancel_btn)
        self.layout.addStretch()
        self.layout.addLayout(bottomLayout)

    def editHotkey(self):
        if hasattr(self,"hotkey_field")==True: self.hotkey_field.destroy()
        self.hotkey_field = hotkeyField(self.hotkeys_list.columnFromIndex(0),self.hotkeys_list.row(self.hotkeys_list.currentItem()),self)

    def onConfirm(self):
        config_file = f"{os.getcwd()}\\data\\key_config.cfg"
        self.parent.refreshHotkeys()
        self.parent.browser_dock.widget().browserList.refreshHotkeys()
        if self.parent.mediaTabs.count() > 0:
            for tab in range(self.parent.mediaTabs.count()):
                self.parent.mediaTabs.widget(self.parent.mediaTabs.currentIndex()).controls.refreshHotkeys()
        with open(config_file,"w") as cf:
            key_config.write(cf)
        self.close()

    def onSections(self,c,p):
        current = self.hotkey_sections.currentItem().text()
        self.hotkeys_list.clearAll()
        self.hotkeys_list.column(0,"Sequence")
        self.hotkeys_list.column(1,"Description")
        for sequence in key_config[current]:
            self.hotkeys_list.appendRow({0:key_config[current][sequence],1:sequence})
        if self.hotkeys_list.count()>0: self.hotkeys_list.setCurrentRow(1)
            



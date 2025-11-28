import sys
sys.path.append("..")

from PySide6.QtWidgets import QDialog, QVBoxLayout,QHBoxLayout, QComboBox
from PySide6.QtCore import Qt as qt
from GUIControls.commen_controls import confirmButton, cancelButton
from utilities.util_gui import messageBox
from utilities import media_url, youtube_url, network_check, isValidURL
from utilities.util_structs import Formats

import prefs

class urlDialog(QDialog):
    def __init__(self,parent=None):
        self.parent = parent
        self.f = Formats()
        super().__init__(self.parent)
        self.setWindowTitle("Open media from url")
        self.setWindowModality(qt.WindowModal)
        self.setFixedSize(200, 200)
        self.setAttribute(qt.WA_DeleteOnClose)
        self.ui()
        self.Layout()

    def ui(self):
        self.url_field = QComboBox(self)
        self.url_field.setEditable(True)
        if len(prefs.prefs["urlls"]) > 0: self.url_field.addItems(prefs.prefs["urlls"])
        self.confirm_btn = confirmButton("Open",self)
        self.cancel_btn = cancelButton("Cancel",self)
        self.confirm_btn.clicked.connect(self.onConfirm)
        self.cancel_btn.clicked.connect(self.close)
        self.url_field.textActivated.connect(self.onConfirm)

    def Layout(self):
        self.layout = QVBoxLayout(self)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.confirm_btn)
        btn_layout.addWidget(self.cancel_btn)
        self.layout.addWidget(self.url_field)
        self.layout.addLayout(btn_layout)

    def onConfirm(self):
        internet_status = network_check()
        if internet_status!=0:
            messageBox("Error",f"Network connection error, code{internet_status}")
            return
        url = self.url_field.currentText()
        if url == "": messageBox("Error","Empty url field");return
#        if isValidURL(url) == False:
#            messageBox("Error","Invalid URL format")
#            return
        if "youtube" in url:
            self.parent.videoLoad(url,url=True)
        else:
            name = media_url(url)
            format = f".{name.split(".")[-1]}"
            if format in self.f.audio:
                self.parent.audioLoad(url,url=True)
            elif format in self.f.video:
                self.parent.videoLoad(url,url=True)
            else:
                self.parent.videoLoad(url,url=True)
        prefs.prefs["urlls"].clear()
        if self.url_field.count() >0:
            for item in range(0,self.url_field.count()): prefs.prefs["urlls"].append(self.url_field.itemText(item))
        prefs.save()
        self.close()

import sys
sys.path.append("..")
from PySide6.QtWidgets import QTabWidget, QWidget, QDialog, QVBoxLayout, QHBoxLayout,QSpinBox, QComboBox
from PySide6.QtCore import Qt as qt
from GUIControls.commen_controls import confirmButton, cancelButton
from utilities import hexify,dehexify, userDir
from utilities.util_data import title_lngs, screenshot_formats
import prefs

class GeneralWidget(QWidget):

    def __init__(self,parent=None):

        self.lngs = list(title_lngs.keys())
        self.parent = None
        self.title_lng = ""
        self.image_format = ""
        super().__init__(self.parent)
        self.ui()
        self.Layout()


    def ui(self):
        self.title_lng_box = QComboBox(self)
        self.image_format_box = QComboBox(self)
        lngs = list(title_lngs.values())
        for lng in lngs:
            self.title_lng_box.addItem(lng)
        self.image_format_box.addItems(screenshot_formats)
        lng_value = lngs.index(title_lngs[prefs["subtitle-language"]])
        img_value = screenshot_formats.index(prefs["image_format"])
        self.title_lng_box.setCurrentIndex(lng_value)
        self.image_format_box.setCurrentIndex(img_value)
        self.title_lng_box.setPlaceholderText("Subtitle language")
        self.image_format_box.setPlaceholderText("Screenshot image format")
        self.title_lng_box.currentIndexChanged.connect(self.onIndexChange)
        self.image_format_box.currentIndexChanged.connect(self.onIndexChange)


    def Layout(self):
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.title_lng_box)
        self.layout.addWidget(self.image_format_box)
        self.setLayout(self.layout)

    def onIndexChange(self,index):
        if self.title_lng_box.hasFocus() == True: self.title_lng = self.lngs[self.title_lng_box.currentIndex()]
        if self.image_format_box.hasFocus() == True: self.image_format = self.image_format_box.currentText()

class AudioWidget(QWidget):

    def __init__(self,parent=None):

        self.parent = parent
        self.device = prefs["device"]
        self.offset = prefs["offset"]["seek"]
        super().__init__(self.parent)
        self.ui()
        self.Layout()

    def ui(self):
        self.device_box = QComboBox(self)
        self.offset_field = QSpinBox(self)
        self.device_box.setPlaceholderText("Audio device")
#        self.offset_field.setPlaceholderText("Sekk Offset")
        self.device_box.addItems(self.parent.parent.devices)
        self.device_box.setCurrentIndex(self.parent.parent.devices.index(prefs["device"]))
        self.offset_field.setValue(prefs["offset"]["seek"])
        self.device_box.currentIndexChanged.connect(self.onDeviceChange)
        self.offset_field.valueChanged.connect(self.onOffsetValue)

    def Layout(self):
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.device_box)
        self.layout.addWidget(self.offset_field)
        self.setLayout(self.layout)

    def onOffsetValue(self,value):
        self.offset = value

    def onDeviceChange(self,index):
        self.device = index

class prefsDialog(QDialog):
    def __init__(self,parent=None):
        self.parent = parent
        super().__init__(parent)
        self.setWindowModality(qt.WindowModal)
        self.setAttribute(qt.WA_DeleteOnClose)
        self.setWindowTitle("Prefrences")
        self.parent.deviceList()
        self.ui()
        self.Layout()

    def ui(self):
        self.prefs_tabs = QTabWidget(self)
        self.general_tab = GeneralWidget(self)
        self.audio_tab = AudioWidget(self)
        self.confirm_btn = confirmButton("Confirm",self)
        self.cancel_btn = cancelButton("Cancel",self)
        self.prefs_tabs.addTab(self.general_tab,"General Settings")
        self.prefs_tabs.addTab(self.audio_tab,"Audio Setings")
        self.confirm_btn.clicked.connect(self.close)
        self.cancel_btn.clicked.connect(self.onConfirm)

    def Layout(self):
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.prefs_tabs)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.confirm_btn)
        btn_layout.addWidget(self.cancel_btn)
        self.setLayout(self.layout)

    def onConfirm(self):
        prefs["subtitle-language"] = self.general_tab.title_lng
        prefs["image_format"] = self.general_tab.image_format
        prefs["device"] = self.audio_tab.device
        prefs["offset"]["seek"] = self.audio_tab.offset
        save()
        self.parent.refreshDevices()
        self.close()

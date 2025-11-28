from PySide6.QtWidgets import QSlider, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QComboBox
from PySide6.QtCore import Qt as qt
from guiCustomControls import listTabCtrl
import wmp
import fx

audio = fx.audio
video = fx.video

class audioEffect(QWidget):
    def __init__(self,name,values,effect,struct,params,parent=None):
        self.parent = parent
        self.handle = self.parent.parent.instance
        self.name = name
        self.values = values
        self.effect = struct
        self.effect_handle = effect
        self.params = params
        super().__init__(parent)
        self.ui()
        self.Layout()
        self.setLayout(self.layout)
        self.hide()

    def ui(self):
        self.value_sliders = {}
        self.labels = {}
        for value in self.values:
            name = f"{value}_slider"
            self.labels[f"{value}_label"] = QLabel(value,self)
            self.value_sliders[name] = QSlider(qt.Horizontal,self)
            self.value_sliders[name].name = value
            self.value_sliders[name].setAccessibleName(value)
            self.value_sliders[name].setSingleStep(self.values[value]["offset"])
            self.value_sliders[name].setMinimum(self.values[value]["min"])
            self.value_sliders[name].setMaximum(self.values[value]["max"])
            self.value_sliders[name].setValue(self.values[value]["def"])
            self.value_sliders[name].valueChanged.connect(self.onModify)

    def Layout(self):
        self.layout = QVBoxLayout()
        for slider,label in zip(list(self.value_sliders.values()),list(self.labels.values())):
            slider_layout = QHBoxLayout()
            slider_layout.addWidget(label)
            slider_layout.addWidget(slider)
            self.layout.addLayout(slider_layout)


    def onModify(self,value):
        widget = self.focusWidget()
        if isinstance(widget,QSlider):
            self.params[widget.name] = value
            self.fx.setParam(widget.name,value)


class audioFx(listTabCtrl):
    def __init__(self, parent=None):
        self.parent = parent
        super().__init__(parent)
        self.tabActivated.connect(self.applyEffect)
        self.tabChanged.connect(self.onTabChange)
        for effect in audio:
            effect_tabb = audioEffect(audio[effect]["name"],audio[effect]["values"],audio[effect]["handle"],audio[effect]["struct"],audio[effect]["parameters"],self)
            self.addTab(effect,effect_tabb)

    def applyEffect(self):
        tab = self.currentTab()
        if tab is not None:
            state = tab.is_activated()
            widget = tab.widget
            if state == True:
                widget.show()
                widget.fx = wmp.fx(widget.handle,widget.effect_handle,widget.effect,widget.params)
                for w in widget.value_sliders:
                    widget.fx.setParam(widget.value_sliders[w].name,widget.value_sliders[w].value())
            elif state == False:
                widget.hide()
                widget.fx.remove()
    def onTabChange(self,c,p):
        if p is not None and p.is_activated() == True:
            p.widget.hide()
        if c is not None and c.is_activated() == True:
            c.widget.show()




class videoEffect(QWidget):
    def __init__(self, name,params,filter,syntax=None,parent=None):
        self.parent = parent
        self.handle = self.parent.parent.vid
        self.name = name
        self.filter = filter
        self.special = syntax
        self.params = {}
        self.parameters = params
#        self.parent.effects[self.name] = ""
        self.effect_string = ""
        super().__init__(parent)
        self.ui()
        self.Layout()
        self.setLayout(self.layout)
#        self.parent.reconstruct()
        self.hide()

    def ui(self):
        self.param_labels = {}
        self.param_widgets = {}
        for param in self.parameters:
            name = f"{param}_widget"
#            self.params[param] = ""
            if self.parameters[param]["type"] == "numeric":
                self.param_labels[f"{param}_label"] = QLabel(param,self)
                self.param_widgets[name] = QSlider(qt.Horizontal,self)
                self.param_widgets[name].setValue(self.parameters[param]["def"])
                self.param_widgets[name].setSingleStep(self.parameters[param]["offset"])
                self.param_widgets[name].setMinimum(self.parameters[param]["min"])
                self.param_widgets[name].setMaximum(self.parameters[param]["max"])
                self.param_widgets[name].valueChanged.connect(self.onModify)
                self.params[param] = self.parameters[param]["def"]
            elif self.parameters[param]["type"] == "textual":
                self.param_labels[f"{param}_label"] = QLabel(param,self)
                self.param_widgets[name] = QComboBox(self)
                self.param_widgets[name].addItems(self.parameters[param]["values"])
                self.param_widgets[name].currentIndexChanged.connect(self.onModify)
                self.params[param] = self.parameters[param]["values"][0]
            self.param_widgets[name].name = param
            self.param_widgets[name].setAccessibleName(param)
    def Layout(self):
        self.layout = QVBoxLayout()
        for label,widget in zip(list(self.param_widgets.values()),list(self.param_labels.values())):
            param_layout = QHBoxLayout()
            param_layout.addWidget(label)
            param_layout.addWidget(widget)
            self.layout.addLayout(param_layout)


    def onModify(self,value):
        widget = self.focusWidget()
        if isinstance(widget,QSlider):
            self.params[widget.name] = float(value)
        elif isinstance(widget,QComboBox):
            self.params[widget.name] = widget.currentText()
        self.parent.reconstruct()
        self.parent.applyChain()


class videoEffects(listTabCtrl):
    def __init__(self, parent=None):
        self.effects = {}
        self.effect_chain = ""
        self.parent = parent
        super().__init__(parent)
        self.tabChanged.connect(self.onTabChange)
        self.tabActivated.connect(self.applyEffect)
        for effect in video:
            effectTab = videoEffect(video[effect]["name"],video[effect]["values"],video[effect]["filter"],video[effect]["special"] if "special" in video[effect] else None,self)
            self.addTab(effect,effectTab)

    def onTabChange(self,c,p):
        if p is not None and p.is_activated() == True:
            p.widget.hide()
        if c is not None and c.is_activated() == True:
            c.widget.show()


    def applyEffect(self):
        tab = self.currentTab()
        if tab is not None:
            state = tab.is_activated()
            widget = tab.widget
            if state == True:
                widget.show()
                self.reconstruct()
                self.effects[widget.name] = widget.effect_string
                self.applyChain()
            elif state == False:
                widget.hide()
                del self.effects[widget.name]
#                self.effects.pop(widget.name)
                self.applyChain()

    def reconstruct(self):
        effect = self.currentTab().widget
        keys = list(effect.params.keys())
        length = len(keys)
        if effect.filter == "audio":
            effect.effect_string = f"lavfi=[{effect.name}="
            for param in effect.params:
                index = keys.index(param)
                effect.effect_string+= f"{param}={effect.params[param]}"
                if index+1 <length and length>1:
                    effect.effect_string +=":"
            effect.effect_string+= "]"
        elif effect.filter == "video":
            if effect.special is not None:
                effect.effect_string = f"{effect.special}{effect.name}="
            else:
                effect.effect_string = f"{effect.name}="
            for param in effect.params:
                index = keys.index(param)
                effect.effect_string+= f"{param}={effect.params[param]}"
                if index+1 <length and length>1:
                    effect.effect_string +=":"
        self.effects[effect.name] = effect.effect_string

    def applyChain(self):
        keys = list(self.effects.keys())
        length = len(keys)
        self.effect_chain = ""
        for effect in self.effects:
            index = keys.index(effect)
            self.effect_chain += self.effects[effect]
            if length >1 and index+1 <length:
                if self.effects[keys[index+1]] != "":self.effect_chain += ","
        self.parent.vid.instance.af = self.effect_chain

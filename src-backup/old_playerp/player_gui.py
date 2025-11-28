from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QMenu, QPushButton, QLabel, QSlider, QFrame, QToolButton, QListWidget
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtCore import QTimer, QEvent, QKeyCombination
from PySide6.QtCore import Qt as qt
import os
import prefs, wmp, effects
import bookmarks
from guiCustomControls import textLabel, toggleButton, keyEventFilter
from functions import converttime, Segment, getFormat, Formats, mediaIcons, messageBox, Icon, pixmap, hexify,dehexify, hasFocus, contextMenu, menuItem, open_explorer, copyText
import hotkeys

formats = Formats()
f = formats.audio+formats.video
icons = mediaIcons()

class playerControls(QWidget):
    def __init__(self,parent,instance):
        super().__init__()
        contextMenu(self,self.context_menu)
        self.parent = parent
        self.segment = Segment()
        self.hotkey_functions = [self.Playback,self.backword,self.forword,self.playbackStop,self.mute,self.prev,self.next,self.beginning,self.end,self.repeate,self.volumeUp,self.volumeDown,self.parent.bookmarks,self.parent.onMark,self.parent.newMark,self.segment_start,self.segment_end,self.segment.erase,self.mark1,self.mark2,self.mark3,self.mark4,self.mark5,self.mark6,self.mark7,self.mark8,self.mark9,self.mark0,self.screenshot]
        self.hotkeys_list = {}
        self.muted = False
        self.instance = instance
        self.format = getFormat(self.parent.path)
        if "youtube" in self.parent.path and self.parent.url == True: self.format = ".mp4"
        self.currentIndex = 0
        self.dir_files = []
        self.selector = format_selector(player=parent.player,instance=self.instance,vid=self.parent.vid)
        self.pos = 0
        self.setParent(self.parent)
        self.setFocusPolicy(qt.TabFocus)
        self.settype()
        if self.parent.type == type.audio: self.selector.instance = self.parent.instance

        self.ui()
        self.hotkeys()
        self.layout()
        self.setIcons()
        import time
        if self.parent.type == type.video: time.sleep(1)
        self.markload()
        if self.parent.type == type.audio: self.Playback()
        else: self.playback_button.setText("Pause")
        self.timer.start()
        self.player_timer.start()
        self.playerControls.setLayout(self.Layout)
        self.setLayout(self.mainLayout)

    def  ui(self):
        self.playerView = textLabel("player View",self)
        self.playerView.hide()
        self.playerControls = QFrame()
        self.prev_button = QPushButton("previous",self.playerControls)
        self.backword_button = QPushButton("backword",self.playerControls)
        self.playback_button = QPushButton("",self.playerControls)
        self.forword_button = QPushButton("forword",self.playerControls)
        self.next_button = QPushButton("next",self.playerControls)
        self.time_label = textLabel("",self.playerControls)

        self.seek_label = QLabel("seek",self.playerControls)
        self.timer = QTimer()
        self.player_timer = QTimer()
        self.seek_slider = QSlider(qt.Horizontal,self.playerControls)
        self.seek_slider.setAccessibleName("Seek")
        self.mute_button = toggleButton("mute",self.playerControls)
        self.volume_label = QLabel("volume",self.playerControls)
        self.volume_slider = QSlider(qt.Vertical,self.playerControls)
        self.volume_slider.setAccessibleName("Volume")
        self.repeate_button = toggleButton("repeate on" if prefs.prefs["repeate"] == True else "repeate off",self.playerControls)
        self.repeate_button.setActuated(prefs.prefs["repeate"])
        self.stop_button = QPushButton("stop playback",self.playerControls)

        self.selector.command(self.format,"volume",0.7)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(200)
        self.selector.command(self.format,"getVolume")
        mtype = str(self.parent.type);
        v = getattr(self.selector,mtype)["getVolume"]()
        self.volume_slider.setValue(int(v*100) if self.parent.type == type.audio else int(v))
        self.volume_slider.setSingleStep(offset["volume"])

        self.timer.setInterval(1000)
        self.player_timer.setInterval(500)

        self.timer.timeout.connect(self.updateTime)
        self.player_timer.timeout.connect(self.player_update)
        self.prev_button.clicked.connect(self.prev)
        self.forword_button.clicked.connect(self.forword)
        self.playback_button.clicked.connect(self.Playback)
        self.backword_button.clicked.connect(self.backword)
        self.next_button.clicked.connect(self.next)
        self.seek_slider.valueChanged.connect(self.seek)
        self.volume_slider.valueChanged.connect(self.volumeChanged)
        self.mute_button.actuated.connect(self.mute)
        self.stop_button.clicked.connect(self.playbackStop)
        self.repeate_button.actuated.connect(self.repeate)

    def layout(self):
        self.mainLayout = QVBoxLayout()
        self.Layout = QVBoxLayout()
        hb1l = QHBoxLayout()
        hb1l.addWidget(self.prev_button)
        hb1l.addWidget(self.backword_button)
        hb1l.addWidget(self.playback_button)
        hb1l.addWidget(self.forword_button)
        hb1l.addWidget(self.next_button)
        self.Layout.addLayout(hb1l)
        self.Layout.addWidget(self.time_label)
        self.Layout.addWidget(self.seek_label)
        self.Layout.addWidget(self.seek_slider)
        hb2l = QHBoxLayout()
        hb2l.addWidget(self.mute_button)
        hb2l.addWidget(self.volume_label)
        hb2l.addWidget(self.volume_slider)
        self.Layout.addLayout(hb2l)
        self.hb3l = QHBoxLayout()
        self.hb3l.addWidget(self.repeate_button)
        self.hb3l.addWidget(self.stop_button)
        self.Layout.addLayout(self.hb3l)
        self.mainLayout.addWidget(self.playerControls)
        self.mainLayout.addWidget(self.playerView)

    def hotkeys(self):
        actions = ["Play/pause","Volume up","Volume down","Forword","Backword"]
        for hotkey,function in zip(list(hotkeys.key_dict["Player"].keys()),self.hotkey_functions):
            if self.parent.type != type.video and hotkey=="Screenshot": continue
            self.hotkeys_list[hotkey] = QShortcut(QKeySequence(hotkeys.key_config["Player"][hotkey].lower().replace("page","pg")),self.playerView if hotkey in actions else self)
            self.hotkeys_list[hotkey].activated.connect(function)

    def refreshHotkeys(self):
        for hotkey in self.hotkeys_list:
            self.hotkeys_list[hotkey].setKey(QKeySequence(hotkeys.key_config["Main interface"][hotkey]))


    def setIcons(self):
        self.icons = {}
        self.pixmaps = {}
        icons = mediaIcons()
        for icon in icons:
            icon_name = os.path.splitext(os.path.basename(icons[icon]))[0]
            self.icons[icon_name] = Icon(icons[icon])
            self.pixmaps[icon_name] = pixmap(icons[icon])
        self.prev_button.setIcon(self.icons["previous"])
        self.next_button.setIcon(self.icons["next"])
        self.forword_button.setIcon(self.icons["forword"])
        self.backword_button.setIcon(self.icons["backword"])
        self.mute_button.setIcon(self.icons["mute"])
        self.stop_button.setIcon(self.icons["stop"])
        self.repeate_button.setIcon(self.icons["repeate"])
        self.volume_label.setPixmap(self.pixmaps["volume"])
        self.seek_label.setPixmap(self.pixmaps["seek"])

    def screenshot(self):
        self.instance.screenshot(prefs.sc_path,prefs.prefs["image_format"],prefs.prefs["ffmpeg_binary"])

    def prev(self):
        if self.currentIndex <=0: self.currentIndex = 0
        else:self.currentIndex -=1
        if self.currentIndex>=0:
            self.parent.changePath(self.dir_files[self.currentIndex])
            self.Playback()
    def next(self):
        if self.currentIndex >= len(self.dir_files)-1: self.currentIndex = len(self.dir_files)-1
        else: self.currentIndex +=1
        if self.currentIndex<= len(self.dir_files)-1:
            self.parent.changePath(self.dir_files[self.currentIndex])
            self.Playback()

    def forword(self):
        self.selector.command(self.format,"forword")
    def backword(self):
        self.selector.command(self.format,"backword")

    def setseek(self):
        self.selector.command(self.format,"gettime")
        mtype = str(self.parent.type)
        t = getattr(self.selector,mtype)["gettime"]()
        if t is not None and  t["length"] is not None and t["position"] is not None:
            self.seek_slider.setMinimum(0)
            self.seek_slider.setMaximum(int(t["length"]))
            self.seek_slider.setSingleStep(offset["seek"])

    def updateTime(self):
        self.selector.command(self.format,"gettime")
        mtype = str(self.parent.type)
        t = getattr(self.selector,mtype)["gettime"]()
        state = getattr(self.selector,mtype)["state"]()
        if t is not None and  t["length"] is not None and t["position"] is not None:
            self.time_label.setText("elapst: "+converttime(t["position"])+"\n"+"Remainning: "+converttime(t["remaining"])+"\n"+"duration: "+converttime(t["length"]))
            self.pos = t
            self.seek_change()
            if hasattr(self,"length") == False and t["length"] is not None: self.length = t["length"]
        if isinstance(self.pos,dict) and self.seek_slider.maximum() != self.pos["length"]:
            self.setseek()
        if prefs.prefs["repeate"] == True and state == wmp.WMP_STATE_ENDED:
            self.Playback()

    def settype(self):
        if self.format in formats.audio:
            self.parent.type = type.audio
        elif self.format in formats.video:
            self.parent.type = type.video

    def player_update(self):
        mtype = str(self.parent.type)
        t = getattr(self.selector,mtype)["gettime"]()
        if t is not None and t["length"] is not None and t["position"] is not None:
            if self.segment.active == True and  t["position"] == self.segment.end:
                self.selector.setProperty(self.format,"time",self.segment.beginning)
    def beginning(self):
        if self.segment.active == True: self.selector.setProperty(self.format,"time",self.segment.beginning)
        else: self.selector.setProperty(self.format,"time",0)

    def end(self):
        self.selector.command(self.format,"state")
        mtype = str(self.parent.type)
        t = getattr(self.selector,mtype)["gettime"]()
        if self.segment.active == True: self.selector.setProperty(self.format,"time",self.segment.end)
        else: self.selector.setProperty(self.format,"time",t["length"])

    def segment_mark(self,pos):
        mtype = str(self.parent.type)
        t = getattr(self.selector,mtype)["gettime"]()
        match pos:
            case "start":
                self.segment.mark_start(t["position"])
            case "end":
                self.segment.mark_end(t["position"])
            case _:
                return "error"

    def Playback(self):
        self.selector.command(self.format,"state")
        mtype = str(self.parent.type)
        state = getattr(self.selector,mtype)["state"]()
        if state == wmp.WMP_STATE_PLAYING:
            self.selector.command(self.format,"button")
            self.playback_button.setText("play")
            self.playback_button.setIcon(self.icons["play"])
        elif state == wmp.WMP_STATE_PAUSED or state == wmp.WMP_STATE_STOPPED or state == wmp.WMP_STATE_ENDED:
            self.selector.command(self.format,"button")
            self.playback_button.setText("pause")
            self.playback_button.setIcon(self.icons["pause"])

    def mute(self):
        if self.muted== True:
            self.muted = False
            self.selector.command(self.format,"mute")
            self.mute_button.setText("mute")
        elif self.muted == False:
            self.muted = True
            self.selector.command(self.format,"mute")
            self.mute_button.setText("unmute")

    def playbackStop(self):
        self.selector.command(self.format,"stop")
        self.playback_button.setText("play")

    def volumeUp(self):
        self.selector.setProperty(self.format,"setVolume",wmp.WMP_VOLUME_UP,value2=offset["volume"])
        self.volumeChange()

    def volumeDown(self):
        self.selector.setProperty(self.format,"setVolume",wmp.WMP_VOLUME_DOWN,value2=offset["volume"])
        self.volumeChange()

    def segment_start(self):
        self.segment_mark("start")

    def segment_end(self):
        self.segment_mark("end")

    def repeate(self):
        if prefs.prefs["repeate"] == False:
            prefs.prefs["repeate"] = True
            self.repeate_button.setText("repeate on")
        elif prefs.prefs["repeate"] == True:
            prefs.prefs["repeate"] = False
            self.repeate_button.setText("repeate off")
            prefs.save()


    def volumeChanged(self,value):
        self.selector.setProperty(self.format,"volume",value)

    def seek(self,value):
        self.selector.setProperty(self.format,"time",value)

    def seek_change(self):
        self.selector.command(self.format,"gettime")
        mtype = str(self.parent.type)
        t = getattr(self.selector,mtype)["gettime"]()
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(t["position"])
        self.seek_slider.blockSignals(False)

    def volumeChange(self):
        self.selector.command(self.format,"getVolume")
        mtype = str(self.parent.type)
        v = getattr(self.selector,mtype)["getVolume"]()
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(v*100 if self.parent.type == type.audio else v)
        self.volume_slider.blockSignals(False)

    def mark(self):
        name = prefs.marks+self.parent.name+".mark"
        mtype = str(self.parent.type)
        if self.parent.type == type.audio: pos = getattr(self.selector,mtype)["gettime"]()
        elif self.parent.type == type.video: pos = self.pos["position"]
        with open(name,"w") as f:
            if self.parent.type == type.audio:
                f.write(hexify("name = "+self.parent.name))
                f.write("\n")
                f.write(hexify("position = "+str(pos["position"])))
            elif self.parent.type == type.video:
                f.write(hexify("name = "+self.parent.name))
                f.write("\n")
                f.write(hexify("position = "+str(pos)))

    def markload(self):
        name = prefs.marks+self.parent.name+".mark"
        if os.path.exists(name) == True:
            with open(name,"r") as f:
                data = list(f.readlines())
                lines = []
                if len(data) >0: 
                    lines.append(dehexify(data[0].strip()))
                    lines.append(dehexify(data[1].strip()))
                if len(lines) >0:
                    pos = int(lines[1][11:])
                    if pos and pos >0:self.selector.setProperty(self.format,"time",pos)

    def mark1(self):
        self.seekToMark(1)
    def mark2(self):
        self.seekToMark(2)
    def mark3(self):
        self.seekToMark(3)
    def mark4(self):
        self.seekToMark(4)
    def mark5(self):
        self.seekToMark(5)
    def mark6(self):
        self.seekToMark(6)
    def mark7(self):
        self.seekToMark(7)
    def mark8(self):
        self.seekToMark(8)
    def mark9(self):
        self.seekToMark(10)
    def mark0(self):
        self.seekToMark(0)

    def seekToMark(self,n):
        m = bookmarks.marks[self.parent.name]
        if f"{n}" in m: self.selector.setProperty(self.format,"time",m[f"{n}"])

    def activateShortcuts(self):
        isFocused = hasFocus(self)
        for hotkey in self.hotkeys_list: self.hotkeys_list[hotkey].setEnabled(True) if isFocused else self.hotkeys_list[hotkey].setEnabled(False)

    def context_menu(self):
        menu = QMenu("Media File options")
        if self.url==True:
            menuItem(menu,"Copy url",lambda : copyText(self.url),self)
        else:
            menuItem(menu,"Copy Path",lambda : copyText(self.p),self)
            menuItem(menu,"Open in explorer",lambda : open_explorer(self.controls.path),self)
        menu.exec()

    def context_menu(self):
        menu = QMenu("Media File options")
        if self.parent.url==True:
            menuItem(menu,"Copy url",lambda : copyText(self.parent.url),self)
        else:
            menuItem(menu,"Copy Path",lambda : copyText(self.parent.path),self)
            menuItem(menu,"Open in explorer",lambda : open_explorer(self.parent.path),self)
        menu.exec()



    def focusInEvent(self,e):
#        self.activateShortcuts()
        super().focusInEvent(e)

    def focusOutEvent(self,e):
#        self.activateShortcuts()
        super().focusOutEvent(e)


class Player(QWidget):
    def __init__(self,parent,name,path,playlist=None,url=False):
        super().__init__()
        self.name = name
        self.path = path
        self.parent = parent
        self.playlist = playlist
        self.url = url
#        self.player = None
#        self.vid = None
#        self.setpath()
        self.setWindowTitle(self.name)

        self.ui()
        self.layout()
        self.setLayout(self.Layout)
        self.settype()
        if self.playlist is not None:
            self.playlist_files()
        else:
            if self.url == False: self.controls.dir_files = get_dir_files(self,self.path)
        if self.url == False:
            if playlist is None: self.recentMark()
            if self.path in self.controls.dir_files: self.controls.currentIndex = self.controls.dir_files.index(self.path)
        self.setWindowTitle(self.name)
        if self.type == type.audio:
            self.filters_panel = effects.audioFx(self)
        elif self.type == type.video:
            self.filters_panel = effects.videoEffects(self)
        self.filters_panel.hide()
        self.Layout.addWidget(self.filters_panel)
        self.setAttribute(qt.WA_DeleteOnClose)

    def ui(self):
        self.controls = playerControls(self,self.instance)
        self.filters_btn = toggleButton("Audio filters",self.controls)
        self.filters_btn.clicked.connect(self.onToggleFilters)
        
    def layout(self):
        self.Layout = QVBoxLayout()
        self.Layout.addWidget(self.controls)
        self.controls.hb3l.addWidget(self.filters_btn)
        if self.type == type.video and self.video_display : self.Layout.addWidget(self.video_display)


    def setpath(self):
        self.type = ""
        if self.url == False or self.playlist is  None: self.recentMark()


    def setFormat(self):
        self.controls.format = getFormat(self.path)

    def settype(self):
        if self.controls.format in formats.audio:
            self.type = type.audio
        elif self.controls.format in formats.video:
            self.type = type.video


    def recentMark(self):
        name = os.path.basename(self.path)
        if name in prefs.prefs["recent"]:
            del prefs.prefs["recent"][name]
        prefs.prefs["recent"][name] = self.path
        prefs.save()
        self.parent.parent().parent().parent().recentUpdate()

    def newMark(self):
        if self.url == True:
            messageBox("Error","files plaied from the internet mey not have book marks.")
            return
        if self.controls.length<65:
            messageBox("error","this file mey not have book marks")
            return 0
        if self.name not in bookmarks.marks:
            bookmarks.marks[self.name] = {}
        d = bookmarks.newDialog(self)
        d.show()

    def bookmarks(self):
        if self.url == True:
            messageBox("Error","files plaied from the internet mey not have book marks.")
            return

        if self.controls.length<65:
            messageBox("error","this file mey not have book marks")
            return 0
        if self.name not in bookmarks.marks:
            bookmarks.marks[self.name] = {}
        d = bookmarks.marksDialog(self)
        d.show()

    def onMark(self):
        if self.url == True:
            messageBox("Error","files plaied from the internet mey not have book marks.")
            return

        if self.controls.length<65:
            messageBox("error","this file mey not have book marks")
            return 0
        if self.name not in bookmarks.marks:
            bookmarks.marks[self.name] = {}
        t = getattr(self.controls.selector,self.type)["gettime"]()
        l = len(bookmarks.marks[self.name])+1
        if t["position"] is not None: bookmarks.marks[self.name][f"{l}"] = t["position"]
        bookmarks.save()

    def changePath(self,path):
        if self.url==False: self.controls.mark()
        self.path = path
        if self.url == False: 
            self.setFormat()
            self.settype()
            self.controls.currentIndex = self.controls.dir_files.index(self.path)
        if self.url==False: self.name = os.path.basename(self.path)
        else: self.name = "Loading"
        self.setName()
        if self.url==False or playlist is None:self.recentMark()

    def setName(self):
        self.parent.widget(self.parent.currentIndex()).setWindowTitle(self.name)
        self.parent.setTabText(self.parent.currentIndex(),self.name)

    def onToggleFilters(self):
        if self.filters_panel.isVisible() == True:
            self.filters_panel.hide()
        elif self.filters_panel.isVisible() == False:
            self.filters_panel.show()

    def playlist_files(self):
        for track in self.playlist.tracks:
            self.controls.dir_files.append(self.playlist.tracks[track].path)


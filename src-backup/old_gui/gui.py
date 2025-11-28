from PySide6.QtWidgets import QMainWindow, QWidget, QDockWidget, QHBoxLayout, QVBoxLayout, QTabWidget, QListWidget, QTableWidget, QFileDialog, QMenuBar, QSystemTrayIcon, QMenu, QPushButton, QLabel, QSpacerItem, QSizePolicy
from PySide6.QtGui import QShortcut, QKeySequence, QAction, QIcon
from PySide6.QtCore import QTimer
from PySide6.QtCore import Qt as qt

import os
import url
import browser
import audio, video, wmp, player
import playlists
import docs
import prefs
from functions import menuItem, messageBox, contextMenu
from functions import Flags, Formats, getFormat
from guiCustomControls import textLabel
import hotkeys
from functions import programAbout #, contact, docs

offset = prefs.prefs["offset"]
formats = Formats()
f = formats.audio+formats.video
flags = Flags()

class plst(QListWidget):
    def __init__(self,parent=None):
        self.parent = parent
        super().__init__(self.parent)
        self.type = ""
        contextMenu(self,self.context_menu)
        self.itemClicked.connect(self.open)
        self.itemActivated.connect(self.open)
    def open(self):
        item = self.currentItem().text()
        path = prefs.prefs[self.type][item]
        format = getFormat(path)
        if self.currentItem is not None and os.path.exists(path):
            if format in formats.audio:
                self.parent.audioLoad(path)
            elif format in formats.video:
                self.parent.videoLoad(path)
        else:
            messageBox("non existent path",f"path {path} is not found")

    def relist(self):
        self.clear()
        l = list(prefs.prefs[self.type].keys())
        self.addItems(l)

    def deleteItem(self):
        item = self.currentItem()
        del prefs.prefs[self.type][item.text()]
        self.takeItem(self.row(item))
        prefs.save()

    def clearAll(self):
        prefs.prefs[self.type].clear()
        self.clear()
        prefs.save()

    def addToPlaylist(self):
        pass

    def context_menu(self):
        popup = QMenu("actions")
#        menuItem(popup,"Add to existing playlist",self.addToPlaylist,self)
        if self.type == "favorites":
            menuItem(popup,"Delete",self.deleteItem,self)
            menuItem(popup,"Clear all",self.clearAll,self)
        if self.currentItem() is not None and self.count()>0:
            popup.exec()

class Window(QMainWindow):
    def __init__(self):
        self.devices = []
        self.global_functions = {"Play/pause":self.playback,"Mute/Unmute":self.mute,"Volume down":self.volumeDown,"Volume up":self.volumeUp,"Previous":self.previous,"Next":self.next}

        super().__init__()
        self.hotkey_funcs = {"Hotkeys dialog": self.hotkeyPrefs,"Open file": self.openFile,"Close file": self.closeCurrent,"Close all": self.closeAll,"Show/Hide explorer": self.Browser,"Show/Hide player controls": self.controlsChange,"Hide window": self.hide,"Exit": self.close,"Open URL":self.urlDialog,"Documentation":self.docs,"Prefrences Dialog":self.prefsDialog}
        self.hotkeys_list = {}
        self.icon = QIcon(os.getcwd()+"\\Icons\\icon.png")
        self.setWindowTitle("EAS Tones Media Player")
        self.mediaTab = ""
        self.trayIcon()
        self.statusBar()
        self.ui()
        self.layout()
        self.setCentralWidget(self.mainWidget)
        self.setLayout(self.Layout)
        self.mainWidget.setLayout(self.mainLayout)

        self.timer.start()
        self.diskTimer.start()
        self.installEventFilter(self)
        self.setGeometry(200,400,800,600)
        self.setWindowIcon(self.icon)
        self.recentUpdate()

    def ui(self):
        self.MenuBar()
        self.timer = QTimer()
        self.diskTimer = QTimer()
        self.c_list = QListWidget(self)
        self.c_list.type = ""
        self.s_label = QLabel("",self)
        self.s_list = plst(self)
        self.s_label.hide()
        self.s_list.hide()
        self.browser_dock = QDockWidget("Explorer",self)
        self.browser_dock.setFeatures(self.browser_dock.features() ^ QDockWidget.DockWidgetFloatable)
        self.browser_dock.hide()
        self.browser_dock.setAllowedAreas(qt.LeftDockWidgetArea | qt.RightDockWidgetArea)
        self.addDockWidget(qt.RightDockWidgetArea, self.browser_dock)
        self.mainWidget = QWidget(self)
        self.mediaWidget = QWidget(self)
        self.mediaTabs = QTabWidget(self.mediaWidget)
        self.media_dock = QDockWidget("Currently playing media",self)
        self.media_dock.setWidget(self.mediaWidget)
        self.addDockWidget(qt.BottomDockWidgetArea,self.media_dock)
        self.audio_label = textLabel("No files currently  loaded",self.mediaWidget)
        self.playlists_label = QLabel("playlists",self)
        self.playlists_box = playlists.playlistsList(self)
        self.playlists_box.setAccessibleName("playlists")
        self.playlist_label = QLabel("",self)
        self.playlist_box = playlists.plst_list(self)
        self.playlist_label.hide()
        self.playlist_box.hide()
        self.playlist_button = QPushButton("create new playlist",self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update)
        self.diskTimer.setInterval(60000)
        self.diskTimer.timeout.connect(self.diskUpdate)
        self.mediaTabs.setTabPosition(QTabWidget.West)
        self.c_list.addItems(["recent","favorites"])
        self.c_list.currentItemChanged.connect(self.listChange)
        self.mediaTabs.currentChanged.connect(self.onMediaChange)
        self.playlists_box.currentItemChanged.connect(self.onPlaylist)
        self.playlist_button.clicked.connect(self.createPlaylist)

    def layout(self):
        self.Layout = QVBoxLayout()
        self.Layout.addWidget(self.c_list)
        hb1l = QHBoxLayout()
        hb1l.addWidget(self.s_label)
        hb1l.addWidget(self.s_list)

        self.Layout.addLayout(hb1l)
        self.Layout.addStretch()
        self.mainLayout = QVBoxLayout()
#        self.mainLayout.addWidget(self.mediaTabs)
#        self.mainLayout.addWidget(self.audio_label)
        self.audioLayout = QVBoxLayout(self.mediaWidget)
        self.audioLayout.addWidget(self.mediaTabs)
        self.audioLayout.addWidget(self.audio_label)
        self.mediaWidget.setLayout(self.audioLayout)
#        self.mainLayout.addStretch()
#        self.mainLayout.addWidget(self.media_dock)
#        self.mainLayout.addLayout(self.audioLayout)
        self.bottomLayout = QHBoxLayout()
        playlistLayout = QVBoxLayout()
        hb2l = QHBoxLayout()
        hb2l.addWidget(self.playlists_label)
        hb2l.addWidget(self.playlists_box)

        self.mainLayout.addStretch()
        playlistLayout.addLayout(hb2l)
        hb3l = QHBoxLayout()
        hb4l = QHBoxLayout()
        hb4l.addWidget(self.playlist_label)
        hb4l.addWidget(self.playlist_box)
        hb3l.addStretch()

        hb3l.addLayout(hb4l)

        hb3l.addWidget(self.playlist_button)

        playlistLayout.addLayout(hb3l)
        playlistLayout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.bottomLayout.addStretch()
        self.bottomLayout.addLayout(playlistLayout)
        self.mainLayout.addStretch()

        self.mainLayout.addLayout(self.bottomLayout)

        self.Layout.addWidget(self.mainWidget)


    def shortcuts(self):
        for hotkey,function in zip(list(hotkeys.key_dict["Main interface"].keys()),self.hotkey_funcs):
            self.hotkeys_list[hotkey] = QShortcut(QKeySequence(hotkeys.key_config["Main interface"][hotkey].lower().replace("page","pg")),self)
            self.hotkeys_list[hotkey].activated.connect(self.hotkey_funcs[function])

        self.player_hotkey = QShortcut(QKeySequence("Alt+P"),self)
        self.player_hotkey.activated.connect(lambda: self.mediaTab.controls.setFocus() if self.mediaTab is not None else None)

    def refreshHotkeys(self):
        for hotkey in self.hotkeys_list:
            self.hotkeys_list[hotkey].setKey(QKeySequence(hotkeys.key_config["Main interface"][hotkey]))



    def onMediaChange(self):
        self.mediaTab = self.mediaTabs.widget(self.mediaTabs.currentIndex())
        if self.mediaTab is not None: self.controls_action.setChecked(self.mediaTab.controls.playerControls.isVisible())

    def MenuBar(self):
        menubar = self.menuBar()
        self.fileMenu = menubar.addMenu("File")
        menuItem(self.fileMenu,"Open",self.openFile,self)
        menuItem(self.fileMenu,"Open URL",self.urlDialog,self)
        menuItem(self.fileMenu,"close",self.closeCurrent,self)
        menuItem(self.fileMenu,"Close all",self.closeAll,self)
        self.recentMenu = QMenu("recent",self)

        self.fileMenu.addMenu(self.recentMenu)
        menuItem(self.fileMenu,"Hide window",self.hide,self)
        menuItem(self.fileMenu,"Exit",self.close,self)

        self.mediaMenu = menubar.addMenu("Media")
        menuItem(self.mediaMenu, "play/pause", self.playback,self)
        menuItem(self.mediaMenu, "mute/unmute",self.mute,self)
        menuItem(self.mediaMenu, "stop playback",self.playbackStop,self)
        menuItem(self.mediaMenu, "repeate",self.repeate,self)
        menuItem(self.mediaMenu, "forword",self.forword,self)
        menuItem(self.mediaMenu, "backword",self.backword,self)
        menuItem(self.mediaMenu, "previous",self.previous,self)
        menuItem(self.mediaMenu, "next",self.next,self)
        menuItem(self.mediaMenu, "jump to start of playback",self.jumpstart,self)
        menuItem(self.mediaMenu, "jump to end of playback",self.jumpend,self)
        view_menu = menubar.addMenu("view")
        self.browser_action = QAction("show browser",self)
        self.browser_action.setCheckable(True)
        self.browser_action.setChecked(False)
        self.browser_action.triggered.connect(self.onBrowser)
        view_menu.addAction(self.browser_action)

        self.controls_action = QAction("show player controls",self)
        self.controls_action.setCheckable(True)
        self.controls_action.setChecked(True)
        self.controls_action.triggered.connect(self.onControlsChange)
        view_menu.addAction(self.controls_action)

        aboutMenu = menubar.addMenu("Options")
        menuItem(aboutMenu, "documentation",self.docs,self)
        menuItem(aboutMenu, "about",self.programAbout,self)
        menuItem(aboutMenu, "Prefrences",self.prefsDialog,self)
        menuItem(aboutMenu, "Hotkey Prefrences",self.hotkeyPrefs,self)

#    menuItem(aboutMenu, "contact",contact,self)


    def trayIcon(self):
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(self.icon)
        tray_menu = QMenu("Tray Popup")
        self.hide_item = QAction("show" if self.isVisible() == True else "hide",self)
        self.hide_item.triggered.connect(self.windowState)
        tray_menu.addAction(self.hide_item)
        menuItem(tray_menu,"exit",self.close,self)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.setToolTip("media player")
        self.tray_icon.show()


    def windowState(self):
        if self.isVisible() == True:
            self.hide()
            self.hide_item.setText("show")
        elif self.isVisible() == False:
            self.show()
            self.hide_item.setText("hide")


    def recentUpdate(self):
        self.recentMenu.clear()
        l = list(prefs.prefs["recent"].keys())
        if len(l) >0:
            for file in l:
                    menuItem(self.recentMenu, file,self.recentLoad,self)
            if self.c_list.type == "recent":
                self.c_list.relist()

    def recentLoad(self):
        item = self.recentMenu.activeAction().text()
        path = prefs.prefs["recent"][item]
        format = getFormat(path)
        if format in formats.audio:
            self.audioLoad(path)
        elif format in formats.video:
            self.videoLoad(path)

    def listChange(self,c,p):
        if self.s_label.isVisible() == False and self.s_list.isVisible() == False:
            self.s_label.show()
            self.s_list.show()
        item = self.c_list.currentItem().text()
        self.s_list.type = item
        self.s_label.setText(        self.s_list.type)
        self.s_list.setAccessibleName(        self.s_list.type)
        self.s_list.relist()

    def onPlaylist(self):
        self.playlist_box.relist()
        if len(playlists.playlists)==0:
            self.playlist_label.hide()
            self.playlist_box.hide()
        elif len(playlists.playlists)!=0:
            self.playlist_label.show()
            self.playlist_box.show()

    def createPlaylist(self):
        d = playlists.createDialog(self)
        d.exec()

    def playbackStop(self):
        self.mediaTab.controls.playbackStop()
    def jumpstart(self):
        self.mediaTab.controls.beginning()
    def jumpend(self):
        self.mediaTab.controls.end()
    def repeate(self):
        self.mediaTab.controls.repeate()
    def next(self):
        if self.mediaTab is not None: self.mediaTab.controls.next()
    def forword(self):
        self.mediaTab.controls.forword()
    def previous(self):
        if self.mediaTab is not None: self.mediaTab.controls.prev()
    def backword(self):
        self.mediaTab.controls.backword()
    def mute(self):
        if self.mediaTab is not None: self.mediaTab.controls.mute()
    def playback(self):
        if self.mediaTab is not None: self.mediaTab.controls.Playback()
    def volumeUp(self):
        if self.mediaTab is not None: self.mediaTab.controls.volumeUp()

    def volumeDown(self):
        if self.mediaTab is not None: self.mediaTab.controls.volumeDown()

    def audioLoad(self,path,playlist=None,url=False):
        if url == False and self.typeCheck(path) == False: return
        audioInstance = audio.Audio(self.mediaTabs,os.path.basename(path),path,playlist=playlist,url=url)
        self.mediaTabs.addTab(audioInstance,audioInstance.name)
        if url == False:
            audioInstance.controls.setseek()
        self.recentUpdate()

    def videoLoad(self,path,playlist=None,url=False):
        global videoInstance
        if url == False and self.typeCheck(path) == False: return
        if not video.videoInstance:
            video.videoInstance = video.Video(self.mediaTabs,os.path.basename(path),path,playlist,url)
            self.mediaTabs.addTab(video.videoInstance,video.videoInstance.name)
        elif video.videoInstance is not None and self.mediaTabs.count() >0:
            video.videoInstance.changePath(path,playlist,url)

    def typeCheck(self,path):
        if getFormat(path) in f:
            return True
        elif getFormat(path) not in f:
            messageBox("ERROR","Non supported media format.")
            return False


    def controlsChange(self):
        state = self.mediaTab.controls.playerControls.isVisible()
        if state == True:
            self.mediaTab.controls.playerView.show()
            self.mediaTab.controls.playerControls.hide()
            self.controls_action.setChecked(False)
        elif state == False:
            self.controls_action.setChecked(True)
            self.mediaTab.controls.playerView.hide()
            self.mediaTab.controls.playerControls.show()

    def onControlsChange(self): self.controlsChange()

    def Browser(self):

        if browser.window.isVisible() == False:
            self.browser_action.setChecked(True)
            self.browser_dock.show()
            browser.window.show()
            browser.window.setFocus()
        elif browser.window.isVisible() == True:
            self.browser_action.setChecked(False)
            self.browser_dock.hide()
            browser.window.hide()
    def onBrowser(self,checked):
       self.Browser()

    def openFile(self):
        path = ""
        fd = QFileDialog()
        fd.setFileMode(QFileDialog.ExistingFile)
        fd.setNameFilter(flags.all)
        if fd.exec() == QFileDialog.Accepted:
            path = fd.selectedFiles()[0]
            self.open(path)

    def open(self,path):
        format = getFormat(path)
        if format in formats.audio:self.audioLoad(path)
        elif format in formats.video: self.videoLoad(path)
        else: messageBox("Not supported",f"Thhe supplied path: {path} is not supported")

    def deviceList(self):
        device_list = browser.videoInstance.getDevices()
        self.devices.clear()
        for device in device_list:
            self.devices.append(device["name"])


    def refreshDevices(self):
        current_device = prefs.prefs["device"]
        self.deviceList()
        if current_device in self.devices: device_index = self.devices.index(current_device)
        else: device_index = 0
        if hasattr(video,"videoInstance") ==True and video.videoInstance is not None or  browser.videoInstance is not None:
            if video.videoInstance is not None: video.videoInstance.setDevice(current_device)
            browser.videoInstance.setDevice(current_device)
        browser.mediaPlayer.setDevice(device_index+1)
        audio.mediaPlayer.setDevice(device_index+1)

    def hotkeyPrefs(self):
        d = hotkeys.keysDialog(self)
        d.show()

    def urlDialog(self):
        d = url.urlDialog(self)
        d.show()

    def prefsDialog(self):
        d = prefs.prefsDialog(self)
        d.show()

    def docs(self):
        docs.Docs()

    def programAbout(self):
        messageBox("About",programAbout())

    def update(self):
        if self.isVisible() == True:
            if self.mediaTabs.count() <1 and self.mediaTabs.isVisible() == True:
                self.audio_label.show()
                self.isPlayerActive = False
                self.playerActions()
                self.mediaTabs.hide()
            elif self.mediaTabs.count() >0 and self.mediaTabs.isVisible() == False:
                self.audio_label.hide()
                self.mediaTabs.show()
                self.isPlayerActive = True
                self.playerActions()

    def playerActions(self):
        self.controls_action.setEnabled(self.isPlayerActive)
        for action in self.mediaMenu.actions():
            action.setEnabled(self.isPlayerActive)
        fileActions = self.fileMenu.actions()
        fileActions[3].setEnabled(self.isPlayerActive)
        fileActions[2].setEnabled(self.isPlayerActive)

    def diskUpdate(self):
        """if self.isVisible() == True:
            disks = []
            browser.window.drive_box.clear()
            for i in range(1,browser.window.drive_box.count()+1): disks.append(browser.window.drive_box.itemText(i))
            browser.listDrives()
            drives = browser.drives
            if len(drives) != browser.window.drive_box.count():
                browser.window.drive_box.addItems(drives)
            elif len(drives) == browser.window.drive_box.count():
                for letter,drive in zip(disks,drives):
                    if drive != letter: browser.window.drive_box.addItems(drives)"""
        pass

    def closeCurrent(self):
        if self.isPlayerActive == True:
            index = self.mediaTabs.currentIndex()
            format = getFormat(self.mediaTabs.widget(index).path)
            if self.mediaTabs.widget(index).url==False: self.mediaTabs.widget(index).controls.mark()
            if format in formats.audio:
                if audio.player.state(self.mediaTabs.widget(index).controls.instance) == wmp.WMP_STATE_PLAYING:
                    self.mediaTabs.widget(index).controls.playbackStop()
                audio.player.free(self.mediaTabs.widget(index).controls.instance)
            elif format in formats.video:
                video.player.stop()
                video.player.close()
            self.mediaTabs.widget(index).deleteLater()
            self.mediaTabs.widget(index).close()
            self.mediaTabs.removeTab(index)
            del video.videoInstance
            video.videoInstance = None
            self.recentUpdate()


    def closeAll(self):
        count = self.mediaTabs.count()
        for tab in range(count):
            self.closeCurrent()





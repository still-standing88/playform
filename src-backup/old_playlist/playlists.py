from PySide6.QtWidgets import QLabel, QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QListWidget, QLineEdit, QPushButton, QTextEdit, QRadioButton, QButtonGroup, QMenu, QListWidgetItem
from PySide6.QtCore import Qt as qt
import os
import playlist
from guiCustomControls import listctrl, confirmButton, cancelButton, fileDialog
from functions import messageBox, menuItem, contextMenu, Flags, getFormat, Formats

flags = Flags()
f = Formats()
playlist_path = f"{os.getcwd()}\\data\\playlists\\"
playlists = {}

def initialize():
    l = os.listdir(playlist_path)
    if len(l) > 0:
        for file in l:
            if os.path.isfile(os.path.join(playlist_path+file)) == True and file.endswith(".mpls") == True:
                Playlist = file[0:len(file)-5]
                try:
                    playlists[Playlist] = playlist.Playlist(path=os.path.join(playlist_path+file))
                    playlists[Playlist].load()
                except Exception as e:
                    messageBox("error",e.message)

def playlistFromFolder(type,path):
    name = os.path.splitext(path)[0]
    l = os.listdir(path)
    formats = []
    if type == "audio":
        formats = f.audio
    elif type == "video":
        formats = f.video
    files = []
    for file in l:
        if os.path.isfile(os.path.join(path,file)) == True and ext in formats:
            ext = getFormat(os.path.join(path,file))
            files.append(os.path.join(path,file))
    plst = playlist.Playlist(type=type,name=name,formats=formats if type == "video" else [])
    for file in files:
        plst.addEntry(path)
    plst.save(playlist_path+name+".mpls")
    playlists[name] = plst

class tracklist(QListWidget):
    def __init__(self,parent=None):
        self.parent = parent
        super().__init__(parent)
        contextMenu(self,self.context_menu)

    def relist(self):
        self.clear()
        for track in self.parent.tracks:
            item = QListWidgetItem(self)
            item.setText(track)
#            self.addItem(track)

    def addTracks(self):
        paths = []
        filedialog = QFileDialog()
        filedialog.setFileMode(QFileDialog.ExistingFiles)
        filedialog.setNameFilter(flags.all)
        filedialog.setWindowTitle("Select file to add as tracks")
        if filedialog.exec() == QFileDialog.Accepted:
            paths = filedialog.selectedFiles()
        for path in paths:
            self.parent.tracks[os.path.basename(path)] = path
        self.relist()

    def deleteTrack(self):
        self.takeItem(self.currentItem())
        self.parent.tracks.pop(selfcurrentItem().text())


    def clearAll(self):
        self.parent.tracks.clear()
        self.clear()

    def context_menu(self):
        menu = QMenu("Tracks menu",self)
        menuItem(menu,"Add",self.addTracks,self)
        menuItem(menu,"Delete",self.deleteTrack,self)
        menuItem(menu,"Clear all",self.clearAll,self)
        menu.exec()

class createDialog(QDialog):
    def __init__(self,parent=None):
        self.name = ""
        self.description = ""
        self.type = None
        self.tracks = {}
        self.parent = parent
        super().__init__(parent)
        self.setWindowModality(qt.WindowModal)
        self.setWindowTitle("create a new playlist")
        self.ui()
        self.Layout()
        self.setLayout(self.layout)

    def ui(self):
        self.type_label = QLabel("Select playlist type",self)
        self.type_buttons = QButtonGroup(self)
        self.audio_type = QRadioButton("Audio",self)
        self.video_type = QRadioButton("Video",self)
        self.name_field = QLineEdit(self)
        self.description_field = QTextEdit(self)
        self.tracks_list = tracklist(self)
        self.confirm_button = confirmButton("Confirm",self)
        self.cancel_button = cancelButton("Cancel",self)
        self.type_buttons.addButton(self.audio_type)
        self.type_buttons.addButton(self.video_type)
        self.type_buttons.buttonClicked.connect(self.selectType)
        self.name_field.setPlaceholderText("Playlist name")
        self.description_field.setPlaceholderText("Playlist description")
        self.description_field.setTabChangesFocus(True)
        self.confirm_button.clicked.connect(self.onConfirm)
        self.cancel_button.clicked.connect(self.close)

    def Layout(self):
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.type_label)
        typeLayout = QHBoxLayout()
        typeLayout.addWidget(self.audio_type)
        typeLayout.addWidget(self.video_type)
        self.layout.addLayout(typeLayout)
        self.layout.addWidget(self.name_field)
        self.layout.addWidget(self.description_field)
        self.layout.addWidget(self.tracks_list)
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.confirm_button)
        bottom_layout.addWidget(self.cancel_button)
        self.layout.addLayout(bottom_layout)

    def onConfirm(self):
        self.name = self.name_field.text()
        self.description = self.description_field.toPlainText()
        if self.type is None:
            messageBox("Error","You must select a playlist type.")
            return 0
        if len(self.name) <1:
            messageBox("Error","Playlist cannot be empty.")
            return 0
        if len(self.description) <1:
            self.description = "None"
        plst = playlist.Playlist(type=self.type,name=self.name,description=self.description)
        for track in self.tracks:
            plst.addEntry(self.tracks[track])
        playlists[self.name] = plst
        plst.save(path=f"{playlist_path}{self.name}.mpls")
        self.parent.playlists_box.relist()
        self.close()

    def selectType(self):
        self.type = self.type_buttons.checkedButton().text().lower()
        

class editDialog(QDialog):
    def __init__(self,path,parent=None):
        self.parent = parent
        super().__init__(parent)
        self.setWindowModality(qt.WindowModal)
        self.setWindowTitle("Edit playlist info")
        self.path = path
        self.plst = playlist.Playlist(path=self.path)
        self.name = self.plst.name
        self.description = self.plst.description
        self.ui()
        self.Layout()
        self.name_field.setText(self.name)
        self.description_field.setPlainText(self.description)

    def ui(self):
        self.name_field = QLineEdit(self)
        self.description_field = QTextEdit(self)
        self.confirm_button = confirmButton("Confirm",self)
        self.cancel_button = cancelButton("Cancel", self)
        self.name_field.setPlaceholderText("Playlist name")
        self.description_field.setPlaceholderText("Playlist description")
        self.description_field.setTabChangesFocus(True)
        self.confirm_button.clicked.connect(self.onConfirm)
        self.cancel_button.clicked.connect(self.close)

    def Layout(self):
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.name_field)
        self.layout.addWidget(self.description_field)
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.confirm_button)
        buttons_layout.addWidget(self.cancel_button)
        self.layout.addLayout(buttons_layout)

    def onConfirm(self):
        os.remove(self.path)
        self.name = self.name_field.text()
        self.description = self.description_field.toPlainText()
        self.plst.name = self.name
        self.plst.setDescription(self.description)
        self.plst.save(overried=True)
        del self.plst
        self.parent.playlists_box.relist()
        self.close()

class playlistsList(QListWidget):
    def __init__(self,parent=None):
        self.parent= parent
        super().__init__(parent)
        self.relist()
        self.itemActivated.connect(self.onEdit)
        self.itemClicked.connect(self.onEdit)
        contextMenu(self,self.context_menu)

    def onDelete(self):
        playlist = self.currentItem().text()
        if os.path.exists(playlists[playlist].path):
            os.remove(playlists[playlist].path)
            self.relist()

    def onEdit(self):
        playlist = self.currentItem().text()
        d = editDialog(playlists[playlist].path,self.parent)
        d.exec()

    def relist(self):
        self.clearAll()
        initialize()
        if len(playlists)!=0:
            for playlist in playlists:
                self.addItem(playlists[playlist].name)

    def clearAll(self):
        if len(playlists)>1:
            playlists.clear()
        self.clear()


    def context_menu(self):
        if self.currentItem() is not None:
            menu = QMenu("Menu")
            menuItem(menu,"Edit",self.onEdit,self)
            menuItem(menu,"Delete",self.onDelete,self)
            menu.exec()

class trackDialog(fileDialog):
    def __init__(self,playlist,parent=None):
        self.playlist = playlist
        self.parent = parent
        super().__init__("Select tracks to add to playlist",self.parent)
    def onConfirm(self):
        if len(self.files)>0:
            for file in self.files:
                playlists[self.playlist].addEntry(file)
            playlists[self.playlist].save()
        super().onConfirm()

class plst_list(listctrl):
    def __init__(self,parent=None):
        self.parent = parent
        super().__init__(self.parent)
        contextMenu(self,self.context_menu)
        self.itemActivated.connect(self.onTrack)
        self.itemClicked.connect(self.onTrack)

    def onTrack(self):
        item = self.parent.playlists_box.currentItem()
        playlist = item.text() if item is not None else None
        track = self.currentItem().text()
        if playlist is not None:
            path = playlists[playlist].tracks[track].path
            format = getFormat(path)
            if os.path.exists(path)==True:
                if format in f.audio:
                    self.parent.audioLoad(path,playlist=playlists[playlist])
                elif format in f.video:
                    self.parent.videoLoad(path,playlist=playlists[playlist])
            else:
                messageBox("non existent path",f"path {path} is not found")

    def relist(self):
        self.clearAll()
        self.column(0,"title")
        self.column(1,"album")
        self.column(2,"artist")

        item = self.parent.playlists_box.currentItem()
        playlist = item.text() if item is not None else None
        if playlist is not None:
            if len(playlists[playlist].tracks)>0:
                for track in playlists[playlist].tracks:
                    t = self.appendRow({0:str(playlists[playlist].tracks[track].title),1:str(playlists[playlist].tracks[track].album),2:str(playlists[playlist].tracks[track].artist)})
                    t.setText(track)
            if self.count()>0: self.setCurrentRow(1)

    def addTrack(self):
        d = trackDialog(self.parent.playlists_box.currentItem().text(),self)
        d.exec()
        self.relist()

    def deleteTrack(self):
        playlist = self.parent.playlists_box.currentItem().text()
        track_index = self.getCurrentRowIndex()-1
        name = list(playlists[playlist].tracks.keys())[track_index]
        playlists[playlist].removeEntry(name)
        self.removeRow(track_index+1)
        playlists[playlist].save()

    def deleteAll(self):
        playlist = self.parent.playlists_box.currentItem().text()
        playlists[playlist].clear()
        self.relist
        playlists[playlist].save()

    def context_menu(self):
        if self.parent.playlists_box.currentItem() is not None or self.currentItem() is not None:
            menu = QMenu(self)
            menuItem(menu,"Add tracks",self.addTrack,self)
            menuItem(menu,"Delete",self.deleteTrack,self)
            menuItem(menu,"Clear all",self.deleteAll,self)
            menu.exec()
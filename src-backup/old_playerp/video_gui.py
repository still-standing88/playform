import prefs, wmp, player
from PySide6.QtWidgets import QWidget, QListView, QStyledItemDelegate, QMenu, QPushButton, QTextEdit
from PySide6.QtGui import QAction, QActionGroup, QFocusEvent, QFontMetrics, QKeyEvent, QPainter
from PySide6.QtCore import QStringListModel, QSize, QRect
from PySide6.QtCore import Qt as qt
from functions import menuItem, resolutions, speeds, messageBox, youtube_url
import subtitles as st


def initialize():
    global player
    global videoInstance
    player = None
    videoInstance = None

class titleField(QTextEdit):
    def __init__(self,text,parent=None):
        self.parent = parent
        super().__init__(self.parent)
        self.parent.Layout.addWidget(self)
        self.setReadOnly(True)
        self.setTabChangesFocus(True)
        self.setPlainText(text)
        self.setFocus()

    def destroy(self):
        self.parent.Layout.removeWidget(self)
        self.deleteLater()

    def focusOutEvent(self, e: QFocusEvent) -> None:
        self.destroy()
        return super().focusOutEvent(e)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        key = e.key()
        if key==qt.Key_Escape:
            self.destroy()
        else:
            return super().keyPressEvent(e)


class textItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        painter.save()
        text = index.data(qt.DisplayRole)
        rect = option.rect
        font_metrics = QFontMetrics(option.font)
        painter.drawText(rect, qt.TextWordWrap, text)
        painter.restore()

    def sizeHint(self, option, index):
        text = index.data(qt.DisplayRole)
        font_metrics = QFontMetrics(option.font)
        rect = QRect(0, 0, option.rect.width(), 0)
        text_rect = font_metrics.boundingRect(rect, qt.TextWordWrap, text)
        return QSize(option.rect.width(), text_rect.height())

class titlesList(QListView):
    def __init__(self, stringList, parent: QWidget | None = ...) -> None:
        self.stringList = stringList
        self.parent = parent
        super().__init__(self.parent)
        self.hide()
        self.parent.Layout.insertWidget(1,self)
        self.delegate = textItemDelegate(self)
        self.model  = QStringListModel()
        self.setItemDelegate(self.delegate)
        self.setModel(self.model)
        self.model.setStringList(self.stringList)
        self.activated.connect(self.displayText)
        self.clicked.connect(self.displayText)

    def updateStringList(self,stringList):
        self.stringList = stringList
        self.model.setStringList(self.stringList)

    def displayText(self):
        text_field = titleField(self.parent.sub_titles[self.currentIndex().row()].text,self.parent)



class Video(player.Player):
    def __init__(self,parent,name,path,playlist=None,url=False):
        self.url = url
        self.parent = parent
        self.path = path
        self.name = name
        self.playlist = playlist
        self.type = "video"
        self.videoDisplay()
        global player
        player = wmp.video(self.video_display.winId())
        self.player = player
        self.vid = player
        self.instance = player
#        self.setpath()
        super().__init__(self.parent,self.name,self.path,playlist,url)
        self.getTitles()
        self.videoControls()
        self.setGeometry(260,200,640,480)

    def setpath(self):
        super().setpath()
        if self.path != "" or self.path is not None:
            self.instance.load(self.path)
            self.fullscreen = self.instance.fullscreen

    def changePath(self,path,playlist=None,url=False):
        self.playlist = playlist
        self.url = url
        super().changePath(path)
        if player.state() == wmp.WMP_STATE_PLAYING:
            self.controls.playbackStop()
        player.load(self.path)
        self.controls.markload()
        self.fullscreen = self.instance.fullscreen
        if self.url == False: self.getTitles()
        if self.playlist is not None: self.playlist_files()
        self.nameFromUrl()

    def nameFromUrl(self):
        if self.url ==True:
            try:
                name = youtube_url(self.url)
                self.setName()
            except Exception as e:
                messageBox("Error",e)


    def videoDisplay(self):
        self.video_display = QWidget()
        self.video_display.setAttribute(qt.WA_DontCreateNativeAncestors)
        self.video_display.setAttribute(qt.WA_NativeWindow)

    def videoControls(self):
        self.vControls_button = QPushButton("More controls",self)
        self.vControls_button.clicked.connect(self.viewV_controls)
        self.controls.hb3l.addWidget(self.vControls_button)
        self.controlsMenu()

    def controlsMenu(self):
        self.controls_menu = QMenu("Video Controls",self)
        self.speed_menu = QMenu("Playback Speed")
        speedy_actions = QActionGroup(self)
        for value in speeds:
            action = QAction(str(value),self)
            speedy_actions.addAction(action)
            action.triggered.connect(self.setSpeed)
            action.setCheckable(True)
            self.speed_menu.addAction(action)
        self.resolution_menu = QMenu("video scale")
        res_actions = QActionGroup(self)
        for resolution in resolutions:
            action = QAction(resolution,self)
            action.triggered.connect(self.setScale)
            action.setCheckable(True)
            res_actions.addAction(action)
            self.resolution_menu.addAction(action)
        self.fullscreen_action = QAction("full screen",self)
        self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.setChecked(self.instance.fullscreen())
        self.fullscreen_action.triggered.connect(self.fullScreen)
        self.controls_menu.addMenu(self.resolution_menu)
        self.controls_menu.addMenu(self.speed_menu)
        self.controls_menu.addAction(self.fullscreen_action)
        self.titles_action = QAction("Show Subtitles",self)
        self.titles_action.setCheckable(True)
        if hasattr(self,"titles_list"):
            self.titles_action.setChecked(self.titles_list.isVisible())
            self.titles_action.setEnabled(True)
        else:
            self.titles_action.setEnabled(False)
        self.titles_action.triggered.connect(self.onTitles)
        self.controls_menu.addAction(self.titles_action)
#        self.controls_menu.exec_(self.mapToGlobal(self.rect().bottomLeft()))
#        self.controls_menu.hide()

    def setSpeed(self,value):
        self.instance.playbackSpeed(float(self.sender().text()))

    def setScale(self,value):
        self.instance.setResolution(resolutions[self.sender().text()]["width"],resolutions[self.sender().text()]["height"])

    def fullScreen(self):
        if self.fullscreen() == True:
            self.fullscreen_action.setChecked(False)
            self.instance.fullScreen(False)
        elif self.fullscreen() == False:
            self.fullscreen_action.setChecked(True)
            self.instance.fullScreen(True)

    def onTitles(self):
        state = self.titles_list.isVisible()
        if state == True:
            self.titles_action.setChecked(False)
            self.titles_list.hide()
        elif state==False:
            self.titles_action.setChecked(True)
            self.titles_list.show()
            self.titles_list.setFocus()

    def getTitles(self):
        self.sub_titles = st.get_titles(self.path)
        if self.sub_titles != None:
            self.titlesList = []
            for title in self.sub_titles:
                self.titlesList.append(title.text)
            if hasattr(self,"titles_list") == True: self.titles_list.updateStringList(self.titlesList)
            else: self.titles_list = titlesList(self.titlesList,self)
        elif  self.sub_titles == None and hasattr(self,"titles_list") == True:
            self.layout.removeWidget(self.titles_list)
            self.titles_list.deleteLater()
            self.titles_action.setEnabled(False)

    def viewV_controls(self):
        state = self.controls_menu.isVisible()
        if state == True:
            self.controls_menu.hide()
        elif state == False:
            self.controls_menu.show()

    def closeEvent(self,e):
        self.instance.close()
        super().closeEvent(e)

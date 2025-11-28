from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QPushButton, 
    QTextEdit, QListWidget, QCheckBox, QSpinBox, QLabel, 
    QSplitter, QGroupBox
)
from PySide6.QtCore import Qt as qt

from typing import Optional
from av_play import mpv_video_player, formats, AVMediaInstance, AVPlaybackState
from app_config import prefs
from app_db import UserFiles
from .explorer import Explorer
from .explorer_view import ExplorerView
from .library_view import LibraryView


extensions = list(map(lambda ext: f".{ext}", formats["audio"] + formats["video"]))


class ExplorerWidget(QWidget):

    
    def __init__(self, user_db:UserFiles, **kw):
        self._user_db = user_db
        self._player:mpv_video_player.MPVVideoPlayer = mpv_video_player.MPVVideoPlayer()
        self._instance:Optional[AVMediaInstance] = None
        self._explorer = Explorer(extensions)

        super().__init__(kw.get("parent", None))
        self.setWindowTitle("Explorer")
        
        self._callbacks = {**kw,
        "path_change_callback": self.update_path,
        "library_callback": lambda path: self.add_to_library(path)
        }
        
        self._setup_ui()
        self._player.init(window=self.video_widget.winId())


    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        title_label = QLabel("Explorer")
        main_layout.addWidget(title_label)
        main_splitter = QSplitter(qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        left_panel = QGroupBox("Library")
        left_layout = QVBoxLayout(left_panel)
        
        main_splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        path_group = QGroupBox("Path")
        path_layout = QVBoxLayout(path_group)
        self.parent_btn = QPushButton("Parent Directory")
        self.parent_btn.clicked.connect(self.backward)
        path_layout.addWidget(self.parent_btn)

        self.path_edit = QTextEdit()
        self.path_edit.setTabChangesFocus(True)
        path_layout.addWidget(self.path_edit)
        right_layout.addWidget(path_group)
        
        content_splitter = QSplitter(qt.Orientation.Vertical)
        right_layout.addWidget(content_splitter)
        explorer_group = QGroupBox("Files")
        explorer_layout = QVBoxLayout(explorer_group)

        self.explorer_view = ExplorerView(self._explorer, self._player, **{"parent": self, **self._callbacks})
        explorer_layout.addWidget(self.explorer_view)

        self.library_view = LibraryView(self._user_db, self,
        navigate_callback=lambda path: self.explorer_view.change_path(path)
        )
        left_layout.addWidget(self.library_view)

        content_splitter.addWidget(explorer_group)
        
        preview_group = QGroupBox("Media Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.video_widget = QWidget()
        self.video_widget.setAttribute(qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.video_widget.setAttribute(qt.WidgetAttribute.WA_NativeWindow)
        preview_layout.addWidget(self.video_widget)
        
        content_splitter.addWidget(preview_group)
        main_splitter.addWidget(right_panel)
        
        controls_layout = QHBoxLayout()
        self.autoplay_cb = QCheckBox("Auto Play")
        self.autoplay_cb.stateChanged.connect(self.autoplayState)
        self.autoplay_cb.setChecked(prefs.prefs["autoplay"])
        controls_layout.addWidget(self.autoplay_cb)
        controls_layout.addStretch()
        
        volume_label = QLabel("Volume:")
        controls_layout.addWidget(volume_label)
        self.volume_spinbox = QSpinBox()
        self.volume_spinbox.setValue(100)
        self.volume_spinbox.setRange(0, 100)
        self.volume_spinbox.setSuffix("%")
        self.volume_spinbox.setAccessibleName("volume")
        self.volume_spinbox.valueChanged.connect(self.volumeChange)
        controls_layout.addWidget(self.volume_spinbox)
        
        main_layout.addLayout(controls_layout)

    def repeat_media(self):
        if prefs.prefs['repeat'] == True:
            if self._instance is not None:
                try:
                    if self._instance.get_playback_state == AVPlaybackState.AV_STATE_STOPPED:
                        self._instance.play()
                except:
                    pass


    def volumeChange(self, value):
        if self._instance is not None:
            try:
                self._instance.set_volume(value)
            except:
                pass
        else:
             self._instance = self._player.primary_instance
             if self._instance is not None: 
                 try:
                     self._instance.set_volume(value)
                 except:
                     pass

    def autoplayState(self, state):
        if state == 2:
            prefs.prefs['autoplay'] = True
        elif state == 0:
                prefs.prefs['autoplay'] = False
        prefs.save()

    def update_path(self):
        self.path_edit.setText(self._explorer.current_path)

    def backward(self):
        self.explorer_view.backward()

    def add_to_library(self, path):
        self.library_view.add_path(path)
import os
import sys
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QTreeView, QPushButton, 
    QTextEdit, QListWidget, QCheckBox, QSpinBox, QLabel, 
    QSplitter, QGroupBox
)
from PySide6.QtCore import Qt as qt, QTimer, Slot
from PySide6.QtGui import QKeyEvent, QPalette, QColor, QPixmap

from typing import Optional, Callable
import utilities.vlc_bootstrap
from av_play import VLCVideoPlayer, AVMediaInstance, AVPlaybackState
from utilities.formats import formats, image_extensions
from app_config import prefs
from app_constance.vlc_args import log_args
from app_constance.styles import COLORS
from app_db import UserFiles
from .explorer import Explorer
from .explorer_view import ExplorerView
from .library_view import LibraryView
from .play_bar import PlayerBar
from utilities.functions import get_vlclog_file, get_debug_level, initialize_com


extensions = list(map(lambda ext: f".{ext}", formats["audio"] + formats["video"])) + list(image_extensions)

class PathEdit(QTextEdit):


    def __init__(self, callback:Callable, parent = None):
        super().__init__(parent)
        self._callback = callback
        self.setTabChangesFocus(True)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() in [qt.Key.Key_Enter, qt.Key.Key_Return]:
            self._callback()
        else:
            return super().keyPressEvent(e)


class ExplorerWidget(QWidget):

    
    def __init__(self, user_db:UserFiles, **kw):
        self._user_db = user_db
        self._player:VLCVideoPlayer = VLCVideoPlayer()
        self._instance:Optional[AVMediaInstance] = None
        self._explorer = Explorer(extensions)

        super().__init__(kw.get("parent", None))
        self.setWindowTitle(_("Explorer"))
        
        self._callbacks = {**kw,
        "path_change_callback": self.update_path,
        "library_callback": lambda path: self.add_to_library(path),
        "image_preview_callback": self._on_image_preview,
        }
        vlc_args = list(log_args)
        if prefs.prefs.get("vlc_logging", True):
            vlc_args.extend([
                "--file-logging",
                "--logmode", "text",
                "--logfile", get_vlclog_file(),
                "--verbose", str(int(get_debug_level()))
            ])

        device_name = prefs.prefs.get("device_name", "")
        device_id = None
        if device_name and sys.platform.startswith("win"):
            try:
                import vlc as _vlc
                tmp = _vlc.Instance(["--intf", "dummy"])
                head = tmp.audio_output_device_list_get("mmdevice")
                if head:
                    cur = head
                    while cur:
                        cur = cur.contents
                        if cur.description.decode('utf-8', errors='ignore') == device_name:
                            device_id = cur.device.decode('utf-8', errors='ignore')
                            break
                        cur = cur.next
                    _vlc.libvlc_audio_output_device_list_release(head)
                tmp.release()
            except Exception:
                pass

        self._setup_ui()
        self._player.init(vlc_args=vlc_args, device_id=device_id)
        self._player.set_window(self.video_widget.winId())
        
        device_name = prefs.prefs.get("device_name", "")
        if device_name:
            device_count = self._player.get_devices()
            for i in range(device_count):
                device_info = self._player.get_device(i)
                if device_info and device_info.name == device_name:
                    self._player.set_device(i)
                    break
        else:
            device = prefs.prefs.get("device", 0)
            if device < self._player.get_devices():
                self._player.set_device(device)


    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        title_label = QLabel(_("Explorer"))
        main_layout.addWidget(title_label)
        main_splitter = QSplitter(qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        left_panel = QGroupBox(_("Library"))
        left_layout = QVBoxLayout(left_panel)
        
        main_splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        path_group = QGroupBox(_("Path"))
        path_layout = QVBoxLayout(path_group)
        self.parent_btn = QPushButton(_("Parent Directory"))
        self.parent_btn.clicked.connect(self.backward)
        path_layout.addWidget(self.parent_btn)

        self.path_edit = PathEdit(self.set_path)

        path_layout.addWidget(self.path_edit)
        right_layout.addWidget(path_group)
        
        content_splitter = QSplitter(qt.Orientation.Vertical)
        right_layout.addWidget(content_splitter)
        explorer_group = QGroupBox(_("Files"))
        explorer_layout = QVBoxLayout(explorer_group)

        files_splitter = QSplitter(qt.Orientation.Horizontal)

        self.explorer_view = ExplorerView(self._explorer, self._player, **{"parent": self, **self._callbacks})
        files_splitter.addWidget(self.explorer_view)

        self.image_preview_label = QLabel()
        self.image_preview_label.setAlignment(qt.AlignmentFlag.AlignCenter)
        self.image_preview_label.setMinimumWidth(200)
        self.image_preview_label.hide()
        files_splitter.addWidget(self.image_preview_label)

        files_splitter.setStretchFactor(0, 3)
        files_splitter.setStretchFactor(1, 2)

        explorer_layout.addWidget(files_splitter)

        self.library_view = LibraryView(self._user_db, self,
        navigate_callback=lambda path: self.explorer_view.change_path(path)
        )
        left_layout.addWidget(self.library_view)

        content_splitter.addWidget(explorer_group)
        
        preview_group = QGroupBox(_("Media Preview"))
        preview_layout = QVBoxLayout(preview_group)
        self.video_widget = QFrame(self)
        self.vid_palette = self.video_widget.palette()
        self.vid_palette.setColor(QPalette.ColorRole.Window, COLORS['black'])
        self.video_widget.setPalette(self.vid_palette)
        self.video_widget.setAutoFillBackground(True)

        preview_layout.addWidget(self.video_widget)
        
        self.player_bar = PlayerBar(self)
        preview_layout.addWidget(self.player_bar)
        
        self.player_bar.playPauseToggled.connect(self.explorer_view.on_playbar_play_pause)
        self.player_bar.forwardTriggered.connect(self.explorer_view.media_forward)
        self.player_bar.backwardTriggered.connect(self.explorer_view.media_backward)
        self.player_bar.seekRequested.connect(self.explorer_view.on_playbar_seek)
        
        self.explorer_view.set_player_bar(self.player_bar)
        
        content_splitter.addWidget(preview_group)
        main_splitter.addWidget(right_panel)
        
        media_group = QGroupBox(_("Media"))
        controls_layout = QHBoxLayout(media_group)
        self.autoplay_cb = QCheckBox(_("Auto Play"))
        self.autoplay_cb.stateChanged.connect(self.autoplayState)
        self.autoplay_cb.setChecked(prefs.prefs["autoplay"])
        controls_layout.addWidget(self.autoplay_cb)
        controls_layout.addStretch()

        volume_label = QLabel(_("Volume:"))
        controls_layout.addWidget(volume_label)
        self.volume_spinbox = QSpinBox()
        self.volume_spinbox.setValue(100)
        self.volume_spinbox.setRange(0, 100)
        self.volume_spinbox.setSuffix("%")
        self.volume_spinbox.setAccessibleName(_("volume"))
        self.volume_spinbox.valueChanged.connect(self.volumeChange)
        controls_layout.addWidget(self.volume_spinbox)

        main_layout.addWidget(media_group)

    def repeat_media(self):
        if prefs.prefs['repeat'] == True:
            if self._instance is not None:
                try:
                    if self._instance.get_playback_state() == AVPlaybackState.AV_STATE_STOPPED:
                        self._instance.play()
                except:
                    pass


    @Slot(int)
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

    @Slot(int)
    def autoplayState(self, state):
        if state == 2:
            prefs.prefs['autoplay'] = True
        elif state == 0:
                prefs.prefs['autoplay'] = False
        prefs.save()

    def update_path(self):
        self.path_edit.setText(self._explorer.current_path)

    def set_path(self):
        new_path = self.path_edit.toPlainText()
        self.explorer_view.change_path(new_path)

    @Slot()
    def backward(self):
        self.explorer_view.backward()

    def add_to_library(self, path):
        self.library_view.add_path(path)

    def _on_image_preview(self, path: str):
        if path:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.image_preview_label.width() or 400,
                    self.image_preview_label.height() or 400,
                    qt.AspectRatioMode.KeepAspectRatio,
                    qt.TransformationMode.SmoothTransformation,
                )
                self.image_preview_label.setPixmap(scaled)
                self.image_preview_label.show()
                return
        self.image_preview_label.hide()

    def reset_shortcuts(self):
        pass

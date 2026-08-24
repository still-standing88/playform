import os
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QTreeView, QPushButton,
    QLineEdit, QListWidget, QCheckBox, QSpinBox, QLabel,
    QSplitter, QGroupBox, QToolBar, QComboBox, QScrollArea
)
from PySide6.QtCore import Qt as qt, QTimer, Slot
from PySide6.QtGui import QPalette, QColor, QPixmap, QAction, QActionGroup, QShortcut, QKeySequence

from typing import Optional, Callable, Dict
import utilities.mpv_bootstrap
from media_core.av_play import VideoPlayer, AVMediaInstance, AVPlaybackState
from utilities.formats import formats, image_extensions
from app_config import prefs, key_config
from app_constance.styles import COLORS
from app_db import UserFiles
from gui_controls.player_key_event_filter import KeyEventFilter
from .explorer import Explorer
from .explorer_view import ExplorerView
from .library_view import LibraryView
from .play_bar import PlayerBar
from utilities.functions import get_mpvlog_file, get_debug_level, initialize_com, parse_mpv_options


extensions = list(map(lambda ext: f".{ext}", formats["audio"] + formats["video"])) + list(image_extensions)
video_extensions = set(formats["video"])


class ExplorerWidget(QWidget):

    
    def __init__(self, user_db:UserFiles, **kw):
        self._user_db = user_db
        self._player:VideoPlayer = VideoPlayer()
        self._instance:Optional[AVMediaInstance] = None
        self._explorer = Explorer(extensions, sort_mode=prefs.prefs.get("explorer_sort_mode", "name_asc"))
        self._shortcuts: Dict[str, QShortcut] = {}
        self._video_preview_active = False
        self._video_preview_applied: Optional[bool] = None

        super().__init__(kw.get("parent", None))
        self.setWindowTitle(_("Explorer"))

        self._callbacks = {**kw,
        "path_change_callback": self.update_path,
        "library_callback": lambda path: self.add_to_library(path),
        "image_preview_callback": self._on_image_preview,
        "image_preview_dialog_callback": self.show_image_preview_dialog,
        "media_preview_callback": self._on_media_preview,
        "queue_callback": self._on_queue_requested,
        }
        config: dict = {}
        # See player_init.py: mpv clamps set_volume() at its own default
        # volume-max regardless of what's requested, independent of this
        # spinbox's own range.
        config["volume"] = prefs.prefs.get("explorer_volume", 120)
        config["volume_max"] = 300

        if prefs.prefs.get("mpv_logging", True):
            level_map = {0: "error", 1: "info", 2: "debug"}
            config["log_file"] = get_mpvlog_file()
            config["msg_level"] = f"all={level_map.get(get_debug_level(), 'info')}"

        extra_options = prefs.prefs.get("mpv_extra_options", "")
        if extra_options:
            try:
                config.update(parse_mpv_options(extra_options))
            except Exception:
                pass

        self._setup_ui()

        self._key_event_filter = KeyEventFilter(self)
        self._install_key_event_filter()
        self.set_shortcuts()
        self._setup_tab_order()

        self._player.init(config=config)
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
        # No separate title label here - the dock widget's own title bar
        # already reads "Explorer" right above this, so a second one was
        # just always-visible chrome duplicating it for free.
        main_splitter = QSplitter(qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        left_panel = QGroupBox(_("Library"))
        left_layout = QVBoxLayout(left_panel)
        
        main_splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        location_group = QGroupBox(_("Path && Search"))
        location_layout = QVBoxLayout(location_group)

        path_row = QHBoxLayout()
        self.parent_btn = QPushButton(_("Parent Directory"))
        self.parent_btn.clicked.connect(self.backward)
        path_row.addWidget(self.parent_btn)

        self.path_edit = QLineEdit()
        self.path_edit.setAccessibleName(_("Current path"))
        self.path_edit.returnPressed.connect(self.set_path)
        path_row.addWidget(self.path_edit, 1)
        location_layout.addLayout(path_row)

        self.search_edit = QComboBox()
        self.search_edit.setEditable(True)
        self.search_edit.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.search_edit.lineEdit().setPlaceholderText(_("Search current folder..."))
        self.search_edit.setAccessibleName(_("Search current folder"))
        if prefs.prefs.get("store_search_history", True):
            self.search_edit.addItems(prefs.prefs.get("search_history", []))
        self.search_edit.setCurrentText("")
        self.search_edit.lineEdit().returnPressed.connect(self._on_search_submitted)
        location_layout.addWidget(self.search_edit)
        right_layout.addWidget(location_group)

        content_splitter = QSplitter(qt.Orientation.Vertical)
        self._content_splitter = content_splitter
        right_layout.addWidget(content_splitter)
        explorer_group = QGroupBox(_("Files"))
        explorer_layout = QVBoxLayout(explorer_group)

        files_splitter = QSplitter(qt.Orientation.Horizontal)

        self.explorer_view = ExplorerView(self._explorer, self._player, **{"parent": self, **self._callbacks})
        files_splitter.addWidget(self.explorer_view)

        self.toolbar = QToolBar(_("Explorer Toolbar"))
        self.toolbar.setToolButtonStyle(qt.ToolButtonStyle.ToolButtonTextOnly)

        self.view_mode_group = QActionGroup(self)
        self.view_mode_group.setExclusive(True)

        self.view_list_action = QAction(_("List View"), self)
        self.view_list_action.setCheckable(True)
        self.view_list_action.triggered.connect(lambda: self._on_view_mode_selected(list_mode=True))
        self.view_mode_group.addAction(self.view_list_action)
        self.toolbar.addAction(self.view_list_action)

        self.view_icon_action = QAction(_("Icon View"), self)
        self.view_icon_action.setCheckable(True)
        self.view_icon_action.triggered.connect(lambda: self._on_view_mode_selected(list_mode=False))
        self.view_mode_group.addAction(self.view_icon_action)
        self.toolbar.addAction(self.view_icon_action)

        saved_view_mode = prefs.prefs.get("explorer_view_mode", "list")
        if saved_view_mode == "icon":
            self.view_icon_action.setChecked(True)
        else:
            self.view_list_action.setChecked(True)
        self.explorer_view.set_view_mode(list_mode=(saved_view_mode != "icon"))

        self.toolbar.addSeparator()

        self.refresh_action = QAction(_("Refresh"), self)
        self.refresh_action.setShortcut(qt.Key.Key_F5)
        self.refresh_action.setShortcutContext(qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.refresh_action.triggered.connect(self.explorer_view.refresh)
        self.toolbar.addAction(self.refresh_action)
        self.addAction(self.refresh_action)

        self.toolbar.addSeparator()

        self.add_to_database_action = QAction(_("Add Current Folder to Database"), self)
        self.add_to_database_action.triggered.connect(self._on_add_current_folder_to_database)
        self.toolbar.addAction(self.add_to_database_action)

        # Index 0, not 1 - main_splitter was added first (there's no title
        # label above it anymore), so this needs to land before it.
        main_layout.insertWidget(0, self.toolbar)

        self.image_preview_label = QLabel()
        self.image_preview_label.setAlignment(qt.AlignmentFlag.AlignCenter)
        # 80, not 200: this label plus the files list's own minimum width was
        # enough to force horizontal scrolling as soon as an image preview
        # appeared in a narrow dock.
        self.image_preview_label.setMinimumWidth(self.IMAGE_PREVIEW_MIN_WIDTH)
        self.image_preview_label.hide()
        files_splitter.addWidget(self.image_preview_label)

        files_splitter.setStretchFactor(0, 3)
        files_splitter.setStretchFactor(1, 2)
        files_splitter.setCollapsible(1, True)

        explorer_layout.addWidget(files_splitter)

        self.library_view = LibraryView(self._user_db, self,
        navigate_callback=lambda path: self.explorer_view.change_path(path)
        )
        left_layout.addWidget(self.library_view)

        content_splitter.addWidget(explorer_group)
        
        preview_group = QGroupBox(_("Media Preview"))
        self._preview_group = preview_group
        preview_layout = QVBoxLayout(preview_group)
        self.video_widget = QFrame(self)
        self.vid_palette = self.video_widget.palette()
        self.vid_palette.setColor(QPalette.ColorRole.Window, COLORS['black'])
        self.video_widget.setPalette(self.vid_palette)
        self.video_widget.setAutoFillBackground(True)
        # Same native-window attributes as the main player's VideoDisplayWidget.
        # Without WA_DontCreateNativeAncestors, winId() below forces every
        # ancestor up the widget tree to also get a real native window instead
        # of Qt's lightweight "alien widget" rendering -- a real source of
        # GPU/compositing instability once MPV's wid-embedded video is hosted
        # here alongside the main player's own native window hierarchy.
        self.video_widget.setAttribute(qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.video_widget.setAttribute(qt.WidgetAttribute.WA_NativeWindow)

        preview_layout.addWidget(self.video_widget)
        
        self.player_bar = PlayerBar(self)
        preview_layout.addWidget(self.player_bar)
        
        self.player_bar.playPauseToggled.connect(self.explorer_view.on_playbar_play_pause)
        self.player_bar.forwardTriggered.connect(self.explorer_view.media_forward)
        self.player_bar.backwardTriggered.connect(self.explorer_view.media_backward)
        self.player_bar.seekRequested.connect(self.explorer_view.on_playbar_seek)
        
        self.explorer_view.set_player_bar(self.player_bar)
        
        content_splitter.addWidget(preview_group)
        # QFrame's sizeHint is (-1, -1), so without stretch factors the
        # preview pane was handed exactly its own sizeHint (the player bar
        # alone) and video_widget sat at 0px height forever - the Media
        # Preview group never actually showed picture. Stretch alone isn't
        # enough either, which is what _set_video_preview_active handles.
        content_splitter.setStretchFactor(0, 3)
        content_splitter.setStretchFactor(1, 2)
        content_splitter.setCollapsible(1, False)
        main_splitter.addWidget(right_panel)
        
        media_row = QWidget()
        controls_layout = QHBoxLayout(media_row)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        self.autoplay_cb = QCheckBox(_("Auto Play"))
        self.autoplay_cb.stateChanged.connect(self.autoplayState)
        self.autoplay_cb.setChecked(prefs.prefs["autoplay"])
        controls_layout.addWidget(self.autoplay_cb)

        self.loop_cb = QCheckBox(_("Loop"))
        self.loop_cb.stateChanged.connect(self.loopState)
        self.loop_cb.setChecked(prefs.prefs.get("explorer_loop", False))
        controls_layout.addWidget(self.loop_cb)
        controls_layout.addStretch()

        volume_label = QLabel(_("Volume:"))
        controls_layout.addWidget(volume_label)
        self.volume_spinbox = QSpinBox()
        self.volume_spinbox.setRange(0, 300)
        self.volume_spinbox.setValue(prefs.prefs.get("explorer_volume", 120))
        self.volume_spinbox.setSuffix("%")
        self.volume_spinbox.setAccessibleName(_("volume"))
        self.volume_spinbox.valueChanged.connect(self.volumeChange)
        controls_layout.addWidget(self.volume_spinbox)

        # main_splitter's combined content (Library plus Path/Search/Files/
        # Media Preview, each in its own QGroupBox) has a large minimum
        # height once every group box's own padding stacks on top of its
        # content's minimum. Explorer normally docks alongside the Player
        # dock, which has the exact same problem (already fixed) - both
        # competing for one shared vertical budget means every pixel of
        # always-visible chrome on either side directly steals from the
        # other. So the splitter scrolls, and the floor is a modest 150px
        # for the same reason as the Player accordion's floor: guarantee
        # *something* is always reachable without scrolling, not the whole
        # panel at once. Auto Play/Loop/Volume stay pinned below it as a
        # frameless row - inside the scroll area they were the last child
        # and so the first thing to disappear, which is exactly the
        # "volume isn't on screen" bug; frameless costs ~30px against the
        # 61px the QGroupBox version cost.
        splitter_index = main_layout.indexOf(main_splitter)
        main_layout.removeWidget(main_splitter)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.addWidget(main_splitter, 1)
        self.splitter_scroll = QScrollArea(self)
        self.splitter_scroll.setWidget(scroll_content)
        self.splitter_scroll.setWidgetResizable(True)
        self.splitter_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.splitter_scroll.setMinimumHeight(self.IDEAL_CONTENT_FLOOR)
        main_layout.insertWidget(splitter_index, self.splitter_scroll, 1)
        main_layout.addWidget(media_row)

    # Recomputed fresh on every clamp_to_screen() pass (see DockManager) -
    # never mutated cumulatively, so plugging into a bigger screen restores
    # the full, comfortable floor rather than leaving it permanently shrunk
    # from whatever the smallest screen ever seen last demanded.
    IDEAL_CONTENT_FLOOR = 150
    MIN_CONTENT_FLOOR = 0

    def set_content_floor(self, px: int):
        self.splitter_scroll.setMinimumHeight(max(self.MIN_CONTENT_FLOOR, px))

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
        prefs.prefs["explorer_volume"] = value
        prefs.save()
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

    @Slot(int)
    def loopState(self, state):
        enabled = state == 2
        prefs.prefs['explorer_loop'] = enabled
        prefs.save()
        self.explorer_view.set_loop_enabled(enabled)

    def update_path(self):
        self.path_edit.setText(self._explorer.current_path)

    def set_path(self):
        new_path = self.path_edit.text()
        self.explorer_view.change_path(new_path)

    @Slot()
    def backward(self):
        self.explorer_view.backward()

    def add_to_library(self, path):
        self.library_view.add_path(path)

    def _on_queue_requested(self, paths):
        callback = self._callbacks.get("enqueue_files_callback")
        if callable(callback):
            callback(paths)

    def show_image_preview_dialog(self, path: str):
        if not path:
            return
        from EXPLORER.image_preview_dialog import ImagePreviewDialog
        dialog = getattr(self, "_image_preview_dialog", None)
        if dialog is None:
            dialog = ImagePreviewDialog(path, self)
            self._image_preview_dialog = dialog
        else:
            dialog.close()
            dialog = ImagePreviewDialog(path, self)
            self._image_preview_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _on_view_mode_selected(self, list_mode: bool):
        self.explorer_view.set_view_mode(list_mode=list_mode)
        prefs.prefs["explorer_view_mode"] = "list" if list_mode else "icon"
        prefs.save()

    def _on_search_submitted(self):
        query = self.search_edit.currentText().strip()
        if not query:
            return
        self.explorer_view.perform_search(query)
        if prefs.prefs.get("store_search_history", True):
            self._remember_search(query)

    def _remember_search(self, query: str):
        history = [q for q in prefs.prefs.get("search_history", []) if q != query]
        history.insert(0, query)
        history = history[:20]
        prefs.prefs["search_history"] = history
        prefs.save()

        existing_index = self.search_edit.findText(query)
        if existing_index != -1:
            self.search_edit.removeItem(existing_index)
        self.search_edit.insertItem(0, query)
        while self.search_edit.count() > 20:
            self.search_edit.removeItem(self.search_edit.count() - 1)
        self.search_edit.setCurrentIndex(0)

    def clear_search_history(self):
        prefs.prefs["search_history"] = []
        prefs.save()
        current_text = self.search_edit.currentText()
        self.search_edit.clear()
        self.search_edit.setCurrentText(current_text)

    def _on_add_current_folder_to_database(self):
        path = self._explorer.current_path
        if os.path.isdir(path):
            self._execute_callback("catalog_folder_callback", path)

    def _execute_callback(self, callback_name: str, param=None):
        callback = self._callbacks.get(callback_name, None)
        if callback is not None:
            callback(param) if param is not None else callback()

    def _on_image_preview(self, path: str):
        if path:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                target = max(self.IMAGE_PREVIEW_MIN_WIDTH, self.image_preview_label.width())
                scaled = pixmap.scaled(
                    target,
                    max(self.IMAGE_PREVIEW_MIN_WIDTH, self.image_preview_label.height()),
                    qt.AspectRatioMode.KeepAspectRatio,
                    qt.TransformationMode.SmoothTransformation,
                )
                self.image_preview_label.setPixmap(scaled)
                self.image_preview_label.show()
                return
        self.image_preview_label.hide()

    VIDEO_PREVIEW_HEIGHT = 160
    IMAGE_PREVIEW_MIN_WIDTH = 80

    def _on_media_preview(self, path: str):
        is_video = bool(path) and os.path.splitext(path)[1].lower().lstrip(".") in video_extensions
        self._set_video_preview_active(is_video)

    def _set_video_preview_active(self, active: bool):
        self._video_preview_active = active
        self._apply_video_preview_sizes()

    def _apply_video_preview_sizes(self):
        # Only redistributes the vertical splitter - deliberately never
        # touches video_widget's minimumHeight, so an idle Explorer keeps the
        # same small minimum height and no new scrolling appears inside
        # splitter_scroll. Qt takes the extra pixels from the Files pane down
        # to its own minimum and no further. _video_preview_applied tracks
        # what was actually written, so switching dock tabs (or focusing a
        # second video) doesn't undo a manual splitter drag.
        if self._video_preview_applied == self._video_preview_active:
            return
        if not self.isVisible():
            return
        total = self._content_splitter.height()
        if total <= 0:
            return
        if self._video_preview_active:
            preview = max(self.VIDEO_PREVIEW_HEIGHT, int(total * 0.4))
        else:
            preview = self._preview_group.minimumSizeHint().height()
        self._content_splitter.setSizes([max(0, total - preview), preview])
        self._video_preview_applied = self._video_preview_active

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_video_preview_sizes)

    def _setup_tab_order(self):
        # Search field must come before the library treeview in the tab
        # chain; path edit and files list follow.
        QWidget.setTabOrder(self.path_edit, self.search_edit)
        QWidget.setTabOrder(self.search_edit, self.library_view)
        QWidget.setTabOrder(self.library_view, self.explorer_view)

    def _install_key_event_filter(self):
        self._key_event_filter.install_on_widgets([
            self.library_view,
            self.path_edit,
            self.search_edit,
            self.search_edit.lineEdit(),
            self.autoplay_cb,
            self.loop_cb,
            self.volume_spinbox,
            self.parent_btn,
        ])

    def set_shortcuts(self):
        for shortcut in self._shortcuts.values():
            shortcut.setParent(None)
        self._shortcuts = {}

        hotkeys = key_config.key_config["Explorer"]
        mapping: Dict[str, Callable] = {
            hotkeys["Play/Pause"]: self.explorer_view.media_play_pause,
            hotkeys["Stop"]: self.explorer_view.media_stop,
            hotkeys["Forward"]: self.explorer_view.media_forward,
            hotkeys["Backward"]: self.explorer_view.media_backward,
            hotkeys["Search files/folders"]: self._focus_search,
        }
        for key_sequence, callback in mapping.items():
            shortcut = QShortcut(QKeySequence(key_sequence), self)
            shortcut.setContext(qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(callback)
            self._shortcuts[key_sequence] = shortcut

    def _focus_search(self):
        # QComboBox's internal line edit sets its focus proxy back to the
        # combo box itself, so the combo (not the line edit) is what ends
        # up as the actual QApplication.focusWidget().
        self.search_edit.setFocus()
        self.search_edit.lineEdit().selectAll()

    def reset_shortcuts(self):
        self.set_shortcuts()

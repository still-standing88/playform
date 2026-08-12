from genericpath import isfile
import os

from typing import Optional, Callable
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QMenu, QListWidget, QListWidgetItem, QLabel
from PySide6.QtCore import Qt as qt, Slot, QSize
import utilities.mpv_bootstrap
from media_core.av_play import AVMediaInstance, VideoPlayer, AVPlaybackState
from utilities.formats import image_extensions

from app_config import prefs
from utilities.functions import copyText
from utilities.util_gui import menuItem, contextMenu
from utilities import signal_manager
from utilities.announcement_categories import AnnouncementCategory
from .explorer import Explorer, PathInfo, PathType, ExplorerMode
from .search_worker import SearchWorker
import app_db


def _announce(text):
    signal_manager.announce(text, AnnouncementCategory.EXPLORER)


class ExplorerView(QListWidget):

    @staticmethod
    def set_last_path(path):
        prefs.prefs["last_path"] = path
        prefs.save()


    def __init__(self, explorer:Explorer, player:VideoPlayer, **kw):
        self._callbacks = kw
        self._just_launched = True
        self._current_media:Optional[str] = None
        self._focused_item_path:Optional[str] = None
        self._player = player
        self._instance:Optional[AVMediaInstance] = None
        self._loop_enabled:bool = prefs.prefs.get("explorer_loop", False)
        self._explorer = explorer
        
        self._pending_media_path:Optional[str] = None
        self._player_bar = None
        self._search_item_paths: dict[str, str] = {}

        super().__init__(kw.get("parent", None))
        self._search_worker = SearchWorker(self)
        self._search_worker.results_ready.connect(self._on_search_results)
        self._search_worker.error.connect(self._on_search_error)
        self.currentItemChanged.connect(self.onItemChange)
        self.itemClicked.connect(self.onItemActivate)
        self.itemActivated.connect(self.onItemActivate)
        contextMenu(self, self.context_menu)

        last_path = prefs.prefs["last_path"]
        if last_path != "" and os.path.exists(last_path):
            self.change_path(last_path)
        else:
            self.change_path(self._explorer.default_path)

    def set_player_bar(self, player_bar):
        self._player_bar = player_bar

    def set_loop_enabled(self, enabled: bool):
        self._loop_enabled = enabled
        if self._instance is not None:
            self._instance.set_loop(enabled)

    def open_file(self):
        if self._focused_item_path:
            self.media_stop()
            self._execute_callback("open_callback", self._focused_item_path)  # type: ignore[arg-type]

    def open_new_tab(self):
        if self._focused_item_path:
            self._execute_callback("open_new_callback", self._focused_item_path)  # type: ignore[arg-type]

    def add_to_favorites(self):
        if self._focused_item_path:
            self._execute_callback("favorites_callback", self._focused_item_path)  # type: ignore[arg-type]

    def update_path(self):
        self._execute_callback("path_change_callback", with_param=False)

    def add_to_playlist(self):
        if self._focused_item_path:
            self._execute_callback("playlist_callback", self._focused_item_path)  # type: ignore[arg-type]

    def create_playlist_from_folder(self):
        if self._focused_item_path:
            self._execute_callback("create_playlist_callback", self._focused_item_path)  # type: ignore[arg-type]

    def _sort(self, mode: str):
        self._explorer.set_sort(mode)
        prefs.prefs["explorer_sort_mode"] = mode
        prefs.save()
        self.relist_contents()

    def add_to_library(self):
        if self._focused_item_path:
            self._execute_callback("library_callback", self._focused_item_path)  # type: ignore[arg-type]

    def add_to_database(self):
        if self._focused_item_path:
            self._execute_callback("catalog_folder_callback", self._focused_item_path)  # type: ignore[arg-type]

    def copy_path(self):
        copyText(self._focused_item_path)

    def _delayed_media_load(self):
        if self._pending_media_path and self._pending_media_path != self._current_media:
            self._current_media = self._pending_media_path
            
            if self._instance is None:
                self._instance = self._player.create_file_instance(self._pending_media_path)
                # A freshly created mpv core defaults loop off - re-apply the
                # checkbox's current state, since load_file() on an existing
                # instance below keeps whatever loop state was already set on
                # it.
                self._instance.set_loop(self._loop_enabled)
            else:
                self._instance.load_file(self._pending_media_path)
            # pause(), not stop(): mpv auto-plays on load by default, and this
            # runs immediately afterward with no delay to prevent that when
            # autoplay is off. stop() is a command (mpv_command_node) and
            # reliably fails ("Error running mpv command") when issued before
            # mpv finishes opening the just-loaded file; pause() just writes
            # the read/write "pause" property instead, which doesn't race
            # (verified empirically).
            self._instance.pause()
            if not self._just_launched and prefs.prefs["autoplay"]:
                self._instance.play()
                if self._player_bar:
                    self._player_bar.setState(True)
            else:
                if self._player_bar:
                    self._player_bar.setState(False)
        self._pending_media_path = None

    def _notify_navigation_error(self):
        # Explorer already falls back to a safe folder silently on
        # permission/IO errors - surface a brief status-bar note so the
        # user isn't left wondering why they got redirected, without
        # interrupting them with a modal dialog for a routine error.
        error = self._explorer.last_navigation_error
        if error:
            _announce(_("Couldn't open {error}").format(error=error))

    def change_path(self, path:str):
        self._explorer.set_current_path(path)
        self.relist_contents()
        self.update_path()
        self.set_last_path(self._explorer.current_path)
        self._notify_navigation_error()

    def forward(self):
        if self._focused_item_path is not None:
            self._explorer.forward(self._focused_item_path)
            self.relist_contents()
            self.update_path()
            self.set_last_path(self._explorer.current_path)
            self._notify_navigation_error()

    def backward(self):
        self._search_worker.cancel()
        item_name = os.path.basename(self._explorer.current_path)
        self._explorer.backward()
        self.relist_contents()
        self.update_path()
        if item_name in self._explorer.items:
            self.setCurrentItem(self.findItems(item_name, qt.MatchFlag.MatchExactly)[0])
        self.set_last_path(self._explorer.current_path)
        self._notify_navigation_error()

    @Slot()
    def onItemActivate(self):
        if self._focused_item_path is not None:
            if os.path.isfile(self._focused_item_path):
                self.open_file()
            elif os.path.isdir(self._focused_item_path):
                self.forward()

    def relist_contents(self):
        self.clear()
        self.list_contents()

    def list_contents(self):
        if self._explorer.mode == ExplorerMode.SEARCH_RESULTS:
            self._search_item_paths = {}
            root = self._explorer.current_path
            labels = []
            for item in self._explorer.search_results:
                try:
                    label = os.path.relpath(item.path, root)
                except ValueError:
                    label = item.path
                if label in self._search_item_paths:
                    label = item.path
                self._search_item_paths[label] = item.path
                labels.append(label)
            self.addItems(labels)
        else:
            self._search_item_paths = {}
            self.addItems(self._explorer.folders + self._explorer.files)

    def set_view_mode(self, list_mode: bool):
        self.setViewMode(QListWidget.ViewMode.ListMode if list_mode else QListWidget.ViewMode.IconMode)
        if not list_mode:
            self.setGridSize(QSize(96, 96))
            self.setResizeMode(QListWidget.ResizeMode.Adjust)
            # The detail overlay widget (set_item_info) doesn't fit inside a
            # fixed icon-grid cell - drop it so Icon view shows plain
            # icons/text instead of a broken/invisible overlay.
            for i in range(self.count()):
                self.removeItemWidget(self.item(i))
        self.setWrapping(not list_mode)
        if self.currentItem() is not None:
            self.set_item_info()

    def perform_search(self, query: str):
        root_path, use_db = self._explorer.begin_search(query, media_db=app_db.media_db)
        _announce(_("Searching..."))
        self._search_worker.start_search(root_path, query, self._explorer.file_extensions, use_db)

    @Slot(str, str, list)
    def _on_search_results(self, root_path, query, paths):
        self._explorer.apply_search_results(paths)
        self.relist_contents()
        self.update_path()
        self.set_last_path(self._explorer.current_path)
        _announce(_("Search complete: {count} result(s)").format(count=len(paths)))

    @Slot(str, str)
    def _on_search_error(self, root_path, message):
        _announce(_("Search failed: {error}").format(error=message))

    def refresh(self):
        if self._explorer.mode == ExplorerMode.SEARCH_RESULTS and self._explorer.search_query:
            self.perform_search(self._explorer.search_query)
        else:
            self.relist_contents()
            self.update_path()


    def media_play_pause(self):
        if self._instance is not None:
            state:AVPlaybackState = self._instance.get_playback_state()
            if state == AVPlaybackState.AV_STATE_PLAYING:
                self._instance.pause()
                if self._player_bar:
                    self._player_bar.setState(False)
            else:
                self._instance.play()
                if self._player_bar:
                    self._player_bar.setState(True)

    @Slot(bool)
    def on_playbar_play_pause(self, playing: bool):
        if self._instance is not None:
            if playing:
                self._instance.play()
            else:
                self._instance.pause()

    @Slot()
    def media_backward(self):
        if self._instance is not None:
            self._instance.set_position(self._instance.get_position() - prefs.prefs["offset"]["seek"])

    @Slot()
    def media_forward(self):
        if self._instance is not None:
            self._instance.set_position(self._instance.get_position() + prefs.prefs["offset"]["seek"])

    def media_stop(self):
        if self._instance is not None:
            self._instance.stop()
            if self._player_bar:
                self._player_bar.setState(False)

    @Slot(float)
    def on_playbar_seek(self, position: float):
        if self._instance is not None:
            self._instance.set_position(position)

    def set_item_info(self):
        if self.currentItem() is None: return
        current_item = self.currentItem().text()
        item_info:Optional[PathInfo] = self._explorer.items.get(current_item, None)
        if item_info is None: return
        info = f"{_("Type extension")}: {item_info.info.ext}\r{_("Date modified")}: {item_info.info.modify_date}{f"\r{_("size")}: " + item_info.info.size if item_info.type == PathType.FILE else ""}"

        # Accessible description + tooltip work regardless of view mode.
        self.currentItem().setData(qt.ItemDataRole.AccessibleDescriptionRole, f", {info}")
        self.currentItem().setToolTip(info.replace("\r", "\n"))

        if self.viewMode() == QListWidget.ViewMode.ListMode:
            # The overlay widget only fits properly in List/Details view -
            # Icon view's fixed grid cells can't accommodate it (see
            # set_view_mode), so it's Icon-mode users get the tooltip/
            # accessible description above instead.
            infoText  = QLabel(info,self)
            infoText.adjustSize()
            self.setItemWidget(self.currentItem(),infoText)
            infoText.setMinimumHeight(50)
            infoText.setMinimumWidth(200)
            self.currentItem().setSizeHint(infoText.sizeHint())

    def _execute_callback(self, callback_name:str, param:str = "", with_param :bool = True):
        callback:Optional[Callable[[str], None]] = self._callbacks.get(callback_name, None)
        if callback is not None:
            if with_param:
                callback(param)
            else:
                callback()

    def context_menu(self, event):
        if self._explorer.mode == ExplorerMode.SEARCH_RESULTS:
            if self.currentItem() is None: return
            full_path = self._search_item_paths.get(self.currentItem().text())
            if full_path is None: return
            menu = QMenu()
            menuItem(menu, _("Open"), self.open_file, self)
            menuItem(menu, _("copy path"), self.copy_path, self)
            menuItem(menu, _("Add to playlist"), self.add_to_playlist, self)
            menuItem(menu, _("Add to favorites"), self.add_to_favorites, self)
            menu.addSeparator()
            menuItem(menu, _("Refresh"), self.refresh, self)
            menu.exec()
            return

        if self.currentItem() is None: return
        item = self.currentItem().text()
        item_info:Optional[PathInfo] = self._explorer.items.get(item, None)
        if item_info is None: return  # Guard against None
        menu = QMenu()

        sort_menu = menu.addMenu(_("Sort by"))
        menuItem(sort_menu, _("Name (A\u2013Z)"),       lambda: self._sort("name_asc"),     self)
        menuItem(sort_menu, _("Name (Z\u2013A)"),       lambda: self._sort("name_desc"),    self)
        menuItem(sort_menu, _("Newest first"),           lambda: self._sort("date_newest"),  self)
        menuItem(sort_menu, _("Oldest first"),           lambda: self._sort("date_oldest"),  self)
        menu.addSeparator()

        if item_info.type == PathType.FOLDER:
            menuItem(menu, _("navigate to folder"), self.forward, self)
        elif item_info.type == PathType.FILE:
                menuItem(menu, _("Open"), self.open_file, self)

                menuItem(menu,_("copy path"),self.copy_path,self)

        if item_info.type == PathType.FOLDER:
            menuItem(menu, _("Add to library"), self.add_to_library, self)
            menuItem(menu, _("Create playlist from folder"), self.create_playlist_from_folder, self)
            if app_db.media_db.is_path_cataloged(self._focused_item_path):
                already_action = menu.addAction(_("Already in Database"))
                already_action.setEnabled(False)
            else:
                menuItem(menu, _("Add to Database"), self.add_to_database, self)
        elif item_info.type == PathType.FILE:
                menuItem(menu, _("Add to playlist"), self.add_to_playlist, self)
                menuItem(menu, _("Add to favorites"), self.add_to_favorites, self)

        menu.addSeparator()
        menuItem(menu, _("Refresh"), self.refresh, self)

        menu.exec()


    @Slot(object, object)
    def onItemChange(self, c, p):
        if p is not None:
            p.setData(qt.ItemDataRole.AccessibleDescriptionRole, "")
            self.removeItemWidget(p)

        if c is None: return

        item_name = c.text()

        if self._explorer.mode == ExplorerMode.SEARCH_RESULTS:
            full_path = self._search_item_paths.get(item_name)
            if full_path is None: return
            self._focused_item_path = full_path
            c.setData(qt.ItemDataRole.AccessibleDescriptionRole, f", {full_path}")

            img_path = full_path if os.path.splitext(full_path)[1].lower() in image_extensions else ""
            self._execute_callback("image_preview_callback", img_path)
            self._pending_media_path = full_path
            self._delayed_media_load()
            if self._just_launched: self._just_launched = False
            return

        item_info:Optional[PathInfo] = self._explorer.items.get(item_name, None)

        if item_info is None: return

        if self._explorer.current_path == "drives":
            self._focused_item_path = self._explorer.items[item_name].path
        else:
            self._focused_item_path = os.path.join(self._explorer.current_path, item_name)
        
        self.set_item_info()

        if item_info.type == PathType.FILE and self._focused_item_path is not None:
            img_path = self._focused_item_path if os.path.splitext(self._focused_item_path)[1].lower() in image_extensions else ""
            self._execute_callback("image_preview_callback", img_path)
            self._pending_media_path = self._focused_item_path
            self._delayed_media_load()
        else:
            self._execute_callback("image_preview_callback", "")

        if self._just_launched: self._just_launched = False

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == qt.Key.Key_Backspace:
            self.backward()
        else:
            super().keyPressEvent(event)

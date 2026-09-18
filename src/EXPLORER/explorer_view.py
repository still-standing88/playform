from genericpath import isfile
import os

from typing import Optional, Callable
from PySide6.QtGui import QKeyEvent, QActionGroup, QAction, QFontMetrics, QFont, QColor, QTextOption, QPalette
from PySide6.QtWidgets import (
    QMenu, QListWidget, QListWidgetItem, QLabel, QDialog, QComboBox, QVBoxLayout,
    QDialogButtonBox, QStyledItemDelegate, QStyleOptionViewItem, QApplication, QStyle
)
from PySide6.QtCore import Qt as qt, Slot, QSize, QRect
import utilities.mpv_bootstrap
from media_core.av_play import AVMediaInstance, VideoPlayer, AVPlaybackState
from utilities.formats import image_extensions, formats as media_formats

media_file_extensions = {f".{ext}" for ext in media_formats["audio"] + media_formats["video"]}

from app_config import prefs
from utilities.functions import copyText, open_file_location
from utilities.util_gui import menuItem, contextMenu
from utilities import signal_manager
from utilities.announcement_categories import AnnouncementCategory
from .explorer import Explorer, PathInfo, PathType, ExplorerMode
from .search_worker import SearchWorker
import app_db


def _announce(text):
    signal_manager.announce(text, AnnouncementCategory.EXPLORER)


DETAILS_ROLE = qt.ItemDataRole.UserRole + 1


class FileDetailsDelegate(QStyledItemDelegate):
    """Detail-view painter: file name wrapped over up to two lines with the
    entry's details (type/date/size) on a line below. Replaces the old
    per-item QLabel overlay, whose fixed 200px minimum width clipped long
    names and whose creation-time sizeHint never adapted to window resizes.
    Height is uniform for all rows so scrolling stays smooth; width comes
    from the view's viewport so text re-wraps on resize."""

    MAX_NAME_LINES = 2

    def __init__(self, view):
        super().__init__(view)
        self._view = view
        self._width = 300

    def set_viewport_width(self, width: int):
        self._width = max(120, int(width))

    @staticmethod
    def _wrap_lines(text, metrics: QFontMetrics, width: int, max_lines: int) -> list:
        if not text:
            return []
        words = text.split()
        lines = []
        current = ""
        overflow = False
        for word in words:
            candidate = f"{current} {word}" if current else word
            if not current or metrics.horizontalAdvance(candidate) <= width:
                current = candidate
            else:
                lines.append(current)
                current = word
                if len(lines) == max_lines:
                    overflow = True
                    break
        if not overflow and current:
            lines.append(current)
        if lines and (overflow or metrics.horizontalAdvance(lines[-1]) > width):
            lines[-1] = metrics.elidedText(lines[-1], qt.TextElideMode.ElideRight, width)
        return lines[:max_lines]

    def _row_height(self, name_metrics: QFontMetrics, detail_metrics: QFontMetrics) -> int:
        return self.MAX_NAME_LINES * name_metrics.height() + detail_metrics.height() + 8

    def sizeHint(self, option, index):
        if self._view.viewMode() != QListWidget.ViewMode.ListMode:
            return super().sizeHint(option, index)
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        name_metrics = QFontMetrics(opt.font)
        detail_font = opt.font
        detail_font.setPointSizeF(max(7.0, detail_font.pointSizeF() - 1))
        detail_metrics = QFontMetrics(detail_font)
        return QSize(self._width, self._row_height(name_metrics, detail_metrics))

    def paint(self, painter, option, index):
        if self._view.viewMode() != QListWidget.ViewMode.ListMode:
            super().paint(painter, option, index)
            return

        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        name = opt.text
        details = index.data(DETAILS_ROLE) or ""

        opt.text = ""
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)

        rect = opt.rect.adjusted(6, 2, -6, -2)
        name_metrics = QFontMetrics(opt.font)
        detail_font = QFont(opt.font)
        detail_font.setPointSizeF(max(7.0, detail_font.pointSizeF() - 1))
        detail_metrics = QFontMetrics(detail_font)

        y = rect.top()
        for line in self._wrap_lines(name, name_metrics, rect.width(), self.MAX_NAME_LINES):
            painter.setFont(opt.font)
            painter.setPen(opt.palette.color(QPalette.ColorRole.Text))
            painter.drawText(QRect(rect.left(), y, rect.width(), name_metrics.height()),
                             qt.AlignmentFlag.AlignLeft | qt.AlignmentFlag.AlignVCenter, line)
            y += name_metrics.height()

        if details:
            painter.setFont(detail_font)
            painter.setPen(opt.palette.color(QPalette.ColorRole.PlaceholderText))
            elided = detail_metrics.elidedText(details, qt.TextElideMode.ElideRight, rect.width())
            painter.drawText(QRect(rect.left(), y, rect.width(), detail_metrics.height()),
                             qt.AlignmentFlag.AlignLeft | qt.AlignmentFlag.AlignVCenter, elided)


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

        # Detail view paints name+details through a delegate (no per-item
        # widgets), re-wraps on resize, and rows load in batches so folders
        # with thousands of entries stay responsive.
        self._details_delegate = FileDetailsDelegate(self)
        self.setItemDelegate(self._details_delegate)
        self.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.setUniformItemSizes(False)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll_near_bottom)

        self.BATCH_SIZE = 500
        self._pending_entries: list = []
        self._loading_more = False

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

    def open_in_explorer(self):
        if self._focused_item_path:
            open_file_location(self._focused_item_path)

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
        # Cancels any in-flight search so its results can't land after the
        # navigation and yank the view back into SEARCH_RESULTS mode.
        self._search_worker.cancel()
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
                if os.path.splitext(self._focused_item_path)[1].lower() in image_extensions:
                    self._execute_callback("image_preview_dialog_callback", self._focused_item_path)
                    return
                self.open_file()
            elif os.path.isdir(self._focused_item_path):
                self.forward()

    def relist_contents(self):
        self.clear()
        self._pending_entries = self._build_entries()
        self._load_more_entries()

    def _entry_details(self, item_info: Optional[PathInfo]) -> tuple:
        """(visual details line, accessible description, tooltip) for one
        entry. The visual line is compact ("mp3 · 2026-08-25 · 3.5 MB");
        the accessible description keeps the labeled wording."""
        if item_info is None:
            return "", "", ""
        is_file = item_info.type == PathType.FILE
        ext_label = item_info.info.ext if is_file else _("Folder")
        visual_parts = [ext_label]
        labeled_parts = [f"{_('Type extension')}: {item_info.info.ext}"]
        if item_info.info.modify_date is not None:
            date_str = str(item_info.info.modify_date)
            visual_parts.append(date_str)
            labeled_parts.append(f"{_('Date modified')}: {date_str}")
        if is_file:
            visual_parts.append(item_info.info.size)
            labeled_parts.append(f"{_('size')}: {item_info.info.size}")
        visual = " · ".join(visual_parts)
        labeled = ", ".join(labeled_parts)
        tooltip = f"{item_info.info.name}\n{labeled}"
        return visual, labeled, tooltip

    def _make_list_item(self, label: str, item_info: Optional[PathInfo]) -> QListWidgetItem:
        item = QListWidgetItem(label)
        visual, labeled, tooltip = self._entry_details(item_info)
        item.setData(DETAILS_ROLE, visual)
        # Every row carries its own description so screen readers announce
        # name + details on any focused entry, not just the current one.
        item.setData(qt.ItemDataRole.AccessibleDescriptionRole, labeled)
        item.setToolTip(tooltip)
        return item

    def _build_entries(self) -> list:
        """Full ordered (label, PathInfo) list -- sorting/filtering already
        happened in Explorer before this point; batches preserve its order."""
        entries = []
        if self._explorer.mode == ExplorerMode.SEARCH_RESULTS:
            self._search_item_paths = {}
            root = self._explorer.current_path
            for result in self._explorer.search_results:
                try:
                    label = os.path.relpath(result.path, root)
                except ValueError:
                    label = result.path
                if label in self._search_item_paths:
                    label = result.path
                self._search_item_paths[label] = result.path
                entries.append((label, result))
        else:
            self._search_item_paths = {}
            for name in self._explorer.folders + self._explorer.files:
                entries.append((name, self._explorer.items.get(name)))
        return entries

    def _load_more_entries(self):
        if not self._pending_entries:
            return
        batch = self._pending_entries[:self.BATCH_SIZE]
        del self._pending_entries[:self.BATCH_SIZE]
        for label, item_info in batch:
            self.addItem(self._make_list_item(label, item_info))

    def _on_scroll_near_bottom(self, value: int):
        bar = self.verticalScrollBar()
        if not self._pending_entries:
            return
        if value >= bar.maximum() - 60:
            self._load_more_entries()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._details_delegate.set_viewport_width(self.viewport().width())
        self.doItemsLayout()

    def set_view_mode(self, list_mode: bool):
        self.setViewMode(QListWidget.ViewMode.ListMode if list_mode else QListWidget.ViewMode.IconMode)
        if not list_mode:
            self.setGridSize(QSize(96, 96))
            self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setWrapping(not list_mode)
        self._details_delegate.set_viewport_width(self.viewport().width())
        self.doItemsLayout()

    def perform_search(self, query: str):
        root_path, use_db = self._explorer.begin_search(query, media_db=app_db.media_db)
        _announce(_("Searching..."))
        self._search_worker.start_search(root_path, query, self._explorer.file_extensions, use_db)

    @Slot(str, str, list)
    def _on_search_results(self, root_path, query, paths):
        # A navigation since the search started clears search_query; a
        # result that was already queued on the event loop when the cancel
        # landed is stale and must not yank the view back into search mode.
        if self._explorer.search_query is None:
            return
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
            self._explorer.rescan()
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
            self._player.backward(prefs.prefs["offset"]["seek"])

    @Slot()
    def media_forward(self):
        if self._instance is not None:
            self._player.forward(prefs.prefs["offset"]["seek"])

    def media_stop(self):
        if self._instance is not None:
            self._instance.stop()
            if self._player_bar:
                self._player_bar.setState(False)

    @Slot(float)
    def on_playbar_seek(self, position: float):
        if self._instance is not None:
            self._instance.set_position(int(position * self._instance.get_length()))

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
            if os.path.splitext(full_path or "")[1].lower() in media_file_extensions:
                menuItem(menu, _("Add to Queue"), self.add_selection_to_queue, self)
            menuItem(menu, _("Open in Explorer"), self.open_in_explorer, self)
            menuItem(menu, _("Add to favorites"), self.add_to_favorites, self)
            menu.addSeparator()
            self._add_view_and_filter_submenus(menu)
            menu.addSeparator()
            menuItem(menu, _("Refresh"), self.refresh, self)
            menu.exec()
            return

        if self.currentItem() is None: return
        item = self.currentItem().text()
        item_info:Optional[PathInfo] = self._explorer.items.get(item, None)
        if item_info is None: return  # Guard against None
        menu = QMenu()

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
                if os.path.splitext(self._focused_item_path or "")[1].lower() in media_file_extensions:
                    menuItem(menu, _("Add to Queue"), self.add_selection_to_queue, self)
                menuItem(menu, _("Open in Explorer"), self.open_in_explorer, self)
                menuItem(menu, _("Add to favorites"), self.add_to_favorites, self)

        menu.addSeparator()
        self._add_view_and_filter_submenus(menu)
        menu.addSeparator()
        menuItem(menu, _("Refresh"), self.refresh, self)

        menu.exec()

    def _add_view_and_filter_submenus(self, menu):
        view_menu = menu.addMenu(_("View"))
        view_group = QActionGroup(view_menu)
        view_group.setExclusive(True)
        saved_view_mode = prefs.prefs.get("explorer_view_mode", "list")
        list_action = QAction(_("Detail View"), view_menu)
        list_action.setCheckable(True)
        list_action.setChecked(saved_view_mode != "icon")
        list_action.triggered.connect(lambda: self._set_view_mode(True))
        icon_action = QAction(_("Icon View"), view_menu)
        icon_action.setCheckable(True)
        icon_action.setChecked(saved_view_mode == "icon")
        icon_action.triggered.connect(lambda: self._set_view_mode(False))
        view_group.addAction(list_action)
        view_group.addAction(icon_action)
        view_menu.addAction(list_action)
        view_menu.addAction(icon_action)

        if self._explorer.mode != ExplorerMode.SEARCH_RESULTS:
            sort_menu = menu.addMenu(_("Sort by"))
            menuItem(sort_menu, _("Name (A\u2013Z)"),       lambda: self._sort("name_asc"),     self)
            menuItem(sort_menu, _("Name (Z\u2013A)"),       lambda: self._sort("name_desc"),    self)
            menuItem(sort_menu, _("Newest first"),           lambda: self._sort("date_newest"),  self)
            menuItem(sort_menu, _("Oldest first"),           lambda: self._sort("date_oldest"),  self)

        filter_menu = menu.addMenu(_("Filter"))
        filter_group = QActionGroup(filter_menu)
        filter_group.setExclusive(True)
        current_mode = prefs.prefs.get("explorer_filter_mode", "all")
        for mode_value, label in (
            ("all", _("All Files")),
            ("audio", _("Audio")),
            ("video", _("Video")),
            ("image", _("Images")),
        ):
            action = QAction(label, filter_menu)
            action.setCheckable(True)
            action.setChecked(current_mode == mode_value)
            action.triggered.connect(lambda _c=False, m=mode_value: self._set_filter(m))
            filter_group.addAction(action)
            filter_menu.addAction(action)
        custom_values = prefs.prefs.get("explorer_filter_format", "")
        custom_mode = "custom" if current_mode == "custom" else ""
        custom_action = QAction(_("Custom Format..."), filter_menu)
        custom_action.setCheckable(True)
        custom_action.setChecked(bool(custom_mode))
        custom_action.triggered.connect(self._on_custom_filter)
        filter_group.addAction(custom_action)
        filter_menu.addAction(custom_action)

    def _set_view_mode(self, list_mode: bool):
        self.set_view_mode(list_mode=list_mode)
        prefs.prefs["explorer_view_mode"] = "list" if list_mode else "icon"
        prefs.save()

    def _set_filter(self, mode: str, fmt: str = ""):
        self._explorer.set_filter(mode, fmt)
        prefs.prefs["explorer_filter_mode"] = mode
        prefs.prefs["explorer_filter_format"] = fmt
        prefs.save()
        self.relist_contents()

    def _on_custom_filter(self):
        dialog = FilterFormatDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        fmt = dialog.selected_format()
        if not fmt:
            return
        self._set_filter("custom", fmt)

    def add_selection_to_queue(self):
        paths = self._selected_media_paths()
        if not paths:
            return
        self._execute_callback("queue_callback", paths, with_param=True)

    def _selected_media_paths(self):
        paths = []
        items = self.selectedItems() if self.selectedItems() else (
            [self.currentItem()] if self.currentItem() is not None else [])
        for item in items:
            if item is None:
                continue
            name = item.text()
            if self._explorer.mode == ExplorerMode.SEARCH_RESULTS:
                path = self._search_item_paths.get(name)
            elif name in self._explorer.items:
                path = self._explorer.items[name].path
            else:
                path = os.path.join(self._explorer.current_path, name)
            if path and os.path.isfile(path) and os.path.splitext(path)[1].lower() in media_file_extensions:
                paths.append(path)
        return paths


    @Slot(object, object)
    def onItemChange(self, c, p):
        # Loading more rows when focus approaches the end of the loaded
        # batch keeps keyboard/screen-reader users from ever hitting an
        # artificial "last item" before the real end of the folder.
        if c is not None and self._pending_entries and self.row(c) >= self.count() - 10:
            self._load_more_entries()

        if c is None: return

        item_name = c.text()

        if self._explorer.mode == ExplorerMode.SEARCH_RESULTS:
            full_path = self._search_item_paths.get(item_name)
            if full_path is None: return
            self._focused_item_path = full_path

            img_path = full_path if os.path.splitext(full_path)[1].lower() in image_extensions else ""
            self._execute_callback("image_preview_callback", img_path)
            self._execute_callback("media_preview_callback", full_path)
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

        if item_info.type == PathType.FILE and self._focused_item_path is not None:
            img_path = self._focused_item_path if os.path.splitext(self._focused_item_path)[1].lower() in image_extensions else ""
            self._execute_callback("image_preview_callback", img_path)
            self._execute_callback("media_preview_callback", self._focused_item_path)
            self._pending_media_path = self._focused_item_path
            self._delayed_media_load()
        else:
            self._execute_callback("image_preview_callback", "")
            self._execute_callback("media_preview_callback", "")

        if self._just_launched: self._just_launched = False

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == qt.Key.Key_Backspace:
            self.backward()
        else:
            super().keyPressEvent(event)


class FilterFormatDialog(QDialog):
    """Editable combo box of every format the Explorer supports (image,
    video, and audio extensions) for custom file filtering."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Filter by Format"))
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(_("Format (extension):"), self))

        self.format_combo = QComboBox(self)
        self.format_combo.setEditable(True)
        all_exts = sorted(
            set(media_formats["audio"]) | set(media_formats["video"]) | set(image_extensions)
        )
        for ext in all_exts:
            self.format_combo.addItem(ext)
        current = prefs.prefs.get("explorer_filter_format", "")
        if current:
            self.format_combo.setCurrentText(current)
        layout.addWidget(self.format_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_format(self) -> str:
        return self.format_combo.currentText().strip().lstrip(".").lower()

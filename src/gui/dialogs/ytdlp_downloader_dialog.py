"""yt-dlp Download Manager dialog.

Singleton dialog like the regular Download Manager: a category tree
(YouTube videos / playlists / channels / other), a per-category video
list, a live status label + pause button, and a yt-dlp log pane. The
queue engine runs in the background regardless of visibility; the status
label, list, and log only refresh while the dialog is shown.
"""

import logging
import os
import re
import subprocess
import sys

from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSplitter,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem, QMenu,
    QPlainTextEdit, QMessageBox,
)

from app_constance.styles import TITLE_LABEL_STYLE
from media_core.ytdlp_download.engine import (
    YtDlpDownloadEngine,
    classify_url,
    url_has_playlist_param,
    CATEGORY_YOUTUBE_VIDEOS,
    CATEGORY_YOUTUBE_PLAYLISTS,
    CATEGORY_YOUTUBE_CHANNELS,
    CATEGORY_OTHER,
    CATEGORY_LABELS,
    STATUS_QUEUED,
    STATUS_DOWNLOADING,
    STATUS_PAUSED,
    STATUS_COMPLETED,
    STATUS_FAILED,
)
from .ytdlp_review_dialog import YtDlpReviewDialog, _FlatFetchThread

logger = logging.getLogger(__name__)


class _EngineBridge(QObject):
    queue_changed = Signal()
    entry_updated = Signal(object)
    log_line = Signal(str)


def default_ytdlp_destination() -> str:
    from utilities.functions import get_app_path
    return os.path.join(get_app_path(), "downloads", "yt-dlp")


class YtDlpDownloaderDialog(QDialog):
    dialog_hidden = Signal()
    dialog_closed = Signal()
    play_requested = Signal(str)

    def __init__(self, engine: YtDlpDownloadEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._bridge = _EngineBridge()
        self.setWindowTitle(_("yt-dlp Download Manager"))
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(860, 520)
        self.resize(980, 600)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        self._engine.on_queue_changed = self._bridge.queue_changed.emit
        self._engine.on_entry_updated = self._bridge.entry_updated.emit
        self._engine.on_log_line = self._bridge.log_line.emit
        self._bridge.queue_changed.connect(self._refresh_all)
        self._bridge.entry_updated.connect(self._on_entry_updated)
        self._bridge.log_line.connect(self._append_log)

        self._build_ui()
        self._engine.start()
        self._refresh_categories()
        self._refresh_status()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        title_bar = QHBoxLayout()
        title_label = QLabel(_("yt-dlp Download Manager"))
        title_label.setStyleSheet(TITLE_LABEL_STYLE)
        title_bar.addWidget(title_label)
        title_bar.addStretch()

        minimize_btn = QPushButton(_("Minimize"))
        minimize_btn.setFixedSize(75, 25)
        minimize_btn.setToolTip(_("Hide to status bar"))
        minimize_btn.clicked.connect(self._on_minimize)
        title_bar.addWidget(minimize_btn)

        close_btn = QPushButton(_("Close"))
        close_btn.setFixedSize(60, 25)
        close_btn.clicked.connect(self._on_close_requested)
        title_bar.addWidget(close_btn)
        layout.addLayout(title_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        layout.addWidget(splitter, 1)

        self.category_tree = QTreeWidget(self)
        self.category_tree.setColumnCount(1)
        self.category_tree.setHeaderLabels([_("Categories")])
        self.category_tree.setAccessibleName(_("Download categories"))
        self.category_tree.setAccessibleDescription(
            _("YouTube videos, playlists, channels, and other video downloads. "
              "Playlists and channels expand to their entries; right-click for "
              "pause, resume, remove, and open location.")
        )
        self.category_tree.currentItemChanged.connect(lambda *_c: self._refresh_video_list())
        self.category_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.category_tree.customContextMenuRequested.connect(self._show_category_menu)
        splitter.addWidget(self.category_tree)

        self.video_list = QListWidget(self)
        self.video_list.setAccessibleName(_("Downloads in category"))
        self.video_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.video_list.customContextMenuRequested.connect(self._show_video_menu)
        self.video_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        splitter.addWidget(self.video_list)
        splitter.setSizes([260, 700])

        status_row = QHBoxLayout()
        self.status_label = QLabel(_("Idle"), self)
        self.status_label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.status_label.setAccessibleName(_("Current download status"))
        status_row.addWidget(self.status_label, 1)

        self.pause_button = QPushButton(_("Pause"), self)
        self.pause_button.clicked.connect(self._on_pause_current)
        status_row.addWidget(self.pause_button)
        layout.addLayout(status_row)

        self.log_edit = QPlainTextEdit(self)
        self.log_edit.setReadOnly(True)
        self.log_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.log_edit.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.log_edit.setAccessibleName(_("yt-dlp log"))
        self.log_edit.setMaximumHeight(120)
        layout.addWidget(self.log_edit)

        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self.add_download_button = QPushButton(_("Add Download..."), self)
        self.add_download_button.clicked.connect(self._on_add_download)
        bottom_row.addWidget(self.add_download_button)
        layout.addLayout(bottom_row)

    # ------------------------------------------------------------------
    # Refresh helpers (only while visible)
    # ------------------------------------------------------------------
    def _updates_allowed(self) -> bool:
        return self.isVisible()

    @Slot()
    def _refresh_all(self):
        if not self._updates_allowed():
            return
        self._refresh_categories()
        self._refresh_video_list()
        self._refresh_status()

    @Slot(object)
    def _on_entry_updated(self, entry):
        if not self._updates_allowed():
            return
        self._update_list_item(entry)
        self._refresh_status()

    @Slot(str)
    def _append_log(self, line: str):
        if not self._updates_allowed():
            return
        self.log_edit.appendPlainText(line)

    def _selected_node(self):
        item = self.category_tree.currentItem()
        if item is None:
            return None, None
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        return data.get("category"), data.get("parent")

    def _refresh_categories(self):
        tree = self.category_tree
        previous = self._selected_node()
        tree.blockSignals(True)
        tree.clear()

        for category in (CATEGORY_YOUTUBE_VIDEOS, CATEGORY_YOUTUBE_PLAYLISTS,
                         CATEGORY_YOUTUBE_CHANNELS, CATEGORY_OTHER):
            entries = self._engine.get_entries(category)
            if category in (CATEGORY_YOUTUBE_PLAYLISTS, CATEGORY_YOUTUBE_CHANNELS):
                # The row reads "Playlists (2)" as in two playlists -- not
                # the number of videos inside them (children show that).
                top_count = len({e.parent or e.title for e in entries})
            else:
                top_count = len(entries)
            top = QTreeWidgetItem([f"{_(CATEGORY_LABELS[category])} ({top_count})"])
            top.setData(0, Qt.ItemDataRole.UserRole, {"category": category, "parent": None})
            tree.addTopLevelItem(top)

            if category in (CATEGORY_YOUTUBE_PLAYLISTS, CATEGORY_YOUTUBE_CHANNELS):
                parents = []
                for entry in entries:
                    parent = entry.parent or entry.title
                    if parent not in parents:
                        parents.append(parent)
                for parent in parents:
                    count = sum(1 for e in entries if (e.parent or e.title) == parent)
                    child = QTreeWidgetItem([f"{parent} ({count})"])
                    child.setData(0, Qt.ItemDataRole.UserRole,
                                  {"category": category, "parent": parent})
                    top.addChild(child)

        tree.expandAll()
        restored = None
        previous_category, previous_parent = previous
        if previous_category is not None:
            start = tree.topLevelItem(
                (CATEGORY_YOUTUBE_VIDEOS, CATEGORY_YOUTUBE_PLAYLISTS,
                 CATEGORY_YOUTUBE_CHANNELS, CATEGORY_OTHER).index(previous_category))
            if previous_parent is None:
                restored = start
            elif start is not None:
                for i in range(start.childCount()):
                    child = start.child(i)
                    if (child.data(0, Qt.ItemDataRole.UserRole) or {}).get("parent") == previous_parent:
                        restored = child
                        break
        tree.setCurrentItem(restored if restored is not None else tree.topLevelItem(0))
        tree.blockSignals(False)
        self._refresh_video_list()

    def _refresh_video_list(self):
        category, parent = self._selected_node()
        self.video_list.clear()
        if category is None:
            return
        for entry in self._engine.get_entries(category):
            if parent is not None and (entry.parent or entry.title) != parent:
                continue
            self.video_list.addItem(self._make_list_item(entry))

    @staticmethod
    def _entry_text(entry) -> str:
        status_labels = {
            STATUS_QUEUED: _("Queued"),
            STATUS_DOWNLOADING: _("Downloading"),
            STATUS_PAUSED: _("Paused"),
            STATUS_COMPLETED: _("Completed"),
            STATUS_FAILED: _("Failed"),
        }
        text = f"{entry.title} — {status_labels.get(entry.status, entry.status)}"
        if entry.status == STATUS_DOWNLOADING:
            details = f"{entry.progress_pct:.1f}%"
            if entry.speed:
                details += f" · {entry.speed}"
            if entry.eta:
                details += f" · ETA {entry.eta}"
            text = f"{text} ({details})"
        elif entry.error:
            text = f"{text} ({entry.error})"
        return text

    def _make_list_item(self, entry) -> QListWidgetItem:
        item = QListWidgetItem(self._entry_text(entry))
        item.setData(Qt.ItemDataRole.UserRole, entry.id)
        item.setToolTip(entry.url)
        item.setData(Qt.ItemDataRole.AccessibleDescriptionRole,
                     f"{_('status')}: {entry.status}, {entry.progress_pct:.0f}%")
        return item

    def _update_list_item(self, entry):
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == entry.id:
                item.setText(self._entry_text(entry))
                item.setData(Qt.ItemDataRole.AccessibleDescriptionRole,
                             f"{_('status')}: {entry.status}, {entry.progress_pct:.0f}%")
                return

    def _refresh_status(self):
        entries = self._engine.get_entries()
        current = next((e for e in entries if e.status == STATUS_DOWNLOADING), None)

        counts = {}
        for entry in entries:
            counts[entry.status] = counts.get(entry.status, 0) + 1
        summary_parts = []
        if counts.get(STATUS_QUEUED):
            summary_parts.append(_("{count} queued").format(count=counts[STATUS_QUEUED]))
        if counts.get(STATUS_PAUSED):
            summary_parts.append(_("{count} paused").format(count=counts[STATUS_PAUSED]))
        if counts.get(STATUS_COMPLETED):
            summary_parts.append(_("{count} completed").format(count=counts[STATUS_COMPLETED]))
        if counts.get(STATUS_FAILED):
            summary_parts.append(_("{count} failed").format(count=counts[STATUS_FAILED]))
        summary = " · ".join(summary_parts)

        if current is not None:
            text = _("Downloading {title} — {pct}% at {speed}, ETA {eta}").format(
                title=current.title, pct=f"{current.progress_pct:.1f}",
                speed=current.speed or "—", eta=current.eta or "—")
            if summary:
                text = f"{text} ({summary})"
        elif summary:
            text = _("No active download — {summary}").format(summary=summary)
        else:
            text = _("No downloads yet. Use Add Download to queue one.")
        self.status_label.setText(text)
        self.pause_button.setEnabled(current is not None)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _entries_under_node(self) -> list:
        category, parent = self._selected_node()
        if category is None:
            return []
        entries = self._engine.get_entries(category)
        if parent is not None:
            entries = [e for e in entries if (e.parent or e.title) == parent]
        return entries

    def _show_category_menu(self, position):
        item = self.category_tree.currentItem()
        if item is None:
            return
        # The menu is self-aware: top-level category rows (Videos, Other,
        # and the Playlists/Channels roots) offer nothing -- actions only
        # make sense on a concrete playlist/channel entry under them.
        if item.parent() is None:
            return
        entries = self._entries_under_node()
        menu = QMenu(self)
        any_downloading = any(e.status == STATUS_DOWNLOADING for e in entries)
        any_paused = any(e.status == STATUS_PAUSED for e in entries)

        pause_action = menu.addAction(_("Pause"))
        pause_action.setEnabled(any_downloading)
        pause_action.triggered.connect(
            lambda: [self._engine.pause(e.id) for e in entries])

        resume_action = menu.addAction(_("Resume"))
        resume_action.setEnabled(any_paused)
        resume_action.triggered.connect(
            lambda: [self._engine.resume(e.id) for e in entries])

        remove_action = menu.addAction(_("Remove"))
        remove_action.setEnabled(bool(entries))
        remove_action.triggered.connect(
            lambda: [self._engine.remove(e.id) for e in entries])

        menu.addSeparator()
        open_action = menu.addAction(_("Open Location"))
        open_action.setEnabled(bool(entries))
        open_action.triggered.connect(self._open_selected_location)
        menu.exec(self.category_tree.viewport().mapToGlobal(position))

    def _show_video_menu(self, position):
        item = self.video_list.currentItem()
        if item is None:
            return
        entry = self._engine.get_entry(item.data(Qt.ItemDataRole.UserRole))
        if entry is None:
            return
        menu = QMenu(self)

        file_exists = bool(entry.filepath) and os.path.isfile(entry.filepath)
        play_action = menu.addAction(_("Play"))
        play_action.setEnabled(entry.status == STATUS_COMPLETED and file_exists)
        play_action.triggered.connect(lambda: self.play_requested.emit(entry.filepath))

        if entry.status == STATUS_DOWNLOADING:
            pause_resume = menu.addAction(_("Pause"))
            pause_resume.triggered.connect(lambda: self._engine.pause(entry.id))
        elif entry.status in (STATUS_PAUSED, STATUS_FAILED):
            pause_resume = menu.addAction(_("Resume"))
            pause_resume.triggered.connect(lambda: self._engine.resume(entry.id))
        else:
            pause_resume = None

        remove_action = menu.addAction(_("Remove"))
        remove_action.triggered.connect(lambda: self._engine.remove(entry.id))

        menu.addSeparator()
        open_action = menu.addAction(_("Open Location"))
        open_action.setEnabled(bool(entry.destination))
        open_action.triggered.connect(lambda: self._open_location(entry.destination))
        menu.exec(self.video_list.viewport().mapToGlobal(position))

    def _open_selected_location(self):
        entries = self._entries_under_node()
        if entries:
            self._open_location(entries[0].destination)

    @staticmethod
    def _open_location(path: str):
        if not path or not os.path.isdir(path):
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)  # noqa: S606 - user-requested folder open
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except OSError as exc:
            logger.warning("Could not open location %s: %s", path, exc)

    def _on_pause_current(self):
        for entry in self._engine.get_entries():
            if entry.status == STATUS_DOWNLOADING:
                self._engine.pause(entry.id)
                return

    def _on_item_double_clicked(self, item):
        entry = self._engine.get_entry(item.data(Qt.ItemDataRole.UserRole))
        if entry is not None and entry.status == STATUS_COMPLETED \
                and entry.filepath and os.path.isfile(entry.filepath):
            self.play_requested.emit(entry.filepath)

    # ------------------------------------------------------------------
    # Add-download flow with URL detection
    # ------------------------------------------------------------------
    def _on_add_download(self):
        from .ytdlp_add_dialog import YtDlpAddDialog
        dialog = YtDlpAddDialog(default_ytdlp_destination(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        url, destination = dialog.values()
        self.handle_url(url, destination)

    def handle_url(self, url: str, destination: str = ""):
        """Route one URL through detection: single video, playlist ask,
        playlist review, channel kind ask, or plain 'other' enqueue."""
        destination = destination or default_ytdlp_destination()
        category = classify_url(url)

        if category == CATEGORY_YOUTUBE_VIDEOS:
            if url_has_playlist_param(url):
                reply = QMessageBox.question(
                    self, _("Video or Playlist?"),
                    _("This link points to a video inside a playlist.\n\n"
                      "Download just this video, or the whole playlist?"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    | QMessageBox.StandardButton.Cancel)
                if reply == QMessageBox.StandardButton.Cancel:
                    return
                if reply == QMessageBox.StandardButton.Yes:
                    self._enqueue_single(url, destination, CATEGORY_YOUTUBE_VIDEOS)
                    return
                self._open_review(url, "playlist", destination)
                return
            self._enqueue_single(url, destination, CATEGORY_YOUTUBE_VIDEOS)
        elif category == CATEGORY_YOUTUBE_PLAYLISTS:
            self._open_review(url, "playlist", destination)
        elif category == CATEGORY_YOUTUBE_CHANNELS:
            self._ask_channel_kind(url, destination)
        else:
            self._enqueue_single(url, destination, CATEGORY_OTHER)

    @staticmethod
    def _derive_parent_name(url: str, kind: str) -> str:
        """Fallback name when yt-dlp's listing carried no playlist/channel
        title -- a readable label derived from the URL, never the raw URL."""
        if kind == "playlist":
            match = re.search(r"[?&]list=([^&]+)", url)
            if match:
                return _("Playlist {id}").format(id=match.group(1))
            return url
        tail = url.rstrip("/").rsplit("/", 1)[-1]
        return tail.lstrip("@") or url

    def _ask_channel_kind(self, url: str, destination: str):
        box = QMessageBox(self)
        box.setWindowTitle(_("Channel Downloads"))
        box.setText(_("Download this channel's videos, its shorts, or both?"))
        videos_button = box.addButton(_("Videos"), QMessageBox.ButtonRole.AcceptRole)
        shorts_button = box.addButton(_("Shorts"), QMessageBox.ButtonRole.AcceptRole)
        both_button = box.addButton(_("Both"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is videos_button:
            self._open_review(url, "channel_videos", destination)
        elif clicked is shorts_button:
            self._open_review(url, "channel_shorts", destination)
        elif clicked is both_button:
            self._open_review(url, "channel_all", destination)

    def _open_review(self, url: str, kind: str, destination: str):
        dialog = YtDlpReviewDialog(url, kind, self)
        dialog.set_default_location(destination)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        options = dialog.options()

        categories = {
            "playlist": CATEGORY_YOUTUBE_PLAYLISTS,
            "channel_videos": CATEGORY_YOUTUBE_CHANNELS,
            "channel_shorts": CATEGORY_YOUTUBE_CHANNELS,
            "channel_all": CATEGORY_YOUTUBE_CHANNELS,
        }
        category = categories.get(kind, CATEGORY_OTHER)
        parent_name = dialog.source_title() or self._derive_parent_name(url, kind)

        added_any = False
        for entry_data in dialog.selected_entries():
            entry = self._engine.add_entry(
                url=entry_data["url"], title=entry_data["title"],
                category=category, destination=options["destination"],
                parent=parent_name, format_mode=options["format_mode"])
            added_any = True
            if not options["start_now"]:
                self._engine.pause(entry.id)

        if added_any:
            self.show_dialog()
            self._announce_queue_added(len(dialog.selected_entries()))

    def _announce_queue_added(self, count: int):
        from utilities import signal_manager
        from utilities.announcement_categories import AnnouncementCategory
        signal_manager.announce(
            _("Queued {count} download(s)").format(count=count),
            AnnouncementCategory.DOWNLOADS)

    def _enqueue_single(self, url: str, destination: str, category: str):
        entry = self._engine.add_entry(url=url, title=url, category=category,
                                       destination=destination)
        thread = _FlatFetchThread([url], self)
        entry_id = entry.id

        def _on_found(found):
            if found.get("title"):
                self._engine.set_title(entry_id, found["title"])

        thread.entry_found.connect(_on_found)
        thread.finished_ok.connect(thread.deleteLater)
        thread.failed.connect(thread.deleteLater)
        thread.start()

        self.show_dialog()
        self._announce_queue_added(1)

    # ------------------------------------------------------------------
    # Chrome
    # ------------------------------------------------------------------
    @Slot()
    def show_dialog(self):
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.show()
        self.raise_()
        self.activateWindow()
        self._refresh_all()

    @Slot()
    def _on_minimize(self):
        self.hide()
        self.dialog_hidden.emit()

    @Slot()
    def _on_close_requested(self):
        running = any(e.status == STATUS_DOWNLOADING for e in self._engine.get_entries())
        if running:
            reply = QMessageBox.question(
                self, _("Downloads Running"),
                _("A download is currently running. Minimize instead of closing?\n\n"
                  "Closing keeps the queue; it resumes next time you open this window."),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
            self._on_minimize()
            return
        self.accept()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.dialog_closed.emit()
        event.accept()

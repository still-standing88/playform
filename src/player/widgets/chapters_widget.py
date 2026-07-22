from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal, QItemSelectionModel
from PySide6.QtGui import QColor

from gui_controls.player_key_event_filter import KeyEventFilter
from app_constance.styles import SUBTITLES_LIST_STYLE


class ChaptersWidget(QWidget):
    chapterActivated = Signal(float)  # start time in seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self._key_event_filter = KeyEventFilter(self)

        self.setup_ui()
        self.connect_signals()
        self._install_event_filter()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.chapters_list = QListWidget(self)
        self.chapters_list.setAccessibleName(_("Chapters display"))
        self.chapters_list.setAccessibleDescription(_("Chapters for the current media"))
        self.chapters_list.setAlternatingRowColors(True)
        self.chapters_list.setMaximumHeight(150)
        self.chapters_list.setStyleSheet(SUBTITLES_LIST_STYLE)

        layout.addWidget(self.chapters_list)

    def connect_signals(self):
        self.chapters_list.itemClicked.connect(self._on_item_activated)
        self.chapters_list.itemActivated.connect(self._on_item_activated)

    def _on_item_activated(self, item: QListWidgetItem):
        start = item.data(Qt.ItemDataRole.UserRole)
        if start is not None:
            self.chapterActivated.emit(float(start))

    def load_chapters(self, chapters: list[dict]):
        self.chapters_list.clear()
        for chapter in chapters:
            title = chapter.get("title") or _("Chapter")
            start = chapter.get("start", 0.0)
            item = QListWidgetItem(f"{self._format_time(start)}  {title}")
            item.setData(Qt.ItemDataRole.UserRole, start)
            self.chapters_list.addItem(item)

    def clear_chapters(self):
        self.chapters_list.clear()
        self._highlighted_idx = -1

    def highlight_chapter_at_time(self, timestamp_usec: int):
        count = self.chapters_list.count()
        if count == 0:
            return

        timestamp_sec = timestamp_usec / 1_000_000

        active_idx = -1
        for i in range(count):
            start = self.chapters_list.item(i).data(Qt.ItemDataRole.UserRole)
            if start is not None and start <= timestamp_sec:
                active_idx = i
            else:
                break

        prev_idx = getattr(self, "_highlighted_idx", -1)
        if active_idx == prev_idx:
            return

        if prev_idx >= 0:
            self.chapters_list.item(prev_idx).setBackground(QColor(0, 0, 0, 0))

        if active_idx >= 0:
            item = self.chapters_list.item(active_idx)
            item.setBackground(QColor(255, 255, 0, 80))
            self.chapters_list.scrollToItem(item)
            self.chapters_list.selectionModel().setCurrentIndex(
                self.chapters_list.model().index(active_idx, 0),
                QItemSelectionModel.SelectionFlag.NoUpdate,
            )

        self._highlighted_idx = active_idx

    @staticmethod
    def _format_time(seconds: float) -> str:
        total = int(seconds)
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h:d}:{m:02d}:{s:02d}"
        return f"{m:d}:{s:02d}"

    def _install_event_filter(self):
        self._key_event_filter.install_on_widgets([self.chapters_list])

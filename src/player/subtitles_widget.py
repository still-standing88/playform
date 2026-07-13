from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QComboBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from gui_controls.player_key_event_filter import KeyEventFilter
from app_constance.styles import SUBTITLES_LIST_STYLE


class SubtitlesWidget(QWidget):
    languageSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._key_event_filter = KeyEventFilter(self)
        self._all_subtitles_loaded = False  # Track if we've loaded all subtitles

        self.setup_ui()
        self.connect_signals()
        self._install_event_filter()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.language_combo = QComboBox(self)
        self.language_combo.setAccessibleName(_("Subtitle language"))
        self.language_combo.setVisible(False)
        layout.addWidget(self.language_combo)

        self.subtitles_list = QListWidget(self)
        self.subtitles_list.setAccessibleName(_("Subtitles display"))
        self.subtitles_list.setAccessibleDescription(_("Current video subtitles"))
        self.subtitles_list.setAlternatingRowColors(True)
        self.subtitles_list.setMaximumHeight(150)

        self.subtitles_list.setStyleSheet(SUBTITLES_LIST_STYLE)

        layout.addWidget(self.subtitles_list)

    def connect_signals(self):
        self.language_combo.currentTextChanged.connect(self._on_language_changed)

    def _on_language_changed(self, language: str):
        if language:
            self.languageSelected.emit(language)

    def set_available_languages(self, languages: list[str], current: str | None = None):
        self.language_combo.blockSignals(True)
        self.language_combo.clear()
        self.language_combo.addItems(languages)
        if current and current in languages:
            self.language_combo.setCurrentText(current)
        self.language_combo.blockSignals(False)
        self.language_combo.setVisible(len(languages) > 1)

    def add_subtitle_line(self, text, timestamp=None):
        item = QListWidgetItem(text)
        if timestamp:
            item.setData(Qt.ItemDataRole.UserRole, timestamp)

        self.subtitles_list.addItem(item)

    def clear_subtitles(self):
        self.subtitles_list.clear()
        self._all_subtitles_loaded = False

    def load_all_subtitles(self, subtitle_manager):
        """Load all subtitles from subtitle manager"""
        self.subtitles_list.clear()
        for sub in subtitle_manager.subtitles:
            item = QListWidgetItem(sub.text)
            item.setData(Qt.ItemDataRole.UserRole, sub.start)  # Store start time
            self.subtitles_list.addItem(item)
        self._all_subtitles_loaded = True

    def highlight_subtitle_at_time(self, timestamp_usec):
        if not self._all_subtitles_loaded:
            return

        count = self.subtitles_list.count()
        if count == 0:
            return

        active_idx = -1
        for i in range(count):
            item_timestamp = self.subtitles_list.item(i).data(Qt.ItemDataRole.UserRole)
            if item_timestamp is not None and item_timestamp <= timestamp_usec:
                active_idx = i
            else:
                break

        prev_idx = getattr(self, "_highlighted_idx", -1)
        if active_idx == prev_idx:
            return

        if prev_idx >= 0:
            self.subtitles_list.item(prev_idx).setBackground(QColor(0, 0, 0, 0))

        if active_idx >= 0:
            item = self.subtitles_list.item(active_idx)
            item.setBackground(QColor(255, 255, 0, 80))
            self.subtitles_list.scrollToItem(item)

        self._highlighted_idx = active_idx

    def _install_event_filter(self):
        self._key_event_filter.install_on_widgets([self.subtitles_list, self.language_combo])

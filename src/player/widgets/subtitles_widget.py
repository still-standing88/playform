from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QComboBox, QDoubleSpinBox, QCheckBox,
                               QPushButton)
from PySide6.QtCore import Qt, Signal, QItemSelectionModel
from PySide6.QtGui import QColor

from gui_controls.player_key_event_filter import KeyEventFilter
from app_constance.styles import subtitles_list_style

# Distinguishes "an mpv track id was chosen" from a yt-dlp language string,
# since one combo carries both kinds of entry.
TRACK_ID_ROLE = Qt.ItemDataRole.UserRole


class SubtitlesWidget(QWidget):
    languageSelected = Signal(str)
    trackSelected = Signal(object)  # mpv track id, or None for "off"
    delayChanged = Signal(float)
    visibilityToggled = Signal(bool)
    seekRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._key_event_filter = KeyEventFilter(self)
        self._all_subtitles_loaded = False  # Track if we've loaded all subtitles
        self._building = False

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

        self.subtitles_list.setStyleSheet(subtitles_list_style())

        layout.addWidget(self.subtitles_list)

        seek_row = QHBoxLayout()
        self.prev_line_button = QPushButton(_("Previous Line"), self)
        self.prev_line_button.setToolTip(_("Seek playback to the previous subtitle line"))
        self.next_line_button = QPushButton(_("Next Line"), self)
        self.next_line_button.setToolTip(_("Seek playback to the next subtitle line"))
        seek_row.addWidget(self.prev_line_button)
        seek_row.addWidget(self.next_line_button)
        layout.addLayout(seek_row)

        delay_row = QHBoxLayout()
        delay_label = QLabel(_("Subtitle Delay (seconds)"), self)
        delay_row.addWidget(delay_label)
        self.delay_spin = QDoubleSpinBox(self)
        self.delay_spin.setRange(-60.0, 60.0)
        self.delay_spin.setDecimals(2)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.setValue(0.0)
        self.delay_spin.setAccessibleName(_("Subtitle Delay (seconds)"))
        delay_label.setBuddy(self.delay_spin)
        delay_row.addWidget(self.delay_spin, 1)
        layout.addLayout(delay_row)

        self.visibility_check = QCheckBox(_("Show subtitles on video"), self)
        self.visibility_check.setToolTip(
            _("Controls MPV's own on-video rendering; the list above is unaffected")
        )
        layout.addWidget(self.visibility_check)

    def apply_theme_styles(self):
        self.subtitles_list.setStyleSheet(subtitles_list_style())

    def connect_signals(self):
        self.language_combo.currentIndexChanged.connect(self._on_selection_changed)
        self.delay_spin.valueChanged.connect(self._on_delay_changed)
        self.visibility_check.toggled.connect(self._on_visibility_toggled)
        self.prev_line_button.clicked.connect(lambda: self.seekRequested.emit(-1))
        self.next_line_button.clicked.connect(lambda: self.seekRequested.emit(1))

    def _on_selection_changed(self, index: int):
        if self._building or index < 0:
            return
        data = self.language_combo.itemData(index, TRACK_ID_ROLE)
        if data is not None:
            # An embedded mpv track: -1 is the sentinel for the "Off" entry,
            # since None can't be told apart from "no data on this item".
            self.trackSelected.emit(None if data == -1 else data)
            return
        language = self.language_combo.itemText(index)
        if language:
            self.languageSelected.emit(language)

    def _on_delay_changed(self, value: float):
        if self._building:
            return
        self.delayChanged.emit(float(value))

    def _on_visibility_toggled(self, checked: bool):
        if self._building:
            return
        self.visibilityToggled.emit(checked)

    def set_available_languages(self, languages: list[str], current: str | None = None):
        self._building = True
        try:
            self.language_combo.clear()
            self.language_combo.addItems(languages)
            if current and current in languages:
                self.language_combo.setCurrentText(current)
        finally:
            self._building = False
        self.language_combo.setVisible(len(languages) > 1)
        self._update_seek_enabled(False)

    def set_available_tracks(self, tracks: list[dict]):
        """Embedded subtitle tracks from mpv (see
        MPVVideoPlayer.get_subtitle_tracks). Shown in the same combo as
        yt-dlp languages -- only one of the two ever applies to a given
        track, and the item's data tells them apart."""
        self._building = True
        try:
            self.language_combo.clear()
            self.language_combo.addItem(_("Off"), -1)
            self.language_combo.setItemData(0, -1, TRACK_ID_ROLE)
            selected_row = 0
            for track in tracks:
                self.language_combo.addItem(self._track_label(track), track.get("id"))
                row = self.language_combo.count() - 1
                self.language_combo.setItemData(row, track.get("id"), TRACK_ID_ROLE)
                if track.get("selected"):
                    selected_row = row
            self.language_combo.setCurrentIndex(selected_row)
        finally:
            self._building = False
        self.language_combo.setVisible(bool(tracks))
        self._update_seek_enabled(bool(tracks))

    @staticmethod
    def _track_label(track: dict) -> str:
        parts = [track.get("title") or track.get("lang") or _("Track {id}").format(id=track.get("id"))]
        if track.get("title") and track.get("lang"):
            parts.append(f"({track['lang']})")
        if track.get("forced"):
            parts.append(_("[forced]"))
        return " ".join(parts)

    def _update_seek_enabled(self, enabled: bool):
        self.prev_line_button.setEnabled(enabled)
        self.next_line_button.setEnabled(enabled)

    def sync_mpv_state(self, delay: float, visible: bool):
        self._building = True
        try:
            self.delay_spin.setValue(float(delay))
            self.visibility_check.setChecked(bool(visible))
        finally:
            self._building = False

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
            self.subtitles_list.selectionModel().setCurrentIndex(
                self.subtitles_list.model().index(active_idx, 0),
                QItemSelectionModel.SelectionFlag.NoUpdate,
            )

        self._highlighted_idx = active_idx

    def _install_event_filter(self):
        self._key_event_filter.install_on_widgets([
            self.subtitles_list, self.language_combo, self.delay_spin,
            self.visibility_check, self.prev_line_button, self.next_line_button,
        ])

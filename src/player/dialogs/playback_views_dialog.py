import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QDialogButtonBox, QPushButton)


class PlaybackQueueDialog(QDialog):
    queueRemoveRequested = Signal(int)
    queueClearRequested = Signal()
    queueJumpRequested = Signal(int)

    def __init__(self, player_widget, parent=None):
        super().__init__(parent or player_widget)
        self.player_widget = player_widget
        self.setWindowTitle(_("Playback Queue"))
        self.setModal(False)
        self.resize(420, 380)
        self._syncing = False

        layout = QVBoxLayout(self)

        self.info_label = QLabel(self)
        self.info_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        layout.addWidget(self.info_label)

        self.queue_list = QListWidget(self)
        self.queue_list.setAccessibleName(_("Queued tracks list"))
        self.queue_list.itemActivated.connect(self._on_item_activated)
        layout.addWidget(self.queue_list)

        buttons = QHBoxLayout()
        self.remove_btn = QPushButton(_("Remove Selected"))
        self.remove_btn.clicked.connect(self._on_remove_clicked)
        buttons.addWidget(self.remove_btn)
        self.clear_btn = QPushButton(_("Clear Queue"))
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        buttons.addWidget(self.clear_btn)
        buttons.addStretch(1)
        close_btn = QPushButton(_("Close"))
        close_btn.clicked.connect(self.close)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        self.refresh_queue()

    def refresh_queue(self):
        if self._syncing:
            return
        self._syncing = True
        try:
            self.queue_list.clear()
            queue = self.player_widget.get_queue() if self.player_widget else []
            active_index = -1
            if self.player_widget and self.player_widget.player.is_queue_track_active():
                current = getattr(self.player_widget.player.primary_instance, "file_path", None) if self.player_widget.player.primary_instance else None
                if current:
                    norm = os.path.normpath(current)
                    for i, loc in enumerate(queue):
                        if os.path.normpath(loc) == norm:
                            active_index = i
                            break
            for i, location in enumerate(queue):
                item = QListWidgetItem(f"{i + 1}. {os.path.basename(location)}")
                item.setToolTip(location)
                if i == active_index:
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)
                self.queue_list.addItem(item)
            count = len(queue)
            if count > 0:
                self.info_label.setText(_("{count} track(s) queued").format(count=count))
            else:
                self.info_label.setText(_("Queue is empty"))
        finally:
            self._syncing = False

    def _on_remove_clicked(self):
        row = self.queue_list.currentRow()
        if row >= 0:
            self.queueRemoveRequested.emit(row)

    def _on_clear_clicked(self):
        self.queueClearRequested.emit()

    def _on_item_activated(self, item):
        row = self.queue_list.row(item)
        if row >= 0:
            self.queueJumpRequested.emit(row)


class PlaylistViewDialog(QDialog):
    def __init__(self, player_widget, parent=None):
        super().__init__(parent or player_widget)
        self.player_widget = player_widget
        self.setWindowTitle(_("Playlist"))
        self.setModal(False)
        self.resize(480, 420)

        layout = QVBoxLayout(self)

        self.now_playing_label = QLabel(self)
        self.now_playing_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.now_playing_label.setWordWrap(True)
        layout.addWidget(self.now_playing_label)

        self.tracks_list = QListWidget(self)
        self.tracks_list.setAccessibleName(_("Current playlist tracks list"))
        self.tracks_list.itemActivated.connect(self._on_track_activated)
        layout.addWidget(self.tracks_list)

        close_btn = QPushButton(_("Close"))
        close_btn.clicked.connect(self.close)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        self.refresh_playlist()

    def refresh_playlist(self):
        self.tracks_list.clear()
        playlist = self.player_widget.player.current_playlist if self.player_widget else None
        current_index = self.player_widget.player.get_current_track_index() if self.player_widget else -1
        count = len(playlist.entries) if playlist else 0

        bold_font = QFont()
        bold_font.setBold(True)
        normal_font = QFont()

        for index, entry in enumerate(playlist.entries) if playlist else []:
            title = entry.title or os.path.basename(entry.location)
            item = QListWidgetItem(f"{index + 1}. {title}")
            item.setToolTip(entry.location)
            if index == current_index:
                item.setFont(bold_font)
            else:
                item.setFont(normal_font)
            self.tracks_list.addItem(item)

        playing_title = None
        if playlist and 0 <= current_index < count:
            entry = playlist.get_entry(current_index)
            playing_title = entry.title or os.path.basename(entry.location)

        if playing_title:
            if count > 1:
                text = _("Now playing: {title} ({position}/{total})").format(
                    title=playing_title, position=current_index + 1, total=count)
            else:
                text = _("Now playing: {title}").format(title=playing_title)
        else:
            text = _("No track playing")
        self.now_playing_label.setText(text)

    def _on_track_activated(self, item):
        index = self.tracks_list.row(item)
        if self.player_widget and self.player_widget.player.current_playlist:
            self.player_widget.player.jump_to_track(index)

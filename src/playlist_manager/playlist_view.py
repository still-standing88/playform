import os

from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import QAbstractItemView, QFileDialog, QMenu, QMessageBox, QVBoxLayout, QWidget

import utilities.mpv_bootstrap
from media_core.av_play import Playlist, PlaylistEntry
from gui_controls.list_ctrl import ListCtrl
from utilities import signal_manager


class PlaylistListCtrl(ListCtrl):
    order_changed = Signal()
    delete_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_multi_selection()
        self.set_simple_style(True)
        self.set_cell_padding(10, 6)
        self.setAccessibleName(_("Playlist tracks list"))
        self.setToolTip(
            _("Reorder tracks by dragging them or pressing Shift+Up / Shift+Down. Right-click for more options.")
        )
        self._list_view.setToolTip(self.toolTip())
        self._header.column_clicked.disconnect(self._on_column_clicked)
        self._list_view.setDragEnabled(True)
        self._list_view.setAcceptDrops(True)
        self._list_view.setDropIndicatorShown(True)
        self._list_view.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list_view.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list_view.viewport().setAcceptDrops(True)

    def eventFilter(self, obj, event):
        if obj == self._list_view.viewport():
            if event.type() == event.Type.KeyPress:
                if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                    if event.key() == Qt.Key.Key_Up and self._move_with_focus_fallback(-1):
                        return True
                    if event.key() == Qt.Key.Key_Down and self._move_with_focus_fallback(1):
                        return True
                if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                    self.delete_requested.emit()
                    return True
            elif event.type() == event.Type.Drop:
                QTimer.singleShot(0, self.order_changed.emit)

        return super().eventFilter(obj, event)

    def _move_with_focus_fallback(self, step: int) -> bool:
        if not self.get_selected_items():
            focused_row = self.get_current_item()
            if focused_row >= 0:
                self.select_item(focused_row, True)
        return self.move_selected_items(step)


class PlaylistView(QWidget):
    play_playlist_signal = Signal(Playlist)

    def __init__(self, parent=None, play_callback=None, playlist_changed_callback=None):
        super().__init__(parent)
        self.play_callback = play_callback
        self.playlist_changed_callback = playlist_changed_callback
        self.current_playlist = None
        self._now_playing_index: Optional[int] = None
        self.setup_ui()
        self.setup_context_menu()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)

        self.list_ctrl = PlaylistListCtrl(self)
        self.list_ctrl.item_clicked.connect(self.on_row_activated)
        self.list_ctrl.item_activated.connect(self.on_row_activated)
        self.list_ctrl.items_reordered.connect(self.persist_current_order)
        self.list_ctrl.order_changed.connect(self.persist_current_order)
        self.list_ctrl.delete_requested.connect(self.delete_selected)
        self.list_ctrl._list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_ctrl._list_view.customContextMenuRequested.connect(self.show_context_menu)
        self._setup_columns()
        layout.addWidget(self.list_ctrl)

    def _setup_columns(self):
        self.list_ctrl.clear_all()
        self.list_ctrl.append_column(_("#"), 40)
        self.list_ctrl.append_column(_("File Name"), 260)
        self.list_ctrl.append_column(_("Title"), 240)
        self.list_ctrl.append_column(_("Artist"), 180)
        self.list_ctrl.append_column(_("Album"), 180)

    def setup_context_menu(self):
        self.context_menu = QMenu(self)

        add_tracks_action = QAction(_("Add Tracks"), self)
        add_tracks_action.triggered.connect(self.add_tracks)
        self.context_menu.addAction(add_tracks_action)

        self.move_up_action = QAction(_("Move Up"), self)
        self.move_up_action.triggered.connect(lambda: self.move_selected_rows(-1))
        self.context_menu.addAction(self.move_up_action)

        self.move_down_action = QAction(_("Move Down"), self)
        self.move_down_action.triggered.connect(lambda: self.move_selected_rows(1))
        self.context_menu.addAction(self.move_down_action)

        self.sort_menu = self.context_menu.addMenu(_("Sort"))
        sort_options = (
            (_("File Name"), "location"),
            (_("Title"), "title"),
            (_("Artist"), "artist"),
            (_("Album"), "album"),
        )
        for label, key in sort_options:
            ascending_action = QAction(label, self)
            ascending_action.triggered.connect(
                lambda checked=False, sort_key=key: self.sort_tracks(sort_key, False)
            )
            self.sort_menu.addAction(ascending_action)

            descending_action = QAction(_("{label} (Descending)").format(label=label), self)
            descending_action.triggered.connect(
                lambda checked=False, sort_key=key: self.sort_tracks(sort_key, True)
            )
            self.sort_menu.addAction(descending_action)

        self.context_menu.addSeparator()

        self.delete_action = QAction(_("Delete Selected"), self)
        self.delete_action.triggered.connect(self.delete_selected)
        self.context_menu.addAction(self.delete_action)

        self.clear_action = QAction(_("Clear Tracks"), self)
        self.clear_action.triggered.connect(self.clear_tracks)
        self.context_menu.addAction(self.clear_action)

    @Slot(object)
    def show_context_menu(self, position):
        has_entries = self.current_playlist is not None and bool(self.current_playlist.entries)
        has_focused_item = self._get_focused_row() >= 0
        target_rows = self._selected_playlist_indexes()
        has_target_rows = bool(target_rows)
        last_row = self.list_ctrl.get_item_count() - 1

        can_move_up = has_target_rows and min(target_rows) > 0
        can_move_down = has_target_rows and max(target_rows) < last_row

        self.move_up_action.setEnabled(can_move_up)
        self.move_down_action.setEnabled(can_move_down)
        self.delete_action.setEnabled(has_focused_item or has_target_rows)
        self.clear_action.setEnabled(has_entries)
        self.sort_menu.setEnabled(has_entries)

        global_pos = self.list_ctrl._list_view.viewport().mapToGlobal(position)
        self.context_menu.exec(global_pos)

    def set_playlist(self, playlist):
        self.current_playlist = playlist
        self.refresh_view()

    def refresh_view(self):
        self.list_ctrl.clear_items()

        if self.current_playlist is None:
            return

        for index, entry in enumerate(self.current_playlist.entries):
            filename = os.path.basename(entry.location)
            row = self.list_ctrl.append_item(str(index + 1))
            self.list_ctrl.set_item_text(row, 1, filename)
            self.list_ctrl.set_item_text(row, 2, entry.title or "")
            self.list_ctrl.set_item_text(row, 3, entry.artist or "")
            self.list_ctrl.set_item_text(row, 4, entry.album or "")
            self.list_ctrl.set_item_data(row, entry)

        self._apply_now_playing_highlight()

    def update_now_playing(self, index: Optional[int]):
        self._now_playing_index = index
        self._apply_now_playing_highlight()

    def _apply_now_playing_highlight(self):
        bold_font = QFont()
        bold_font.setBold(True)
        normal_font = QFont()
        for row in range(self.list_ctrl.get_item_count()):
            is_current = self._now_playing_index is not None and row == self._now_playing_index
            self.list_ctrl.set_item_font(row, bold_font if is_current else normal_font)

    def _get_focused_row(self) -> int:
        row = self.list_ctrl.get_current_item()
        if 0 <= row < self.list_ctrl.get_item_count():
            return row
        return -1

    def _selected_playlist_indexes(self):
        rows = self.list_ctrl.get_selected_items()
        if rows:
            return rows

        focused_row = self._get_focused_row()
        return [focused_row] if focused_row >= 0 else []

    def _save_playlist_changes(self):
        if callable(self.playlist_changed_callback):
            self.playlist_changed_callback()

    def _play_row(self, row: int):
        if self.current_playlist is None:
            return
        if row < 0 or row >= len(self.current_playlist.entries):
            return

        if self.play_callback:
            self.play_callback(self.current_playlist, row)
        else:
            self.play_playlist_signal.emit(self.current_playlist)

    @Slot()
    def persist_current_order(self):
        if self.current_playlist is None:
            return

        ordered_entries = []
        for row in range(self.list_ctrl.get_item_count()):
            entry = self.list_ctrl.get_item_data(row)
            if entry is not None:
                ordered_entries.append(entry)

        self.current_playlist.entries = ordered_entries
        self._save_playlist_changes()
        signal_manager.statusbar_message.emit(_("Playlist order updated"))

    @Slot(int)
    def on_row_activated(self, row):
        self._play_row(row)

    def move_selected_rows(self, step: int) -> bool:
        rows = self.list_ctrl.get_selected_items()
        focused_row = self._get_focused_row()
        if not rows and focused_row >= 0:
            self.list_ctrl.select_item(focused_row, True)

        return self.list_ctrl.move_selected_items(step)

    @Slot()
    def add_tracks(self):
        if self.current_playlist is None:
            QMessageBox.warning(self, _("Warning"), _("No playlist selected"))
            return

        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilter(_("Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a);;All Files (*)"))

        if not file_dialog.exec():
            return

        files = file_dialog.selectedFiles()
        added_count = 0
        for file_path in files:
            self.current_playlist.add_entry(PlaylistEntry(location=file_path))
            added_count += 1

        if added_count:
            self.refresh_view()
            self._save_playlist_changes()
            signal_manager.statusbar_message.emit(
                _("Added {count} track(s) to playlist").format(count=added_count)
            )

    @Slot()
    def delete_selected(self):
        if self.current_playlist is None:
            return

        indexes = self._selected_playlist_indexes()
        if not indexes:
            return

        message = (
            _("Delete the selected track?")
            if len(indexes) == 1
            else _("Delete the selected {count} tracks?").format(count=len(indexes))
        )
        reply = QMessageBox.question(
            self,
            _("Confirm"),
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        for index in reversed(indexes):
            self.current_playlist.remove_entry(index)

        self.refresh_view()
        self._save_playlist_changes()
        signal_manager.statusbar_message.emit(
            _("Removed {count} track(s) from playlist").format(count=len(indexes))
        )

    @Slot()
    def clear_tracks(self):
        if self.current_playlist is None or not self.current_playlist.entries:
            return

        reply = QMessageBox.question(
            self,
            _("Confirm"),
            _("Clear all tracks from this playlist?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        removed_count = len(self.current_playlist.entries)
        self.current_playlist.clear()
        self.refresh_view()
        self._save_playlist_changes()
        signal_manager.statusbar_message.emit(
            _("Removed {count} track(s) from playlist").format(count=removed_count)
        )

    @Slot(str, bool)
    def sort_tracks(self, key, reverse=False):
        if self.current_playlist is None or not self.current_playlist.entries:
            return

        if key == "location":
            self.current_playlist.sort(
                key=lambda entry: os.path.basename(entry.location).lower(),
                reverse=reverse,
            )
        else:
            self.current_playlist.sort(key=key, reverse=reverse)

        self.refresh_view()
        self._save_playlist_changes()
        signal_manager.statusbar_message.emit(_("Playlist sorted"))

from ..dialogs.bookmarks_dialog import BookmarksDialog
from PySide6.QtWidgets import QDialog


class BookmarksController:
    """Bookmark add/jump/delete/persist logic extracted from PlayerControls.
    Operates directly on the owning PlayerControls' state (_current_file,
    _bookmarks, _state, _bookmarks_dialog, ...) rather than duplicating it."""

    def __init__(self, controls):
        self._c = controls

    def show_bookmarks_dialog(self):
        c = self._c
        if not c._current_file or c._current_file not in c._bookmarks:
            return
        bookmarks = c._bookmarks[c._current_file]
        if not bookmarks:
            return
        mw = getattr(c._player_widget, "_main_window", None) or c.window()
        if hasattr(mw, '_dialog_open') and mw._dialog_open:
            return
        if hasattr(mw, '_dialog_open'):
            mw._dialog_open = True
        c._bookmarks_dialog = BookmarksDialog(bookmarks, c)
        dlg = c._bookmarks_dialog
        dlg.deleteRequested.connect(self.delete_bookmark_at)
        dlg.clearAllRequested.connect(self.clear_bookmarks)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected_index = dlg.get_selected_bookmark_index()
            if selected_index is not None:
                self.jump_to_mark(selected_index)
        c._bookmarks_dialog = None
        if hasattr(mw, '_dialog_open'):
            mw._dialog_open = False

    def add_bookmark_at_current_position(self):
        c = self._c
        if not c._current_file:
            return

        current_pos = c.get_seek_position()

        c._state.bookmarks = c._bookmarks
        if c._state.add_bookmark(c._current_file, float(current_pos)):
            c._bookmarks = c._state.bookmarks
        if hasattr(c, '_bookmarks_dialog') and isinstance(c._bookmarks_dialog, BookmarksDialog) and c._bookmarks_dialog is not None:
            self._refresh_bookmarks_dialog()

    def jump_to_mark(self, mark_index: int):
        c = self._c
        if not c._current_file or c._current_file not in c._bookmarks:
            return

        bookmarks = c._bookmarks[c._current_file]
        if mark_index < len(bookmarks):
            position = bookmarks[mark_index]
            c._current_bookmark_index = mark_index
            c.set_seek_position(int(position))
            c.seekChanged.emit(int(position))

    def jump_to_previous_bookmark(self):
        c = self._c
        if not c._current_file or c._current_file not in c._bookmarks:
            return

        bookmarks = c._bookmarks[c._current_file]
        if not bookmarks:
            return

        if c._current_bookmark_index <= 0:
            c._current_bookmark_index = len(bookmarks) - 1
        else:
            c._current_bookmark_index -= 1

        position = bookmarks[c._current_bookmark_index]
        c.set_seek_position(int(position))
        c.seekChanged.emit(int(position))

    def jump_to_next_bookmark(self):
        c = self._c
        if not c._current_file or c._current_file not in c._bookmarks:
            return

        bookmarks = c._bookmarks[c._current_file]
        if not bookmarks:
            return

        if c._current_bookmark_index >= len(bookmarks) - 1 or c._current_bookmark_index < 0:
            c._current_bookmark_index = 0
        else:
            c._current_bookmark_index += 1

        position = bookmarks[c._current_bookmark_index]
        c.set_seek_position(int(position))
        c.seekChanged.emit(int(position))

    def delete_current_bookmark(self):
        c = self._c
        if not c._current_file or c._current_file not in c._bookmarks:
            return
        if not hasattr(c, '_bookmarks_dialog') or c._bookmarks_dialog is None:
            return
        idx = c._bookmarks_dialog.get_selected_bookmark_index()
        if idx is None:
            return
        c._state.bookmarks = c._bookmarks
        if c._state.delete_bookmark(c._current_file, idx):
            c._bookmarks = c._state.bookmarks
            c._bookmarks_dialog.remove_bookmark_at(idx)

    def delete_bookmark_at(self, index: int):
        c = self._c
        if not c._current_file or c._current_file not in c._bookmarks:
            return
        c._state.bookmarks = c._bookmarks
        if c._state.delete_bookmark(c._current_file, index):
            c._bookmarks = c._state.bookmarks
            c._current_bookmark_index = -1
            self._refresh_bookmarks_dialog()

    def add_bookmark_at_position(self, position: float):
        c = self._c
        if not c._current_file:
            return False
        c._state.bookmarks = c._bookmarks
        ok = c._state.add_bookmark(c._current_file, position)
        c._bookmarks = c._state.bookmarks
        if ok and hasattr(c, '_bookmarks_dialog') and c._bookmarks_dialog is not None:
            self._refresh_bookmarks_dialog()
        return ok

    def update_bookmark_at_index(self, index: int, position: float):
        c = self._c
        if not c._current_file:
            return False
        c._state.bookmarks = c._bookmarks
        ok = c._state.update_bookmark(c._current_file, index, position)
        c._bookmarks = c._state.bookmarks
        if ok and hasattr(c, '_bookmarks_dialog') and c._bookmarks_dialog is not None:
            self._refresh_bookmarks_dialog()
        return ok

    def get_bookmarks(self):
        c = self._c
        if not c._current_file:
            return []
        c._state.bookmarks = c._bookmarks
        return c._state.get_bookmarks(c._current_file)

    def clear_bookmarks(self):
        c = self._c
        if not c._current_file:
            return
        c._state.bookmarks = c._bookmarks
        if c._state.clear_bookmarks(c._current_file):
            c._bookmarks = c._state.bookmarks
            c._current_bookmark_index = -1
            if hasattr(c, '_bookmarks_dialog') and c._bookmarks_dialog is not None:
                c._bookmarks_dialog.clear_all()

    def save_bookmarks(self):
        c = self._c
        c._state.bookmarks = c._bookmarks
        c._state.save_bookmarks()

    def load_bookmarks(self):
        c = self._c
        c._state.load_bookmarks()
        c._bookmarks = c._state.bookmarks

    def _refresh_bookmarks_dialog(self):
        c = self._c
        if not hasattr(c, '_bookmarks_dialog') or c._bookmarks_dialog is None:
            return
        dlg = c._bookmarks_dialog
        dlg.clear_all()
        if c._current_file and c._current_file in c._bookmarks:
            for i, bookmark in enumerate(c._bookmarks[c._current_file]):
                minutes = int(bookmark // 60)
                seconds = int(bookmark % 60)
                dlg.bookmarks_list.addItem(
                    _("Mark {index}: {minutes:02d}:{seconds:02d}").format(
                        index=i + 1,
                        minutes=minutes,
                        seconds=seconds,
                    )
                )

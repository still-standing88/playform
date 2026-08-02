import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

import app_db
from app_config import prefs
from media_core.metaindex import indexer as index_indexer
from media_core.metaindex import schema as index_schema

_COMMIT_EVERY = 50


class CatalogWorker(QThread):
    """Single, long-lived, controllable thread for folder cataloging.

    Folders are scanned one at a time from a FIFO queue; enqueue_folder()
    starts the thread if it isn't already running. The filesystem walk and
    the actual metadata extraction (via media_core.metaparser, through
    metaindex.indexer) both happen here (I/O and CPU bound, off the UI
    thread) against a metaindex connection this thread owns for the
    duration of the scan - metaindex's sqlite3 connections aren't shared
    across threads, so this worker never hands rows to another thread to
    write, unlike catalog_roots bookkeeping which still goes through
    media_db's own queue-writer thread.
    """

    folder_started = Signal(str)
    progress = Signal(str, int, int, int)  # path, files_seen, added, skipped
    folder_finished = Signal(str, int, int)  # path, added, skipped
    error = Signal(str, str)
    paused_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending = []
        self._is_running = True
        self._cancel_current = False
        # Set = running, cleared = paused. Starts set (not paused).
        self._resume_event = threading.Event()
        self._resume_event.set()

        # Mirrors the state of the last emitted signal, so a dialog that
        # connects after a folder_started/progress signal already fired
        # (e.g. queued cross-thread emits landing before the dialog exists
        # to receive them) can still initialize itself correctly instead of
        # being stuck on "No folder being scanned" while stats keep
        # updating from progress signals it does catch.
        self.current_folder = None
        self.current_seen = 0
        self.current_added = 0
        self.current_skipped = 0
        self.current_finished = True
        self.current_error = None

    def enqueue_folder(self, path: str):
        self._pending.append(path)
        if not self.isRunning():
            self.start()

    def cancel_current(self):
        self._cancel_current = True
        self._resume_event.set()  # unblock a paused wait so cancellation can take effect

    def cancel_all(self):
        """Cancels the folder currently being scanned and drops any queued
        (not-yet-started) folders - used when the user asks to terminate
        outright rather than just stop the current one. Doesn't touch
        _is_running, so the same worker instance (a singleton reused for
        the app's lifetime) is still usable for a future catalog request."""
        self._pending.clear()
        self.cancel_current()

    def stop(self):
        self._is_running = False
        self._cancel_current = True
        self._resume_event.set()

    def pause(self):
        if self._resume_event.is_set():
            self._resume_event.clear()
            self.paused_changed.emit(True)

    def resume(self):
        if not self._resume_event.is_set():
            self._resume_event.set()
            self.paused_changed.emit(False)

    def is_paused(self) -> bool:
        return not self._resume_event.is_set()

    def run(self):
        while self._is_running and self._pending:
            path = self._pending.pop(0)
            self._cancel_current = False
            self._scan_folder(path)

    def _allowed_extensions(self) -> set:
        return {"." + ext.lstrip(".").lower() for ext in prefs.prefs.get("catalog_extensions", [])}

    def _scan_folder(self, root_path: str):
        self.current_folder = root_path
        self.current_seen = self.current_added = self.current_skipped = 0
        self.current_finished = False
        self.current_error = None
        self.folder_started.emit(root_path)
        allowed_extensions = self._allowed_extensions()
        seen = added = skipped = 0

        conn = app_db.media_db.open_index_connection()
        try:
            existing = index_indexer.load_existing_stats(conn)

            for file_path in Path(root_path).rglob("*"):
                self._resume_event.wait()
                if self._cancel_current or not self._is_running:
                    break

                try:
                    if not file_path.is_file() or file_path.suffix.lower() not in allowed_extensions:
                        continue

                    seen += 1
                    if index_indexer.index_file(conn, file_path, existing=existing):
                        added += 1
                    else:
                        skipped += 1

                    if seen % _COMMIT_EVERY == 0:
                        conn.commit()

                    self.current_seen, self.current_added, self.current_skipped = seen, added, skipped
                    self.progress.emit(root_path, seen, added, skipped)
                except (OSError, PermissionError):
                    skipped += 1
                    continue

            conn.commit()
            # Total files currently indexed under this root, not just
            # `added` (this scan's new/changed count) - a repeat scan of an
            # unchanged folder would otherwise report a shrinking/zero
            # file_count even though everything is still cataloged.
            total = index_schema.count_under_root(conn, root_path)
            app_db.media_db.add_catalog_root(root_path)
            app_db.media_db.update_catalog_root_scan_stats(root_path, total)
            self.current_finished = True
            self.folder_finished.emit(root_path, added, skipped)
        except Exception as e:
            self.current_finished = True
            self.current_error = str(e)
            self.error.emit(root_path, str(e))
        finally:
            conn.close()

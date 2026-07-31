from pathlib import Path

from PySide6.QtCore import QThread, Signal

import app_db
from app_config import prefs
from media_core.metaindex import indexer as index_indexer

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending = []
        self._is_running = True
        self._cancel_current = False

    def enqueue_folder(self, path: str):
        self._pending.append(path)
        if not self.isRunning():
            self.start()

    def cancel_current(self):
        self._cancel_current = True

    def stop(self):
        self._is_running = False
        self._cancel_current = True

    def run(self):
        while self._is_running and self._pending:
            path = self._pending.pop(0)
            self._cancel_current = False
            self._scan_folder(path)

    def _allowed_extensions(self) -> set:
        return {"." + ext.lstrip(".").lower() for ext in prefs.prefs.get("catalog_extensions", [])}

    def _scan_folder(self, root_path: str):
        self.folder_started.emit(root_path)
        allowed_extensions = self._allowed_extensions()
        seen = added = skipped = 0

        conn = app_db.media_db.open_index_connection()
        try:
            existing = index_indexer.load_existing_stats(conn)

            for file_path in Path(root_path).rglob("*"):
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

                    self.progress.emit(root_path, seen, added, skipped)
                except (OSError, PermissionError):
                    skipped += 1
                    continue

            conn.commit()
            app_db.media_db.add_catalog_root(root_path)
            app_db.media_db.update_catalog_root_scan_stats(root_path, added)
            self.folder_finished.emit(root_path, added, skipped)
        except Exception as e:
            self.error.emit(root_path, str(e))
        finally:
            conn.close()

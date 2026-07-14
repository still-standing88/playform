import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal

import app_db
from .base_database import MediaFile, MediaType
from app_config import prefs
from utilities.formats import formats

_BATCH_SIZE = 200


class CatalogWorker(QThread):
    """Single, long-lived, controllable thread for folder cataloging.

    Folders are scanned one at a time from a FIFO queue; enqueue_folder()
    starts the thread if it isn't already running. The filesystem walk
    happens here (I/O bound, off the UI thread); writes are handed to
    media_db's own queue-writer thread via add_media_files(), so this
    thread never touches SQLite directly.
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

    def _extension_map(self):
        allowed = set(prefs.prefs.get("catalog_extensions", []))
        video_exts = set(formats["video"])
        mapping = {}
        for ext in allowed:
            mapping[ext] = MediaType.VIDEO if ext in video_exts else MediaType.AUDIO
        return mapping

    def _scan_folder(self, root_path: str):
        self.folder_started.emit(root_path)
        extension_map = self._extension_map()
        seen = added = skipped = 0
        batch = []

        try:
            for file_path in Path(root_path).rglob("*"):
                if self._cancel_current or not self._is_running:
                    break

                try:
                    if not file_path.is_file():
                        continue
                    suffix = file_path.suffix.lower().lstrip(".")
                    media_type = extension_map.get(suffix)
                    if media_type is None:
                        continue

                    stat = file_path.stat()
                    seen += 1
                    batch.append(MediaFile(
                        id=app_db.media_db._generate_file_id(str(file_path)),
                        path=str(file_path),
                        filename=file_path.name,
                        size=stat.st_size,
                        duration=None,
                        media_type=media_type,
                        metadata={},
                        date_added=str(stat.st_ctime),
                        date_modified=str(stat.st_mtime),
                    ))
                    added += 1

                    if len(batch) >= _BATCH_SIZE:
                        app_db.media_db.add_media_files(batch)
                        batch = []

                    self.progress.emit(root_path, seen, added, skipped)
                except (OSError, PermissionError):
                    skipped += 1
                    continue

            if batch:
                app_db.media_db.add_media_files(batch)

            app_db.media_db.add_catalog_root(root_path)
            app_db.media_db.update_catalog_root_scan_stats(root_path, added)
            self.folder_finished.emit(root_path, added, skipped)
        except Exception as e:
            self.error.emit(root_path, str(e))

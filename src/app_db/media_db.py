import os
import hashlib
import time
from typing import List, Any

from .base_database import BaseDatabaseHandler
from media_core.metaindex import schema as index_schema
from media_core.metaindex import search as index_search
from media_core.metaindex.search import SearchResult


class MediaDatabase(BaseDatabaseHandler):

    MEDIA_SCHEMA = """
    CREATE TABLE IF NOT EXISTS catalog_roots (
        id TEXT PRIMARY KEY NOT NULL,
        path TEXT NOT NULL UNIQUE,
        date_added TEXT NOT NULL,
        date_last_scanned TEXT,
        file_count INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_catalog_roots_path ON catalog_roots(path);
    """

    def __init__(self, db_path: str = os.path.join("data", "media.sqlite3"), simple_mode: bool = False, index_db_path: str = None):
        super().__init__(db_path, self.MEDIA_SCHEMA, simple_mode)
        self.index_db_path = index_db_path or os.path.join(os.path.dirname(db_path) or ".", "media_index.sqlite3")

    def _process_queue_operation(self, operation: str, data: Any, connection):
        if operation == "add_catalog_root":
            self._add_catalog_root_worker(data, connection)
        elif operation == "remove_catalog_root":
            self._remove_catalog_root_worker(data, connection)
        elif operation == "update_catalog_root_scan_stats":
            self._update_catalog_root_scan_stats_worker(data, connection)

    def _generate_root_id(self, path: str) -> str:
        return hashlib.md5(os.path.normcase(os.path.normpath(path)).encode()).hexdigest()

    def _add_catalog_root_worker(self, path: str, db):
        now = str(time.time())
        db.execute_sql(
            "INSERT OR IGNORE INTO catalog_roots (id, path, date_added, date_last_scanned, file_count) VALUES (?, ?, ?, NULL, 0)",
            (self._generate_root_id(path), path, now),
        )

    def _remove_catalog_root_worker(self, path: str, db):
        db.execute_sql("DELETE FROM catalog_roots WHERE id = ?", (self._generate_root_id(path),))

    def _update_catalog_root_scan_stats_worker(self, data: dict, db):
        db.execute_sql(
            "UPDATE catalog_roots SET date_last_scanned = ?, file_count = ? WHERE id = ?",
            (str(time.time()), data["file_count"], self._generate_root_id(data["path"])),
        )

    def add_catalog_root(self, path: str):
        path = os.path.normpath(path)
        if self._simple_mode:
            self._add_catalog_root_worker(path, self._db)
        else:
            self._entry_queue.put(("add_catalog_root", path))

    def remove_catalog_root(self, path: str):
        path = os.path.normpath(path)
        if self._simple_mode:
            self._remove_catalog_root_worker(path, self._db)
        else:
            self._entry_queue.put(("remove_catalog_root", path))

    def update_catalog_root_scan_stats(self, path: str, file_count: int):
        data = {"path": os.path.normpath(path), "file_count": file_count}
        if self._simple_mode:
            self._update_catalog_root_scan_stats_worker(data, self._db)
        else:
            self._entry_queue.put(("update_catalog_root_scan_stats", data))

    def get_catalog_roots(self) -> List[str]:
        cursor = self._db.execute_sql("SELECT path FROM catalog_roots ORDER BY date_added ASC")
        return [row[0] for row in cursor.fetchall()]

    def is_path_cataloged(self, path: str) -> bool:
        normalized = os.path.normcase(os.path.normpath(path))
        for root in self.get_catalog_roots():
            root_normalized = os.path.normcase(os.path.normpath(root))
            if normalized == root_normalized or normalized.startswith(root_normalized + os.sep):
                return True
        return False

    def open_index_connection(self):
        """A fresh metaindex connection, owned by the calling thread for as
        long as it needs it (e.g. CatalogWorker for the duration of one
        folder scan) - metaindex's sqlite3 connections aren't shared across
        threads, mirroring the discipline base_database's own queue-writer
        thread already follows with its own connection."""
        return index_schema.open_db(self.index_db_path)

    def search_by_filename(self, query: str, limit: int = 50) -> List[SearchResult]:
        return index_search.full_text_search(self.index_db_path, query, limit=limit)

    def clear_index(self):
        conn = index_schema.open_db(self.index_db_path)
        try:
            index_schema.clear(conn)
        finally:
            conn.close()

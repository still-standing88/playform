import os
import hashlib
from typing import Optional, List, Any
from datetime import datetime

from .base_database import BaseDatabaseHandler, FileEntry, FileCategory


class UserFiles(BaseDatabaseHandler):

    USER_FILES_SCHEMA = """
    CREATE TABLE IF NOT EXISTS user_files (
        id TEXT PRIMARY KEY NOT NULL,
        path TEXT NOT NULL,
        category TEXT CHECK(category IN ('FAVORITE', 'RECENT', 'LIBRARY')) NOT NULL,
        date_added TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_category ON user_files(category);
    CREATE INDEX IF NOT EXISTS idx_date_added ON user_files(date_added);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_path_category ON user_files(path, category);
    """

    # app_settings/user_presets/download_queue hold everything that used to
    # be scattered across independent data/*.json files (toolbar config,
    # dock session, multi device capture config, playback state, radio
    # favorites, playlists registry, mpv/ffmpeg presets, download queue,
    # non-dialog runtime prefs, ...) -- see AppSettingsStore/PresetsStore in
    # settings_store.py for the read/write helpers built on these.
    APP_SETTINGS_SCHEMA = """
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY NOT NULL,
        value TEXT NOT NULL,
        updated_at TEXT
    );
    """

    USER_PRESETS_SCHEMA = """
    CREATE TABLE IF NOT EXISTS user_presets (
        id TEXT PRIMARY KEY NOT NULL,
        kind TEXT NOT NULL,
        name TEXT NOT NULL,
        data TEXT NOT NULL,
        updated_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_presets_kind ON user_presets(kind);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_presets_kind_name ON user_presets(kind, name);
    """

    # Persists Downloader's non-terminal queue (queued/paused; active items
    # are saved as paused, since a mid-flight HTTP transfer can't resume
    # across a process restart) so the Download Manager -- including
    # podcast episode downloads -- survives an app restart instead of
    # living only in memory. See downloader.Downloader.persist()/restore().
    DOWNLOAD_QUEUE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS download_queue (
        id TEXT PRIMARY KEY NOT NULL,
        url TEXT NOT NULL,
        destination TEXT NOT NULL,
        filename TEXT NOT NULL,
        status TEXT NOT NULL,
        downloaded_size INTEGER NOT NULL DEFAULT 0,
        total_size INTEGER NOT NULL DEFAULT 0,
        metadata TEXT,
        added_at TEXT,
        updated_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_download_queue_status ON download_queue(status);
    """

    SCHEMA_VERSION = 3

    def __init__(self, db_path: str = os.path.join("data", "user.sqlite3"), simple_mode: bool = False):
        full_schema = (self.USER_FILES_SCHEMA + self.APP_SETTINGS_SCHEMA
                        + self.USER_PRESETS_SCHEMA + self.DOWNLOAD_QUEUE_SCHEMA)
        migrations = [
            (2, [
                stmt.strip() for stmt in
                (self.APP_SETTINGS_SCHEMA + self.USER_PRESETS_SCHEMA).split(";")
                if stmt.strip()
            ]),
            (3, [
                stmt.strip() for stmt in self.DOWNLOAD_QUEUE_SCHEMA.split(";")
                if stmt.strip()
            ]),
        ]
        super().__init__(db_path, full_schema, simple_mode,
                          schema_version=self.SCHEMA_VERSION, migrations=migrations)

    def save_download_queue_row(self, row: dict) -> bool:
        try:
            self._db.execute_sql(
                "INSERT INTO download_queue "
                "(id, url, destination, filename, status, downloaded_size, total_size, metadata, added_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET url=excluded.url, destination=excluded.destination, "
                "filename=excluded.filename, status=excluded.status, downloaded_size=excluded.downloaded_size, "
                "total_size=excluded.total_size, metadata=excluded.metadata, updated_at=excluded.updated_at",
                (
                    row["id"], row["url"], row["destination"], row["filename"], row["status"],
                    row.get("downloaded_size", 0), row.get("total_size", 0), row.get("metadata"),
                    row.get("added_at"), row.get("updated_at"),
                ),
            )
            return True
        except Exception:
            import logging
            logging.exception("save_download_queue_row failed")
            return False

    def delete_download_queue_row(self, item_id: str) -> bool:
        try:
            self._db.execute_sql("DELETE FROM download_queue WHERE id = ?", (item_id,))
            return True
        except Exception:
            import logging
            logging.exception("delete_download_queue_row failed")
            return False

    def load_download_queue_rows(self) -> List[dict]:
        try:
            cursor = self._db.execute_sql(
                "SELECT id, url, destination, filename, status, downloaded_size, total_size, metadata, added_at, updated_at "
                "FROM download_queue"
            )
            columns = ["id", "url", "destination", "filename", "status", "downloaded_size", "total_size", "metadata", "added_at", "updated_at"]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception:
            import logging
            logging.exception("load_download_queue_rows failed; returning empty queue")
            return []

    def _generate_entry_id(self, path: str, category: FileCategory) -> str:
        return hashlib.md5(f"{path}_{category.value}".encode()).hexdigest()

    def _process_queue_operation(self, operation: str, data: Any, connection):
        if operation == "add_entry":
            self._add_entry_worker(data, connection)

    def _add_entry_worker(self, entry: FileEntry, db):
        db.execute_sql(
            "INSERT OR REPLACE INTO user_files (id, path, category, date_added) VALUES (?, ?, ?, ?)",
            (entry.id, entry.path, entry.category.value, entry.date_added),
        )

    def add_favorite(self, path: str):
        entry_id = self._generate_entry_id(path, FileCategory.FAVORITE)
        entry = FileEntry(entry_id, path, FileCategory.FAVORITE, str(datetime.now().timestamp()))

        if self._simple_mode:
            self._add_entry_worker(entry, self._db)
        else:
            self._entry_queue.put(("add_entry", entry))

    def add_recent(self, path: str):
        entry_id = self._generate_entry_id(path, FileCategory.RECENT)
        entry = FileEntry(entry_id, path, FileCategory.RECENT, str(datetime.now().timestamp()))

        if self._simple_mode:
            self._add_entry_worker(entry, self._db)
        else:
            self._entry_queue.put(("add_entry", entry))

    def add_library_folder(self, path: str):
        entry_id = self._generate_entry_id(path, FileCategory.LIBRARY)
        entry = FileEntry(entry_id, path, FileCategory.LIBRARY, str(datetime.now().timestamp()))

        if self._simple_mode:
            self._add_entry_worker(entry, self._db)
        else:
            self._entry_queue.put(("add_entry", entry))

    def remove_favorite(self, path: str):
        self._db.execute_sql(
            "DELETE FROM user_files WHERE path = ? AND category = ?",
            (path, FileCategory.FAVORITE.value),
        )

    def remove_recent(self, path: str):
        self._db.execute_sql(
            "DELETE FROM user_files WHERE path = ? AND category = ?",
            (path, FileCategory.RECENT.value),
        )

    def remove_library_folder(self, path: str):
        self._db.execute_sql(
            "DELETE FROM user_files WHERE path = ? AND category = ?",
            (path, FileCategory.LIBRARY.value),
        )

    def clear_favorites(self):
        self._db.execute_sql(
            "DELETE FROM user_files WHERE category = ?",
            (FileCategory.FAVORITE.value,),
        )

    def clear_recents(self):
        self._db.execute_sql(
            "DELETE FROM user_files WHERE category = ?",
            (FileCategory.RECENT.value,),
        )

    def clear_library_folders(self):
        self._db.execute_sql(
            "DELETE FROM user_files WHERE category = ?",
            (FileCategory.LIBRARY.value,),
        )

    def get_favorites(self, limit: Optional[int] = None) -> List[str]:
        if limit:
            cursor = self._db.execute_sql(
                "SELECT path FROM user_files WHERE category = ? ORDER BY date_added DESC LIMIT ?",
                (FileCategory.FAVORITE.value, limit),
            )
        else:
            cursor = self._db.execute_sql(
                "SELECT path FROM user_files WHERE category = ? ORDER BY date_added DESC",
                (FileCategory.FAVORITE.value,),
            )
        return [row[0] for row in cursor.fetchall()]

    def get_recents(self, limit: Optional[int] = None) -> List[str]:
        if limit:
            cursor = self._db.execute_sql(
                "SELECT path FROM user_files WHERE category = ? ORDER BY date_added DESC LIMIT ?",
                (FileCategory.RECENT.value, limit),
            )
        else:
            cursor = self._db.execute_sql(
                "SELECT path FROM user_files WHERE category = ? ORDER BY date_added DESC",
                (FileCategory.RECENT.value,),
            )
        return [row[0] for row in cursor.fetchall()]

    def get_library_folders(self) -> List[str]:
        cursor = self._db.execute_sql(
            "SELECT path FROM user_files WHERE category = ? ORDER BY date_added ASC",
            (FileCategory.LIBRARY.value,),
        )
        return [row[0] for row in cursor.fetchall()]

    def is_favorite(self, path: str) -> bool:
        cursor = self._db.execute_sql(
            "SELECT 1 FROM user_files WHERE path = ? AND category = ?",
            (path, FileCategory.FAVORITE.value),
        )
        return cursor.fetchone() is not None

    def is_in_library(self, path: str) -> bool:
        cursor = self._db.execute_sql(
            "SELECT 1 FROM user_files WHERE path = ? AND category = ?",
            (path, FileCategory.LIBRARY.value),
        )
        return cursor.fetchone() is not None

    def cleanup_recents(self, max_count: int = 100):
        self._db.execute_sql(
            "DELETE FROM user_files WHERE category = ? AND id NOT IN "
            "(SELECT id FROM user_files WHERE category = ? ORDER BY date_added DESC LIMIT ?)",
            (FileCategory.RECENT.value, FileCategory.RECENT.value, max_count),
        )

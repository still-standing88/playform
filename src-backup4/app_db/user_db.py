import os
import sqlite3
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

    def __init__(self, db_path: str = os.path.join("data", "user.sqlite3"), simple_mode: bool = False):
        super().__init__(db_path, self.USER_FILES_SCHEMA, simple_mode)

    def _generate_entry_id(self, path: str, category: FileCategory) -> str:
        return hashlib.md5(f"{path}_{category.value}".encode()).hexdigest()

    def _process_queue_operation(self, operation: str, data: Any, cursor: sqlite3.Cursor, connection: sqlite3.Connection):
        if operation == "add_entry":
            self._add_entry_worker(data, cursor, connection)

    def _add_entry_worker(self, entry: FileEntry, cursor: sqlite3.Cursor, connection: sqlite3.Connection):
        cursor.execute(
            "INSERT OR REPLACE INTO user_files (id, path, category, date_added) VALUES (?, ?, ?, ?)",
            (entry.id, entry.path, entry.category.value, entry.date_added)
        )
        connection.commit()

    def add_favorite(self, path: str):
        entry_id = self._generate_entry_id(path, FileCategory.FAVORITE)
        entry = FileEntry(entry_id, path, FileCategory.FAVORITE, str(datetime.now().timestamp()))
        
        if self._simple_mode:
            self._add_entry_worker(entry, self.get_cursor(), self._connection) # type: ignore
        else:
            self._entry_queue.put(("add_entry", entry))

    def add_recent(self, path: str):
        entry_id = self._generate_entry_id(path, FileCategory.RECENT)
        entry = FileEntry(entry_id, path, FileCategory.RECENT, str(datetime.now().timestamp()))
        
        if self._simple_mode:
            self._add_entry_worker(entry, self.get_cursor(), self._connection) # type: ignore
        else:
            self._entry_queue.put(("add_entry", entry))

    def add_library_folder(self, path: str):
        entry_id = self._generate_entry_id(path, FileCategory.LIBRARY)
        entry = FileEntry(entry_id, path, FileCategory.LIBRARY, str(datetime.now().timestamp()))
        
        if self._simple_mode:
            self._add_entry_worker(entry, self.get_cursor(), self._connection) # type: ignore
        else:
            self._entry_queue.put(("add_entry", entry))

    def remove_favorite(self, path: str):
        cursor = self.get_cursor()
        cursor.execute("DELETE FROM user_files WHERE path = ? AND category = ?", (path, FileCategory.FAVORITE.value))
        self._connection.commit() # type: ignore

    def remove_recent(self, path: str):
        cursor = self.get_cursor()
        cursor.execute("DELETE FROM user_files WHERE path = ? AND category = ?", (path, FileCategory.RECENT.value))
        self._connection.commit() # type: ignore

    def remove_library_folder(self, path: str):
        cursor = self.get_cursor()
        cursor.execute("DELETE FROM user_files WHERE path = ? AND category = ?", (path, FileCategory.LIBRARY.value))
        self._connection.commit() # type: ignore

    def clear_favorites(self):
        cursor = self.get_cursor()
        cursor.execute("DELETE FROM user_files WHERE category = ?", (FileCategory.FAVORITE.value,))
        self._connection.commit() # type: ignore

    def clear_recents(self):
        cursor = self.get_cursor()
        cursor.execute("DELETE FROM user_files WHERE category = ?", (FileCategory.RECENT.value,))
        self._connection.commit() # type: ignore

    def clear_library_folders(self):
        cursor = self.get_cursor()
        cursor.execute("DELETE FROM user_files WHERE category = ?", (FileCategory.LIBRARY.value,))
        self._connection.commit() # type: ignore

    def get_favorites(self, limit: Optional[int] = None) -> List[str]:
        cursor = self.get_cursor()
        if limit:
            cursor.execute("SELECT path FROM user_files WHERE category = ? ORDER BY date_added DESC LIMIT ?", 
                          (FileCategory.FAVORITE.value, limit))
        else:
            cursor.execute("SELECT path FROM user_files WHERE category = ? ORDER BY date_added DESC", 
                          (FileCategory.FAVORITE.value,))
        return [row[0] for row in cursor.fetchall()]

    def get_recents(self, limit: Optional[int] = None) -> List[str]:
        cursor = self.get_cursor()
        if limit:
            cursor.execute("SELECT path FROM user_files WHERE category = ? ORDER BY date_added DESC LIMIT ?", 
                          (FileCategory.RECENT.value, limit))
        else:
            cursor.execute("SELECT path FROM user_files WHERE category = ? ORDER BY date_added DESC", 
                          (FileCategory.RECENT.value,))
        return [row[0] for row in cursor.fetchall()]

    def get_library_folders(self) -> List[str]:
        cursor = self.get_cursor()
        cursor.execute("SELECT path FROM user_files WHERE category = ? ORDER BY date_added ASC", 
                      (FileCategory.LIBRARY.value,))
        return [row[0] for row in cursor.fetchall()]

    def is_favorite(self, path: str) -> bool:
        cursor = self.get_cursor()
        cursor.execute("SELECT 1 FROM user_files WHERE path = ? AND category = ?", 
                      (path, FileCategory.FAVORITE.value))
        return cursor.fetchone() is not None

    def is_in_library(self, path: str) -> bool:
        cursor = self.get_cursor()
        cursor.execute("SELECT 1 FROM user_files WHERE path = ? AND category = ?", 
                      (path, FileCategory.LIBRARY.value))
        return cursor.fetchone() is not None

    def cleanup_recents(self, max_count: int = 100):
        cursor = self.get_cursor()
        cursor.execute(
            "DELETE FROM user_files WHERE category = ? AND id NOT IN (SELECT id FROM user_files WHERE category = ? ORDER BY date_added DESC LIMIT ?)",
            (FileCategory.RECENT.value, FileCategory.RECENT.value, max_count)
        )
        self._connection.commit() # type: ignore
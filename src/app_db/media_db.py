import os
import hashlib
import json
from typing import Optional, List, Dict, Any
from pathlib import Path

from .base_database import BaseDatabaseHandler, MediaFile, MediaType


class MediaDatabase(BaseDatabaseHandler):

    MEDIA_SCHEMA = """
    CREATE TABLE IF NOT EXISTS media_files (
        id TEXT PRIMARY KEY NOT NULL,
        path TEXT NOT NULL UNIQUE,
        filename TEXT NOT NULL,
        size INTEGER NOT NULL,
        duration REAL,
        media_type TEXT CHECK(media_type IN ('VIDEO', 'AUDIO', 'MUSIC')) NOT NULL,
        metadata TEXT,
        date_added TEXT NOT NULL,
        date_modified TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_media_type ON media_files(media_type);
    CREATE INDEX IF NOT EXISTS idx_filename ON media_files(filename);
    CREATE INDEX IF NOT EXISTS idx_path ON media_files(path);
    """

    def __init__(self, db_path: str = os.path.join("data", "media.sqlite3"), simple_mode: bool = False):
        super().__init__(db_path, self.MEDIA_SCHEMA, simple_mode)

    def _generate_file_id(self, file_path: str) -> str:
        return hashlib.md5(file_path.encode()).hexdigest()

    def _process_queue_operation(self, operation: str, data: Any, connection):
        if operation == "add_media":
            self._add_media_worker(data, connection)
        elif operation == "add_media_batch":
            self._add_media_batch_worker(data, connection)

    def _add_media_worker(self, media: MediaFile, db):
        db.execute_sql(
            "INSERT OR REPLACE INTO media_files (id, path, filename, size, duration, media_type, metadata, date_added, date_modified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (media.id, media.path, media.filename, media.size, media.duration, media.media_type.value, json.dumps(media.metadata), media.date_added, media.date_modified),
        )

    def _add_media_batch_worker(self, media_list: List[MediaFile], db):
        for m in media_list:
            db.execute_sql(
                "INSERT OR REPLACE INTO media_files (id, path, filename, size, duration, media_type, metadata, date_added, date_modified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (m.id, m.path, m.filename, m.size, m.duration, m.media_type.value, json.dumps(m.metadata), m.date_added, m.date_modified),
            )

    def add_media_file(self, media: MediaFile):
        if self._simple_mode:
            self._add_media_worker(media, self._db)
        else:
            self._entry_queue.put(("add_media", media))

    def add_media_files(self, media_list: List[MediaFile]):
        if self._simple_mode:
            self._add_media_batch_worker(media_list, self._db)
        else:
            self._entry_queue.put(("add_media_batch", media_list))

    def scan_folder(self, folder_path: str, extensions: Optional[Dict[MediaType, List[str]]] = None) -> List[MediaFile]:
        if extensions is None:
            extensions = {
                MediaType.VIDEO: ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'],
                MediaType.AUDIO: ['.wav', '.flac', '.aac', '.ogg'],
                MediaType.MUSIC: ['.mp3', '.m4a', '.opus']
            }

        media_files = []
        folder = Path(folder_path)

        if not folder.exists():
            return media_files

        for file_path in folder.rglob('*'):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                media_type = None

                for mtype, exts in extensions.items():
                    if suffix in exts:
                        media_type = mtype
                        break

                if media_type:
                    stat = file_path.stat()
                    file_id = self._generate_file_id(str(file_path))

                    media_file = MediaFile(
                        id=file_id,
                        path=str(file_path),
                        filename=file_path.name,
                        size=stat.st_size,
                        duration=None,
                        media_type=media_type,
                        metadata={},
                        date_added=str(stat.st_ctime),
                        date_modified=str(stat.st_mtime)
                    )
                    media_files.append(media_file)

        return media_files

    def search_by_filename(self, query: str, media_type: Optional[MediaType] = None, limit: Optional[int] = None) -> List[MediaFile]:
        like_q = f"%{query}%"
        if media_type:
            if limit:
                cursor = self._db.execute_sql(
                    "SELECT * FROM media_files WHERE filename LIKE ? AND media_type = ? ORDER BY filename LIMIT ?",
                    (like_q, media_type.value, limit),
                )
            else:
                cursor = self._db.execute_sql(
                    "SELECT * FROM media_files WHERE filename LIKE ? AND media_type = ? ORDER BY filename",
                    (like_q, media_type.value),
                )
        else:
            if limit:
                cursor = self._db.execute_sql(
                    "SELECT * FROM media_files WHERE filename LIKE ? ORDER BY filename LIMIT ?",
                    (like_q, limit),
                )
            else:
                cursor = self._db.execute_sql(
                    "SELECT * FROM media_files WHERE filename LIKE ? ORDER BY filename",
                    (like_q,),
                )
        return self._rows_to_media_files(cursor.fetchall())

    def filter_by_type(self, media_type: MediaType, limit: Optional[int] = None) -> List[MediaFile]:
        if limit:
            cursor = self._db.execute_sql(
                "SELECT * FROM media_files WHERE media_type = ? ORDER BY filename LIMIT ?",
                (media_type.value, limit),
            )
        else:
            cursor = self._db.execute_sql(
                "SELECT * FROM media_files WHERE media_type = ? ORDER BY filename",
                (media_type.value,),
            )
        return self._rows_to_media_files(cursor.fetchall())

    def get_by_id(self, file_id: str) -> Optional[MediaFile]:
        cursor = self._db.execute_sql(
            "SELECT * FROM media_files WHERE id = ?",
            (file_id,),
        )
        row = cursor.fetchone()
        return self._row_to_media_file(row) if row else None

    def delete_media_file(self, file_id: str):
        self._db.execute_sql(
            "DELETE FROM media_files WHERE id = ?",
            (file_id,),
        )

    def get_all_media(self) -> List[MediaFile]:
        cursor = self._db.execute_sql("SELECT * FROM media_files ORDER BY filename")
        return self._rows_to_media_files(cursor.fetchall())

    def _row_to_media_file(self, row) -> MediaFile:
        metadata_str = row[6] if row[6] else "{}"
        try:
            metadata = json.loads(metadata_str)
        except Exception:
            metadata = {}
        return MediaFile(
            id=row[0], path=row[1], filename=row[2], size=row[3], duration=row[4],
            media_type=MediaType(row[5]), metadata=metadata,
            date_added=row[7], date_modified=row[8],
        )

    def _rows_to_media_files(self, rows) -> List[MediaFile]:
        return [self._row_to_media_file(row) for row in rows]

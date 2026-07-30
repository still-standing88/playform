import os
import hashlib
from typing import Optional, List, Dict, Any
from pathlib import Path
from sqlalchemy import text

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

    def _process_queue_operation(self, operation: str, data: Any, cursor, connection):
        if operation == "add_media":
            self._add_media_worker(data, cursor, connection)
        elif operation == "add_media_batch":
            self._add_media_batch_worker(data, cursor, connection)

    def _add_media_worker(self, media: MediaFile, cursor, connection):
        cursor.execute(
            text("INSERT OR REPLACE INTO media_files (id, path, filename, size, duration, media_type, metadata, date_added, date_modified) VALUES (:id, :path, :filename, :size, :duration, :media_type, :metadata, :date_added, :date_modified)"),
            {"id": media.id, "path": media.path, "filename": media.filename, "size": media.size, "duration": media.duration, "media_type": media.media_type.value, "metadata": str(media.metadata), "date_added": media.date_added, "date_modified": media.date_modified}
        )
        connection.commit()

    def _add_media_batch_worker(self, media_list: List[MediaFile], cursor, connection):
        media_tuples = [
            (m.id, m.path, m.filename, m.size, m.duration, m.media_type.value, str(m.metadata), m.date_added, m.date_modified)
            for m in media_list
        ]
        for t in media_tuples:
            cursor.execute(
                text("INSERT OR REPLACE INTO media_files (id, path, filename, size, duration, media_type, metadata, date_added, date_modified) VALUES (:id, :path, :filename, :size, :duration, :media_type, :metadata, :date_added, :date_modified)"),
                {"id": t[0], "path": t[1], "filename": t[2], "size": t[3], "duration": t[4], "media_type": t[5], "metadata": t[6], "date_added": t[7], "date_modified": t[8]}
            )
        connection.commit()

    def add_media_file(self, media: MediaFile):
        if self._simple_mode:
            self._add_media_worker(media, self.get_cursor(), self.get_cursor())
        else:
            self._entry_queue.put(("add_media", media))

    def add_media_files(self, media_list: List[MediaFile]):
        if self._simple_mode:
            self._add_media_batch_worker(media_list, self.get_cursor(), self.get_cursor())
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
        cursor = self.get_cursor()
        like_q = f"%{query}%"
        if media_type:
            if limit:
                result = cursor.execute(text("SELECT * FROM media_files WHERE filename LIKE :q AND media_type = :mt ORDER BY filename LIMIT :lim"), {"q": like_q, "mt": media_type.value, "lim": limit})
            else:
                result = cursor.execute(text("SELECT * FROM media_files WHERE filename LIKE :q AND media_type = :mt ORDER BY filename"), {"q": like_q, "mt": media_type.value})
        else:
            if limit:
                result = cursor.execute(text("SELECT * FROM media_files WHERE filename LIKE :q ORDER BY filename LIMIT :lim"), {"q": like_q, "lim": limit})
            else:
                result = cursor.execute(text("SELECT * FROM media_files WHERE filename LIKE :q ORDER BY filename"), {"q": like_q})
        return self._rows_to_media_files(result.fetchall())

    def filter_by_type(self, media_type: MediaType, limit: Optional[int] = None) -> List[MediaFile]:
        cursor = self.get_cursor()
        if limit:
            result = cursor.execute(text("SELECT * FROM media_files WHERE media_type = :mt ORDER BY filename LIMIT :lim"), {"mt": media_type.value, "lim": limit})
        else:
            result = cursor.execute(text("SELECT * FROM media_files WHERE media_type = :mt ORDER BY filename"), {"mt": media_type.value})
        return self._rows_to_media_files(result.fetchall())

    def get_by_id(self, file_id: str) -> Optional[MediaFile]:
        cursor = self.get_cursor()
        result = cursor.execute(text("SELECT * FROM media_files WHERE id = :id"), {"id": file_id})
        row = result.fetchone()
        return self._row_to_media_file(row) if row else None

    def delete_media_file(self, file_id: str):
        cursor = self.get_cursor()
        cursor.execute(text("DELETE FROM media_files WHERE id = :id"), {"id": file_id})
        cursor.commit()

    def get_all_media(self) -> List[MediaFile]:
        cursor = self.get_cursor()
        result = cursor.execute(text("SELECT * FROM media_files ORDER BY filename"))
        return self._rows_to_media_files(result.fetchall())

    def _row_to_media_file(self, row) -> MediaFile:
        return MediaFile(
            id=row[0], path=row[1], filename=row[2], size=row[3], duration=row[4],
            media_type=MediaType(row[5]), metadata=eval(row[6]) if row[6] else {},
            date_added=row[7], date_modified=row[8]
        )

    def _rows_to_media_files(self, rows) -> List[MediaFile]:
        return [self._row_to_media_file(row) for row in rows]
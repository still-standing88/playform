import os
import sqlite3
import threading
import queue
from contextlib import contextmanager
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass

class MediaType(Enum):
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    MUSIC = "MUSIC"

class FileCategory(Enum):
    FAVORITE = "FAVORITE"
    RECENT = "RECENT"
    LIBRARY = "LIBRARY"

@dataclass
class MediaFile:
    id: str
    path: str
    filename: str
    size: int
    duration: Optional[float]
    media_type: MediaType
    metadata: Dict[str, Any]
    date_added: str
    date_modified: str

@dataclass
class FileEntry:
    id: str
    path: str
    category: FileCategory
    date_added: str

class BaseDatabaseHandler:
    
    def __init__(self, db_path: str, schema: str, simple_mode: bool = False):
        self._db_path = db_path
        self._schema = schema
        self._connection: Optional[sqlite3.Connection] = None
        self._cursor: Optional[sqlite3.Cursor] = None
        self._simple_mode = simple_mode
        
        if not self._simple_mode:
            self._entry_queue = queue.Queue()
            self._queue_thread = None
            self._stop_queue = threading.Event()

    def __enter__(self):
        if not self._connection:
            self.connect_to_database()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()

    def connect_to_database(self):
        is_first_run = not os.path.exists(self._db_path)
        if is_first_run:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

        self._connection = sqlite3.connect(self._db_path)
        self._cursor = self._connection.cursor()

        if is_first_run:
            self._cursor.executescript(self._schema)
            self._connection.commit()
        
        if not self._simple_mode:
            self._start_queue_worker()

    def _start_queue_worker(self):
        self._queue_thread = threading.Thread(target=self._queue_worker, daemon=True)
        self._queue_thread.start()

    def _queue_worker(self):
        worker_connection = sqlite3.connect(self._db_path)
        worker_cursor = worker_connection.cursor()
        
        while not self._stop_queue.is_set():
            try:
                operation, data = self._entry_queue.get(timeout=1)
                self._process_queue_operation(operation, data, worker_cursor, worker_connection)
                self._entry_queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                pass
        
        worker_cursor.close()
        worker_connection.close()

    def _process_queue_operation(self, operation: str, data: Any, cursor: sqlite3.Cursor, connection: sqlite3.Connection):
        pass

    def close_connection(self):
        if not self._simple_mode:
            self._stop_queue.set()
            if self._queue_thread:
                self._queue_thread.join(timeout=2)
        
        if self._cursor:
            self._cursor.close()
        if self._connection:
            self._connection.close()
        self._connection = None
        self._cursor = None

    def get_cursor(self) -> sqlite3.Cursor:
        if not self._cursor:
            raise RuntimeError("Database connection is not established.")
        return self._cursor

    @contextmanager
    def get_connection(self):
        connection = sqlite3.connect(self._db_path)
        cursor = connection.cursor()
        try:
            yield connection, cursor
        finally:
            cursor.close()
            connection.close()
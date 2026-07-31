import os
import logging
import threading
import queue
from typing import Optional, Any
from enum import Enum
from dataclasses import dataclass
from peewee import SqliteDatabase


class FileCategory(Enum):
    FAVORITE = "FAVORITE"
    RECENT = "RECENT"
    LIBRARY = "LIBRARY"


@dataclass
class FileEntry:
    id: str
    path: str
    category: FileCategory
    date_added: str


class BaseDatabaseHandler:

    def __init__(self, db_path: str, schema_sql: str, simple_mode: bool = False):
        self._db_path = db_path
        self._schema_sql = schema_sql
        self._db: Optional[SqliteDatabase] = None
        self._simple_mode = simple_mode

        if not self._simple_mode:
            self._entry_queue = queue.Queue()
            self._queue_thread = None
            self._stop_queue = threading.Event()

    def __enter__(self):
        if not self._db:
            self.connect_to_database()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()

    def connect_to_database(self):
        is_first_run = not os.path.exists(self._db_path)
        if is_first_run:
            dir_name = os.path.dirname(self._db_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

        self._db = SqliteDatabase(
            self._db_path,
            pragmas={
                "journal_mode": "wal",
                "cache_size": -4096,
                "foreign_keys": 1,
            },
        )
        self._db.connect()

        if is_first_run:
            for stmt in filter(None, (s.strip() for s in self._schema_sql.split(";"))):
                self._db.execute_sql(stmt)

        if not self._simple_mode:
            self._start_queue_worker()

    def _start_queue_worker(self):
        self._queue_thread = threading.Thread(target=self._queue_worker, daemon=True)
        self._queue_thread.start()

    def _queue_worker(self):
        _win_com = None
        if os.name == "nt":
            try:
                import pythoncom
                pythoncom.CoInitialize()
                _win_com = pythoncom
            except Exception:
                _win_com = None

        worker_db = SqliteDatabase(
            self._db_path,
            pragmas={"journal_mode": "wal", "cache_size": -4096, "foreign_keys": 1},
        )
        worker_db.connect()

        while not self._stop_queue.is_set():
            try:
                operation, data = self._entry_queue.get(timeout=1)
                self._process_queue_operation(operation, data, worker_db)
                self._entry_queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                logging.exception("DB queue worker error while processing operation")

        worker_db.close()
        if _win_com is not None:
            try:
                _win_com.CoUninitialize()
            except Exception:
                pass

    def _process_queue_operation(self, operation: str, data: Any, connection):
        pass

    def close_connection(self):
        if not self._simple_mode:
            self._stop_queue.set()
            if self._queue_thread:
                self._queue_thread.join(timeout=2)

        if self._db:
            self._db.close()
        self._db = None

    def get_cursor(self):
        if not self._db:
            raise RuntimeError("Database connection is not established.")
        return self._db.connection()

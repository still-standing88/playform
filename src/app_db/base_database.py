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

    def __init__(self, db_path: str, schema_sql: str, simple_mode: bool = False,
                 schema_version: int = 1, migrations: Optional[list] = None):
        self._db_path = db_path
        self._schema_sql = schema_sql
        self._db: Optional[SqliteDatabase] = None
        self._simple_mode = simple_mode
        # schema_version is the version schema_sql itself represents (what a
        # first-run DB gets stamped with). migrations is a list of
        # (version, [sql, ...]) pairs applied in order to an *existing* DB
        # whose stored PRAGMA user_version is lower -- each statement runs
        # independently so one bad statement (e.g. a column that already
        # exists from a partial prior run) doesn't block the rest.
        self._schema_version = schema_version
        self._migrations = migrations or []

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
            try:
                self._db.execute_sql(f"PRAGMA user_version = {int(self._schema_version)}")
            except Exception:
                logging.exception("Failed to stamp initial schema version for %s", self._db_path)
        else:
            self._run_migrations()

        if not self._simple_mode:
            self._start_queue_worker()

    def _run_migrations(self):
        if not self._migrations or not self._db:
            return
        try:
            row = self._db.execute_sql("PRAGMA user_version").fetchone()
            current_version = row[0] if row else 0
        except Exception:
            logging.exception("Failed to read schema version for %s; assuming 0", self._db_path)
            current_version = 0

        for version, statements in self._migrations:
            if version <= current_version:
                continue
            for stmt in statements:
                try:
                    self._db.execute_sql(stmt)
                except Exception:
                    logging.exception(
                        "Migration to schema version %s failed for statement on %s "
                        "(continuing -- missing tables/columns are handled gracefully "
                        "at the call site)", version, self._db_path
                    )
            try:
                self._db.execute_sql(f"PRAGMA user_version = {int(version)}")
            except Exception:
                logging.exception("Failed to stamp schema version %s for %s", version, self._db_path)

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

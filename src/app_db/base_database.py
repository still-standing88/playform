import os
import logging
import threading
import queue
from contextlib import contextmanager
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

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
        self._engine = None
        self._SessionFactory: Optional[sessionmaker] = None
        self._session: Optional[Session] = None
        self._simple_mode = simple_mode
        
        if not self._simple_mode:
            self._entry_queue = queue.Queue()
            self._queue_thread = None
            self._stop_queue = threading.Event()

    def __enter__(self):
        if not self._session:
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
        self._engine = create_engine(
            f"sqlite:///{self._db_path}",
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
        self._SessionFactory = sessionmaker(bind=self._engine, expire_on_commit=False, autoflush=False, autocommit=False)
        assert self._SessionFactory is not None
        self._session = self._SessionFactory()

        if is_first_run:
            with self._engine.begin() as conn:
                for stmt in filter(None, (s.strip() for s in self._schema.split(';'))):
                    conn.execute(text(stmt))

        if not self._simple_mode:
            self._start_queue_worker()

    def _start_queue_worker(self):
        self._queue_thread = threading.Thread(target=self._queue_worker, daemon=True)
        self._queue_thread.start()

    def _queue_worker(self):
        _win_com = None
        if os.name == "nt":
            try:
                import pythoncom  # type: ignore
                pythoncom.CoInitialize()
                _win_com = pythoncom
            except Exception:
                _win_com = None
        worker_engine = create_engine(
            f"sqlite:///{self._db_path}",
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
        WorkerSession = sessionmaker(bind=worker_engine, expire_on_commit=False, autoflush=False, autocommit=False)
        worker_session: Session = WorkerSession()

        while not self._stop_queue.is_set():
            try:
                operation, data = self._entry_queue.get(timeout=1)
                self._process_queue_operation(operation, data, worker_session, worker_session)
                self._entry_queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                logging.exception("DB queue worker error while processing operation")
        
        worker_session.close()
        worker_engine.dispose()
        if _win_com is not None:
            try:
                _win_com.CoUninitialize()
            except Exception:
                pass

    def _process_queue_operation(self, operation: str, data: Any, cursor, connection):
        pass

    def close_connection(self):
        if not self._simple_mode:
            self._stop_queue.set()
            if self._queue_thread:
                self._queue_thread.join(timeout=2)
        
        if self._session:
            self._session.close()
        if self._engine:
            self._engine.dispose()
        self._session = None
        self._engine = None

    def get_cursor(self):
        if not self._session:
            raise RuntimeError("Database connection is not established.")
        return self._session

    @contextmanager
    def get_connection(self):
        if not self._engine:
            raise RuntimeError("Database engine is not initialized.")
        SessionLocal = sessionmaker(bind=self._engine, expire_on_commit=False, autoflush=False, autocommit=False)
        session = SessionLocal()
        try:
            yield session, session
        finally:
            session.close()
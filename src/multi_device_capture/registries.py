"""In-memory source/session pools, persisted in app_settings (user.sqlite3) -
same pattern as app_config.toolbar_config."""
from __future__ import annotations

import os
from typing import Optional

from utilities.functions import get_app_path

from .models import CaptureSource, Session

SOURCES_KEY = "multi_device_capture_sources"
SESSIONS_KEY = "multi_device_capture_sessions"
# Legacy paths only kept around for the one-shot migration in load().
LEGACY_SOURCES_FILE = os.path.join(get_app_path(), "data", "multi_device_capture_sources.json")
LEGACY_SESSIONS_FILE = os.path.join(get_app_path(), "data", "multi_device_capture_sessions.json")


class SourceRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, CaptureSource] = {}
        self.load()

    def all(self) -> list[CaptureSource]:
        return list(self._sources.values())

    def get(self, source_id: str) -> Optional[CaptureSource]:
        return self._sources.get(source_id)

    def add(self, source: CaptureSource) -> None:
        self._sources[source.id] = source
        self.save()

    def remove(self, source_id: str) -> None:
        self._sources.pop(source_id, None)
        self.save()

    def save(self) -> bool:
        from app_db import app_settings
        return app_settings.set(SOURCES_KEY, [s.to_dict() for s in self._sources.values()])

    def load(self) -> None:
        from app_db import app_settings
        from app_db.settings_store import migrate_json_file
        data = migrate_json_file(app_settings, LEGACY_SOURCES_FILE, SOURCES_KEY, default=[])
        self._sources = {}
        for entry in data:
            try:
                src = CaptureSource.from_dict(entry)
                self._sources[src.id] = src
            except Exception:
                continue


class SessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self.load()

    def all(self) -> list[Session]:
        return list(self._sessions.values())

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def add(self, session: Session) -> None:
        self._sessions[session.id] = session
        self.save()

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self.save()

    def save(self) -> bool:
        from app_db import app_settings
        return app_settings.set(SESSIONS_KEY, [s.to_dict() for s in self._sessions.values()])

    def load(self) -> None:
        from app_db import app_settings
        from app_db.settings_store import migrate_json_file
        data = migrate_json_file(app_settings, LEGACY_SESSIONS_FILE, SESSIONS_KEY, default=[])
        self._sessions = {}
        for entry in data:
            try:
                session = Session.from_dict(entry)
                self._sessions[session.id] = session
            except Exception:
                continue

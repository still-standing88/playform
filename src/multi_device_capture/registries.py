"""In-memory source/session pools, persisted as plain JSON under data/ -
same pattern as app_config.toolbar_config (unobfuscated JSON, not the
hexify'd prefs.json format, since this isn't the global app-prefs store)."""
from __future__ import annotations

import json
import os
from typing import Optional

from utilities.functions import get_app_path

from .models import CaptureSource, Session

SOURCES_FILE = os.path.join(get_app_path(), "data", "multi_device_capture_sources.json")
SESSIONS_FILE = os.path.join(get_app_path(), "data", "multi_device_capture_sessions.json")


class SourceRegistry:
    def __init__(self, store_path: str = SOURCES_FILE) -> None:
        self._store_path = store_path
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
        try:
            os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
            with open(self._store_path, "w") as f:
                json.dump([s.to_dict() for s in self._sources.values()], f, indent=2)
            return True
        except Exception as exc:
            print(f"Failed to save capture source pool: {exc}")
            return False

    def load(self) -> None:
        if not os.path.exists(self._store_path):
            return
        try:
            with open(self._store_path, "r") as f:
                data = json.load(f)
            self._sources = {}
            for entry in data:
                try:
                    src = CaptureSource.from_dict(entry)
                    self._sources[src.id] = src
                except Exception:
                    continue
        except Exception as exc:
            print(f"Failed to load capture source pool: {exc}")


class SessionRegistry:
    def __init__(self, store_path: str = SESSIONS_FILE) -> None:
        self._store_path = store_path
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
        try:
            os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
            with open(self._store_path, "w") as f:
                json.dump([s.to_dict() for s in self._sessions.values()], f, indent=2)
            return True
        except Exception as exc:
            print(f"Failed to save capture sessions: {exc}")
            return False

    def load(self) -> None:
        if not os.path.exists(self._store_path):
            return
        try:
            with open(self._store_path, "r") as f:
                data = json.load(f)
            self._sessions = {}
            for entry in data:
                try:
                    session = Session.from_dict(entry)
                    self._sessions[session.id] = session
                except Exception:
                    continue
        except Exception as exc:
            print(f"Failed to load capture sessions: {exc}")

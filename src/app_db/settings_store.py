import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional, List


class AppSettingsStore:
    """Generic key -> JSON-blob store backed by UserFiles' app_settings
    table. Replaces the many independent data/*.json files (toolbar config,
    dock session, multi device capture config, playback state, radio
    favorites, playlists registry, non-dialog runtime prefs, ...) with rows
    in the user's SQLite database.

    get()/set() never raise on a missing row, malformed JSON, or a database
    error -- callers get `default` back and the error is logged, per the
    "missing values or errors in the database are handled silently and
    gracefully" requirement. There is no schema to keep in sync per key:
    any JSON-serializable value can be stored.
    """

    def __init__(self, db_handler):
        self._db_handler = db_handler

    def get(self, key: str, default: Any = None) -> Any:
        try:
            db = self._db_handler._db
            if db is None:
                return default
            cursor = db.execute_sql("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
        except Exception:
            logging.exception("AppSettingsStore.get(%r) failed; returning default", key)
            return default
        if not row:
            return default
        try:
            return json.loads(row[0])
        except Exception:
            logging.exception("AppSettingsStore.get(%r): stored value is not valid JSON; returning default", key)
            return default

    def set(self, key: str, value: Any) -> bool:
        try:
            db = self._db_handler._db
            if db is None:
                return False
            payload = json.dumps(value)
            db.execute_sql(
                "INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (key, payload, datetime.now().isoformat()),
            )
            return True
        except Exception:
            logging.exception("AppSettingsStore.set(%r) failed", key)
            return False

    def delete(self, key: str) -> bool:
        try:
            db = self._db_handler._db
            if db is None:
                return False
            db.execute_sql("DELETE FROM app_settings WHERE key = ?", (key,))
            return True
        except Exception:
            logging.exception("AppSettingsStore.delete(%r) failed", key)
            return False


class PresetsStore:
    """kind/name -> JSON-blob preset store backed by UserFiles'
    user_presets table (mpv effect presets, ffmpeg batch-converter presets,
    ...). Same silent/graceful-on-error contract as AppSettingsStore."""

    def __init__(self, db_handler):
        self._db_handler = db_handler

    def list_names(self, kind: str) -> List[str]:
        try:
            db = self._db_handler._db
            if db is None:
                return []
            cursor = db.execute_sql(
                "SELECT name FROM user_presets WHERE kind = ? ORDER BY name ASC", (kind,)
            )
            return [row[0] for row in cursor.fetchall()]
        except Exception:
            logging.exception("PresetsStore.list_names(%r) failed", kind)
            return []

    def get(self, kind: str, name: str, default: Any = None) -> Any:
        try:
            db = self._db_handler._db
            if db is None:
                return default
            cursor = db.execute_sql(
                "SELECT data FROM user_presets WHERE kind = ? AND name = ?", (kind, name)
            )
            row = cursor.fetchone()
        except Exception:
            logging.exception("PresetsStore.get(%r, %r) failed; returning default", kind, name)
            return default
        if not row:
            return default
        try:
            return json.loads(row[0])
        except Exception:
            logging.exception("PresetsStore.get(%r, %r): stored value is not valid JSON; returning default", kind, name)
            return default

    def set(self, kind: str, name: str, data: Any) -> bool:
        try:
            db = self._db_handler._db
            if db is None:
                return False
            payload = json.dumps(data)
            preset_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{kind}:{name}").hex
            db.execute_sql(
                "INSERT INTO user_presets (id, kind, name, data, updated_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(kind, name) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at",
                (preset_id, kind, name, payload, datetime.now().isoformat()),
            )
            return True
        except Exception:
            logging.exception("PresetsStore.set(%r, %r) failed", kind, name)
            return False

    def delete(self, kind: str, name: str) -> bool:
        try:
            db = self._db_handler._db
            if db is None:
                return False
            db.execute_sql("DELETE FROM user_presets WHERE kind = ? AND name = ?", (kind, name))
            return True
        except Exception:
            logging.exception("PresetsStore.delete(%r, %r) failed", kind, name)
            return False

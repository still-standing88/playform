"""Global Audio/Video defaults for the Multi Device Capture panel -
what a session falls back to unless it defines its own settings_override.
Persisted in app_settings (user.sqlite3), same pattern as
app_config.toolbar_config.ToolbarConfig."""
from __future__ import annotations

import json
import os

from utilities.functions import get_app_path

SETTINGS_KEY = "multi_device_capture_settings"
# Legacy path only kept around for the one-shot migration in load().
LEGACY_SETTINGS_FILE = os.path.join(get_app_path(), "data", "multi_device_capture_settings.json")

DEFAULT_SETTINGS = {
    "audio": {
        "sample_rate": 48000,
        "channels": 2,
        "volume": 100,
    },
    "video": {
        "resolution_cap": "Passthrough",
        "fps": 30,
        "capture_cursor": False,
    },
    "hotkeys_enabled": True,
    "last_active_session_id": "",
    "default_output_dir": "",
    "default_container": "mkv",
    "notify_on_finish": True,
    "keep_segments_after_pause": False,
}


class MultiDeviceCaptureSettings:
    def __init__(self) -> None:
        self.data: dict = json.loads(json.dumps(DEFAULT_SETTINGS))  # deep copy
        self.load()

    def get_audio(self) -> dict:
        return dict(self.data.get("audio", DEFAULT_SETTINGS["audio"]))

    def get_video(self) -> dict:
        return dict(self.data.get("video", DEFAULT_SETTINGS["video"]))

    def set_audio(self, values: dict) -> None:
        self.data.setdefault("audio", {}).update(values)
        self.save()

    def set_video(self, values: dict) -> None:
        self.data.setdefault("video", {}).update(values)
        self.save()

    def get(self, key: str, default=None):
        return self.data.get(key, DEFAULT_SETTINGS.get(key, default))

    def set(self, key: str, value) -> None:
        self.data[key] = value
        self.save()

    def save(self) -> bool:
        from app_db import app_settings
        return app_settings.set(SETTINGS_KEY, self.data)

    def load(self) -> None:
        from app_db import app_settings
        from app_db.settings_store import migrate_json_file
        loaded = migrate_json_file(app_settings, LEGACY_SETTINGS_FILE, SETTINGS_KEY)
        if not loaded:
            self.data = json.loads(json.dumps(DEFAULT_SETTINGS))
            self.save()
            return
        merged = json.loads(json.dumps(DEFAULT_SETTINGS))
        for key, value in loaded.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key].update(value)
            else:
                merged[key] = value
        self.data = merged


multi_device_capture_settings = MultiDeviceCaptureSettings()

import os
from typing import Optional
from utilities.functions import get_app_path


class DockPanelSession:

    SETTINGS_KEY = "dock_session"

    def __init__(self):
        # Legacy path only kept around for the one-shot migration below --
        # dock session state itself now lives in app_settings (user.sqlite3).
        self._legacy_session_file = os.path.join(get_app_path(), 'data', 'dock_session.json')
        self.default_config = {
            'recents_favorites': True,
            'explorer': False,
            'player': True,
            'playlists': False,
            'radio': False,
            'podcast': False,
            'debug_console': False,
            'sidebar_hidden': False,
            'controls_minimized': False
        }

    def save_session(self, dock_states: dict[str, bool]) -> bool:
        from app_db import app_settings
        return app_settings.set(self.SETTINGS_KEY, dock_states)

    def load_session(self) -> dict[str, bool]:
        from app_db import app_settings
        from app_db.settings_store import migrate_json_file
        data = migrate_json_file(app_settings, self._legacy_session_file, self.SETTINGS_KEY)
        if not data:
            return self.default_config.copy()
        return data

    def get_default_config(self) -> dict[str, bool]:
        return self.default_config.copy()


dock_session = DockPanelSession()

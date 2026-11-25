from copy import deepcopy

from PySide6.QtCore import QObject, Signal

from app_constance.touch_gestures import normalize_settings


class TouchConfig(QObject):
    changed = Signal()
    SETTINGS_KEY = "touch_gestures"

    def __init__(self, store=None, parent=None):
        super().__init__(parent)
        self._store = store
        self._settings = None

    def _settings_store(self):
        if self._store is None:
            from app_db import app_settings
            return app_settings
        return self._store

    def snapshot(self):
        if self._settings is None:
            self._settings = normalize_settings(self._settings_store().get(self.SETTINGS_KEY))
        return deepcopy(self._settings)

    def save(self, settings):
        settings = normalize_settings(settings)
        if not self._settings_store().set(self.SETTINGS_KEY, settings):
            return False
        self._settings = settings
        self.changed.emit()
        return True


touch_config = TouchConfig()

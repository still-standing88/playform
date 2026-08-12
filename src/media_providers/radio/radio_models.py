from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from utilities.functions import get_app_path


class FavoritesManager:

    SETTINGS_KEY = "radio_stations"

    def __init__(self):
        # Legacy path only kept around for the one-shot migration in
        # _load() -- radio favorites now live in app_settings (user.sqlite3).
        self._legacy_favorites_file = Path(get_app_path()) / "data" / "radio_stations.json"
        self.favorites: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        from app_db import app_settings
        from app_db.settings_store import migrate_json_file
        data = migrate_json_file(app_settings, str(self._legacy_favorites_file), self.SETTINGS_KEY, default={})
        return data if isinstance(data, dict) else {}

    def _save(self) -> None:
        from app_db import app_settings
        app_settings.set(self.SETTINGS_KEY, self.favorites)

    def add(self, station_data: Dict[str, Any]) -> None:
        uuid = station_data.get("uuid")
        if not uuid:
            return

        self.favorites[uuid] = {
            "uuid": uuid,
            "name": station_data.get("name", "Unknown"),
            "url": station_data.get("url", ""),
            "url_resolved": station_data.get("url_resolved", ""),
            "country": station_data.get("country", ""),
            "language": station_data.get("language", []),
            "tags": station_data.get("tags", []),
            "votes": station_data.get("votes", 0),
            "codec": station_data.get("codec", ""),
            "bitrate": station_data.get("bitrate", 0),
            "homepage": station_data.get("homepage", ""),
            "favicon": station_data.get("favicon", ""),
            "added_date": datetime.now().isoformat(),
        }
        self._save()

    def remove(self, uuid: str) -> None:
        if uuid in self.favorites:
            del self.favorites[uuid]
            self._save()

    def is_favorite(self, uuid: str) -> bool:
        return uuid in self.favorites

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self.favorites.values())

    def clear(self) -> None:
        self.favorites = {}
        self._save()

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from utilities.functions import get_app_path


class FavoritesManager:
    def __init__(self):
        self.data_dir = Path(get_app_path()) / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.favorites_file = self.data_dir / "radio_stations.json"
        self.favorites: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if self.favorites_file.exists():
            try:
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self) -> None:
        try:
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

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

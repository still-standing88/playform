import os
import pickle
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional
from utilities.functions import get_app_path


class RadioCache:
    def __init__(self):
        # Lives under data/cache/ alongside the podcast cache -- a single
        # shared cache root under data/ instead of scattered per-feature
        # top-level cache/ directories.
        self.cache_dir = Path(get_app_path()) / "data" / "cache" / "radio"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        legacy_cache_dir = Path(get_app_path()) / "cache" / "radio"
        if legacy_cache_dir.exists() and legacy_cache_dir != self.cache_dir:
            self._migrate_legacy_cache_dir(legacy_cache_dir)
        
        self.cache_expiry = {
            "stats": 24,
            "countries": 168,
            "languages": 168,
            "tags": 24,
            "search": 1,
            "filter": 1,
        }

    def _migrate_legacy_cache_dir(self, legacy_cache_dir: Path) -> None:
        try:
            for cache_file in legacy_cache_dir.glob("*.pkl"):
                try:
                    cache_file.replace(self.cache_dir / cache_file.name)
                except Exception:
                    pass
            try:
                legacy_cache_dir.rmdir()
            except Exception:
                pass
        except Exception:
            pass

    def _get_hash(self, key: str) -> str:
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    def _get_cache_path(self, cache_type: str, key: str = "") -> Path:
        safe_key = key.replace(' ', '_').replace('/', '_').replace('\\', '_')
        if safe_key:
            filename = f"{cache_type}_{self._get_hash(safe_key)}.pkl"
        else:
            filename = f"{cache_type}.pkl"
        return self.cache_dir / filename

    def is_valid(self, cache_type: str, key: str = "") -> bool:
        cache_path = self._get_cache_path(cache_type, key)
        if not cache_path.exists():
            return False
        
        mod_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiry_hours = self.cache_expiry.get(cache_type, 1)
        expiry_time = timedelta(hours=expiry_hours)
        
        return datetime.now() - mod_time < expiry_time

    def load(self, cache_type: str, key: str = "") -> Optional[Any]:
        cache_path = self._get_cache_path(cache_type, key)
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return None

    def save(self, cache_type: str, data: Any, key: str = "") -> None:
        cache_path = self._get_cache_path(cache_type, key)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except Exception:
            pass

    def clear(self, cache_type: Optional[str] = None) -> None:
        if cache_type:
            for cache_file in self.cache_dir.glob(f"{cache_type}*.pkl"):
                cache_file.unlink()
        else:
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()

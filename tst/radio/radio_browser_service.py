import asyncio
import json
import pickle
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from radios import FilterBy, Order, RadioBrowser
from radios.models import Country, Language, Station, Stats, Tag


class RadioBrowserService:
    
    def __init__(self, user_agent: str = "RadioBrowserWidget/1.0"):
        self.user_agent = user_agent
        self.cache_dir = Path("./cache")
        self.data_dir = Path("./data")
        self.cache_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        
        self.favorites_file = self.data_dir / "radio_stations.json"
        self.favorites: Dict[str, Dict[str, Any]] = self._load_favorites()
        
        self.cache_expiry = {
            "stats": 24,
            "countries": 168,
            "languages": 168,
            "tags": 24,
            "search": 1,
            "filter": 1,
        }

    def _load_favorites(self) -> Dict[str, Dict[str, Any]]:
        if self.favorites_file.exists():
            try:
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading favorites: {e}")
                return {}
        return {}

    def _save_favorites(self) -> None:
        try:
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(self.favorites, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving favorites: {e}")

    def _get_cache_path(self, cache_type: str, key: str = "") -> Path:
        safe_key = key.replace(' ', '_').replace('/', '_').replace('\\', '_')
        if safe_key:
            return self.cache_dir / f"{cache_type}_{safe_key}.pkl"
        return self.cache_dir / f"{cache_type}.pkl"

    def _is_cache_valid(self, cache_path: Path, cache_type: str) -> bool:
        if not cache_path.exists():
            return False
        
        mod_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        expiry_hours = self.cache_expiry.get(cache_type, 1)
        expiry_time = timedelta(hours=expiry_hours)
        
        return datetime.now() - mod_time < expiry_time

    def _load_cache(self, cache_path: Path) -> Optional[Any]:
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
            return None

    def _save_cache(self, cache_path: Path, data: Any) -> None:
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Error saving cache: {e}")

    async def get_stats(self, use_cache: bool = True) -> Stats:
        cache_path = self._get_cache_path("stats")
        
        if use_cache and self._is_cache_valid(cache_path, "stats"):
            cached = self._load_cache(cache_path)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            stats = await rb.stats()
        
        self._save_cache(cache_path, stats)
        return stats

    async def get_countries(self, use_cache: bool = True, **kwargs) -> List[Country]:
        cache_path = self._get_cache_path("countries")
        
        if use_cache and self._is_cache_valid(cache_path, "countries"):
            cached = self._load_cache(cache_path)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            countries = await rb.countries(
                order=kwargs.get('order', Order.NAME),
                reverse=kwargs.get('reverse', False),
                hide_broken=kwargs.get('hide_broken', False),
                limit=kwargs.get('limit', 100000),
                offset=kwargs.get('offset', 0),
            )
        
        self._save_cache(cache_path, countries)
        return countries

    async def get_languages(self, use_cache: bool = True, **kwargs) -> List[Language]:
        cache_path = self._get_cache_path("languages")
        
        if use_cache and self._is_cache_valid(cache_path, "languages"):
            cached = self._load_cache(cache_path)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            languages = await rb.languages(
                order=kwargs.get('order', Order.NAME),
                reverse=kwargs.get('reverse', False),
                hide_broken=kwargs.get('hide_broken', False),
                limit=kwargs.get('limit', 100000),
                offset=kwargs.get('offset', 0),
            )
        
        self._save_cache(cache_path, languages)
        return languages

    async def get_tags(self, use_cache: bool = True, **kwargs) -> List[Tag]:
        cache_path = self._get_cache_path("tags")
        
        if use_cache and self._is_cache_valid(cache_path, "tags"):
            cached = self._load_cache(cache_path)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            tags = await rb.tags(
                order=kwargs.get('order', Order.NAME),
                reverse=kwargs.get('reverse', False),
                hide_broken=kwargs.get('hide_broken', False),
                limit=kwargs.get('limit', 100000),
                offset=kwargs.get('offset', 0),
            )
        
        self._save_cache(cache_path, tags)
        return tags

    async def search_stations(self, use_cache: bool = True, **kwargs) -> List[Station]:
        name = kwargs.get('name', '')
        country = kwargs.get('country', '')
        
        cache_key = f"{name}_{country}_{kwargs.get('order', Order.NAME)}"
        cache_path = self._get_cache_path("search", cache_key)
        
        if use_cache and self._is_cache_valid(cache_path, "search"):
            cached = self._load_cache(cache_path)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            search_params = {
                'name': kwargs.get('name'),
                'country': kwargs.get('country'),
                'order': kwargs.get('order', Order.NAME),
                'reverse': kwargs.get('reverse', False),
                'limit': kwargs.get('limit', 100000),
                'offset': kwargs.get('offset', 0),
                'hide_broken': kwargs.get('hide_broken', False),
            }
            valid_params = {k: v for k, v in search_params.items() if v}
            stations = await rb.search(**valid_params)
        
        self._save_cache(cache_path, stations)
        return stations

    async def get_stations_by_filter(self, filter_by: FilterBy, filter_term: str, 
                                    use_cache: bool = True, **kwargs) -> List[Station]:
        cache_key = f"{filter_by.value}_{filter_term}_{kwargs.get('order', Order.NAME)}"
        cache_path = self._get_cache_path("filter", cache_key)
        
        if use_cache and self._is_cache_valid(cache_path, "filter"):
            cached = self._load_cache(cache_path)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            stations = await rb.stations(
                filter_by=filter_by,
                filter_term=filter_term,
                order=kwargs.get('order', Order.NAME),
                reverse=kwargs.get('reverse', False),
                limit=kwargs.get('limit', 100000),
                offset=kwargs.get('offset', 0),
                hide_broken=kwargs.get('hide_broken', False),
            )
        
        self._save_cache(cache_path, stations)
        return stations

    async def get_station_by_uuid(self, uuid: str) -> Optional[Station]:
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            stations = await rb.stations(filter_by=FilterBy.UUID, filter_term=uuid)
            return stations[0] if stations else None

    async def click_station(self, uuid: str) -> None:
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            await rb.station_click(uuid=uuid)

    def add_favorite(self, station: Station) -> None:
        self.favorites[station.uuid] = {
            "uuid": station.uuid,
            "name": station.name,
            "url": station.url,
            "url_resolved": station.url_resolved,
            "country": station.country,
            "language": station.language,
            "tags": station.tags,
            "votes": station.votes,
            "codec": station.codec,
            "bitrate": station.bitrate,
            "homepage": station.homepage,
            "favicon": station.favicon,
            "added_date": datetime.now().isoformat(),
        }
        self._save_favorites()

    def remove_favorite(self, uuid: str) -> None:
        if uuid in self.favorites:
            del self.favorites[uuid]
            self._save_favorites()

    def is_favorite(self, uuid: str) -> bool:
        return uuid in self.favorites

    def get_favorites(self) -> List[Dict[str, Any]]:
        return list(self.favorites.values())

    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        if cache_type:
            for cache_file in self.cache_dir.glob(f"{cache_type}*.pkl"):
                cache_file.unlink()
        else:
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()

    async def close(self):
        # Dummy close method if the underlying library doesn't need explicit closing
        pass
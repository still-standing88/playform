from typing import List, Optional, Dict, Any
from radios import FilterBy, Order, RadioBrowser
from radios.models import Country, Language, Station, Stats, Tag
from media_providers.radio.radio_cache import RadioCache
from media_providers.radio.radio_models import FavoritesManager


class RadioService:
    def __init__(self, user_agent: str = "PlayForm/1.0"):
        self.user_agent = user_agent
        self.cache = RadioCache()
        self.favorites = FavoritesManager()

    def _enum_cache_value(self, value: Any) -> str:
        return str(getattr(value, "value", value))

    def _coerce_order(self, value: Any) -> Order:
        if isinstance(value, Order):
            return value
        if isinstance(value, str):
            try:
                return Order(value)
            except Exception:
                pass
            try:
                return Order[value]
            except Exception:
                pass
        return Order.NAME

    def _coerce_filter_by(self, value: Any) -> FilterBy:
        if isinstance(value, FilterBy):
            return value
        if isinstance(value, str):
            try:
                return FilterBy(value)
            except Exception:
                pass
            try:
                return FilterBy[value]
            except Exception:
                pass
        raise ValueError(f"Unsupported filter_by value: {value}")

    async def get_stats(self, use_cache: bool = True) -> Stats:
        if use_cache and self.cache.is_valid("stats"):
            cached = self.cache.load("stats")
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            stats = await rb.stats()
        
        self.cache.save("stats", stats)
        return stats

    async def get_countries(self, use_cache: bool = True, **kwargs) -> List[Country]:
        order = self._coerce_order(kwargs.get('order', Order.NAME))
        cache_key = f"{self._enum_cache_value(order)}_{kwargs.get('reverse', False)}"
        
        if use_cache and self.cache.is_valid("countries", cache_key):
            cached = self.cache.load("countries", cache_key)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            countries = await rb.countries(
                order=order,
                reverse=kwargs.get('reverse', False),
                hide_broken=kwargs.get('hide_broken', False),
                limit=kwargs.get('limit', 100000),
                offset=kwargs.get('offset', 0),
            )
        
        self.cache.save("countries", countries, cache_key)
        return countries

    async def get_languages(self, use_cache: bool = True, **kwargs) -> List[Language]:
        order = self._coerce_order(kwargs.get('order', Order.NAME))
        cache_key = f"{self._enum_cache_value(order)}_{kwargs.get('reverse', False)}"
        
        if use_cache and self.cache.is_valid("languages", cache_key):
            cached = self.cache.load("languages", cache_key)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            languages = await rb.languages(
                order=order,
                reverse=kwargs.get('reverse', False),
                hide_broken=kwargs.get('hide_broken', False),
                limit=kwargs.get('limit', 100000),
                offset=kwargs.get('offset', 0),
            )
        
        self.cache.save("languages", languages, cache_key)
        return languages

    async def get_tags(self, use_cache: bool = True, **kwargs) -> List[Tag]:
        order = self._coerce_order(kwargs.get('order', Order.NAME))
        cache_key = f"{self._enum_cache_value(order)}_{kwargs.get('reverse', False)}"
        
        if use_cache and self.cache.is_valid("tags", cache_key):
            cached = self.cache.load("tags", cache_key)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            tags = await rb.tags(
                order=order,
                reverse=kwargs.get('reverse', False),
                hide_broken=kwargs.get('hide_broken', False),
                limit=kwargs.get('limit', 100000),
                offset=kwargs.get('offset', 0),
            )
        
        self.cache.save("tags", tags, cache_key)
        return tags

    async def search_stations(self, use_cache: bool = True, **kwargs) -> List[Station]:
        name = kwargs.get('name', '')
        country = kwargs.get('country', '')
        order = self._coerce_order(kwargs.get('order', Order.NAME))
        cache_key = f"{name}_{country}_{self._enum_cache_value(order)}"
        
        if use_cache and self.cache.is_valid("search", cache_key):
            cached = self.cache.load("search", cache_key)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            search_params = {
                'name': kwargs.get('name'),
                'country': kwargs.get('country'),
                'order': order,
                'reverse': kwargs.get('reverse', False),
                'limit': kwargs.get('limit', 100000),
                'offset': kwargs.get('offset', 0),
                'hide_broken': kwargs.get('hide_broken', False),
            }
            valid_params = {k: v for k, v in search_params.items() if v}
            stations = await rb.search(**valid_params)
        
        self.cache.save("search", stations, cache_key)
        return stations

    async def get_stations_by_filter(self, filter_by: FilterBy, filter_term: str, 
                                    use_cache: bool = True, **kwargs) -> List[Station]:
        filter_by = self._coerce_filter_by(filter_by)
        order = self._coerce_order(kwargs.get('order', Order.NAME))
        cache_key = f"{self._enum_cache_value(filter_by)}_{filter_term}_{self._enum_cache_value(order)}"
        
        if use_cache and self.cache.is_valid("filter", cache_key):
            cached = self.cache.load("filter", cache_key)
            if cached:
                return cached
        
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            stations = await rb.stations(
                filter_by=filter_by,
                filter_term=filter_term,
                order=order,
                reverse=kwargs.get('reverse', False),
                limit=kwargs.get('limit', 100000),
                offset=kwargs.get('offset', 0),
                hide_broken=kwargs.get('hide_broken', False),
            )
        
        self.cache.save("filter", stations, cache_key)
        return stations

    async def get_station_by_uuid(self, uuid: str) -> Optional[Station]:
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            stations = await rb.stations(filter_by=FilterBy.UUID, filter_term=uuid)
            return stations[0] if stations else None

    async def click_station(self, uuid: str) -> None:
        async with RadioBrowser(user_agent=self.user_agent) as rb:
            await rb.station_click(uuid=uuid)

    def add_favorite(self, station_data: Dict[str, Any]) -> None:
        self.favorites.add(station_data)

    def remove_favorite(self, uuid: str) -> None:
        self.favorites.remove(uuid)

    def is_favorite(self, uuid: str) -> bool:
        return self.favorites.is_favorite(uuid)

    def get_favorites(self) -> List[Dict[str, Any]]:
        return self.favorites.get_all()

    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        self.cache.clear(cache_type)

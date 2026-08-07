import asyncio
from typing import List, Optional, Dict, Any

import httpx
import pycountry
from media_core.pyradios.radios import RadioBrowser as _PyRadiosClient
from media_providers.radio.radio_browser_types import (
    Country,
    FilterBy,
    Language,
    Order,
    RadioBrowserConnectionError,
    RadioBrowserConnectionTimeoutError,
    RadioBrowserError,
    Station,
    Stats,
    Tag,
)
from media_providers.radio.radio_cache import RadioCache
from media_providers.radio.radio_models import FavoritesManager


class RadioBrowser:
    """Async-facing wrapper around media_core.pyradios's sync RadioBrowser client."""

    def __init__(self, user_agent: str, request_timeout: float = 8.0):
        self.user_agent = user_agent
        self.request_timeout = request_timeout
        self._client: _PyRadiosClient | None = None

    async def _get_client(self) -> _PyRadiosClient:
        if self._client is None:
            def _build() -> _PyRadiosClient:
                client = _PyRadiosClient(session=httpx.Client(timeout=httpx.Timeout(self.request_timeout)))
                # pyradios' Request.get() passes this dict as the per-call headers
                # override on every request; set it directly since the RadioBrowser
                # constructor has no way to customize headers itself.
                client.client._headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
                return client

            try:
                self._client = await asyncio.to_thread(_build)
            except (httpx.HTTPError, OSError, IndexError) as exception:
                msg = "Error occurred while communicating with the Radio Browser API"
                raise RadioBrowserConnectionError(msg) from exception
        return self._client

    async def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        client = await self._get_client()
        url = client.build_url(endpoint)

        if params:
            for key, value in params.items():
                if isinstance(value, bool):
                    params[key] = str(value).lower()

        try:
            return await asyncio.to_thread(client.client.get, url, **(params or {}))
        except httpx.TimeoutException as exception:
            self._client = None
            msg = "Timeout occurred while connecting to the Radio Browser API"
            raise RadioBrowserConnectionTimeoutError(msg) from exception
        except httpx.HTTPError as exception:
            self._client = None
            msg = "Error occurred while communicating with the Radio Browser API"
            raise RadioBrowserConnectionError(msg) from exception
        except ValueError as exception:
            raise RadioBrowserError(str(exception)) from exception

    def _coerce_order(self, value):
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

    def _to_api_bool(self, value):
        return str(bool(value)).lower()

    async def stats(self) -> Stats:
        response = await self._request("json/stats")
        return Stats.from_dict(response)

    async def countries(self, **kwargs) -> list[Country]:
        order = self._coerce_order(kwargs.get('order', Order.NAME))
        params = {
            "hidebroken": self._to_api_bool(kwargs.get('hide_broken', False)),
            "limit": kwargs.get('limit', 100000),
            "offset": kwargs.get('offset', 0),
            "order": order.value,
            "reverse": self._to_api_bool(kwargs.get('reverse', False)),
        }
        countries = await self._request("json/countrycodes", params=params)
        for country in countries:
            country["code"] = country["name"]
            if country["name"] == "XK":
                country["name"] = "Kosovo"
            elif resolved_country := pycountry.countries.get(alpha_2=country["name"]):
                country["name"] = resolved_country.name
        if order == Order.NAME:
            countries.sort(key=lambda c: c["name"])
        return [Country.from_dict(c) for c in countries]

    async def languages(self, **kwargs) -> list[Language]:
        order = self._coerce_order(kwargs.get('order', Order.NAME))
        params = {
            "hidebroken": self._to_api_bool(kwargs.get('hide_broken', False)),
            "offset": kwargs.get('offset', 0),
            "order": order.value,
            "reverse": self._to_api_bool(kwargs.get('reverse', False)),
            "limit": kwargs.get('limit', 100000),
        }
        languages = await self._request("json/languages", params=params)
        for language in languages:
            language["name"] = language["name"].title()
        return [Language.from_dict(l) for l in languages]

    async def tags(self, **kwargs) -> list[Tag]:
        order = self._coerce_order(kwargs.get('order', Order.NAME))
        params = {
            "hidebroken": self._to_api_bool(kwargs.get('hide_broken', False)),
            "offset": kwargs.get('offset', 0),
            "order": order.value,
            "reverse": self._to_api_bool(kwargs.get('reverse', False)),
            "limit": kwargs.get('limit', 100000),
        }
        tags = await self._request("json/tags", params=params)
        return [Tag.from_dict(t) for t in tags]

    def _stations_uri(self, filter_by, filter_term):
        uri = "json/stations"
        if filter_by is not None:
            fbv = filter_by.value if isinstance(filter_by, FilterBy) else filter_by
            uri = f"{uri}/{fbv}"
            if filter_term is not None:
                uri = f"{uri}/{filter_term}"
        return uri

    def _stations_params(self, kwargs):
        order = self._coerce_order(kwargs.get('order', Order.NAME))
        return {
            "hidebroken": self._to_api_bool(kwargs.get('hide_broken', False)),
            "offset": kwargs.get('offset', 0),
            "order": order.value,
            "reverse": self._to_api_bool(kwargs.get('reverse', False)),
            "limit": kwargs.get('limit', 100000),
        }

    async def stations(self, **kwargs) -> list[Station]:
        uri = self._stations_uri(kwargs.get('filter_by'), kwargs.get('filter_term'))
        stations = await self._request(uri, params=self._stations_params(kwargs))
        return [Station.from_dict(s) for s in stations]

    async def search(self, **kwargs) -> list[Station]:
        filter_by = kwargs.get('filter_by')
        filter_term = kwargs.get('filter_term')
        uri = "json/stations/search"
        if filter_by is not None:
            fbv = filter_by.value if isinstance(filter_by, FilterBy) else filter_by
            uri = f"{uri}/{fbv}"
            if filter_term is not None:
                uri = f"{uri}/{filter_term}"
        params = self._stations_params(kwargs)
        params.update({
            "name": kwargs.get('name'),
            "name_exact": kwargs.get('name_exact', False),
            "country": kwargs.get('country'),
            "country_exact": kwargs.get('country_exact', False),
            "state_exact": kwargs.get('state_exact', False),
            "language_exact": kwargs.get('language_exact', False),
            "tag_exact": kwargs.get('tag_exact', False),
            "bitrate_min": kwargs.get('bitrate_min', 0),
            "bitrate_max": kwargs.get('bitrate_max', 1000000),
        })
        params = {k: v for k, v in params.items() if v is not None}
        stations = await self._request(uri, params=params)
        return [Station.from_dict(s) for s in stations]

    async def station_click(self, *, uuid: str) -> None:
        await self._request(f"json/url/{uuid}")

    async def close(self) -> None:
        client = self._client
        self._client = None
        if client is not None:
            client.client._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.close()


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

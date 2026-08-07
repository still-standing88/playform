"""Local replacements for the (now removed) `radios` PyPI package's public
surface: its `FilterBy`/`Order` enums, its `Station`/`Country`/`Language`/
`Tag`/`Stats` dataclasses, and its exception types. Kept field-for-field
compatible so radio_widget.py/radio_tree_widget.py/radio_filter_widget.py
don't need to change - only radio_service.py's transport layer does, since
it now talks to media_core.pyradios instead of the old aiohttp-based client.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional, cast

import pycountry


class RadioBrowserError(Exception):
    """Generic Radio Browser exception."""


class RadioBrowserConnectionError(RadioBrowserError):
    """Radio Browser connection exception."""


class RadioBrowserConnectionTimeoutError(RadioBrowserConnectionError):
    """Radio Browser connection timeout exception."""


class Order(str, Enum):
    """Enum holding the order types."""

    BITRATE = "bitrate"
    CHANGE_TIMESTAMP = "changetimestamp"
    CLICK_COUNT = "clickcount"
    CLICK_TIMESTAMP = "clicktimestamp"
    CLICK_TREND = "clicktrend"
    CODE = "code"
    CODEC = "codec"
    COUNTRY = "country"
    FAVICON = "favicon"
    HOMEPAGE = "homepage"
    LANGUAGE = "language"
    LAST_CHECK_OK = "lastcheckok"
    LAST_CHECK_TIME = "lastchecktime"
    NAME = "name"
    RANDOM = "random"
    STATE = "state"
    STATION_COUNT = "stationcount"
    TAGS = "tags"
    URL = "url"
    VOTES = "votes"


class FilterBy(str, Enum):
    """Enum holding possible filter by types for radio stations."""

    UUID = "byuuid"
    NAME = "byname"
    NAME_EXACT = "bynameexact"
    CODEC = "bycodec"
    CODEC_EXACT = "bycodecexact"
    COUNTRY = "bycountry"
    COUNTRY_EXACT = "bycountryexact"
    COUNTRY_CODE_EXACT = "bycountrycodeexact"
    STATE = "bystate"
    STATE_EXACT = "bystateexact"
    LANGUAGE = "bylanguage"
    LANGUAGE_EXACT = "bylanguageexact"
    TAG = "bytag"
    TAG_EXACT = "bytagexact"


def _split_csv(value: Any) -> list[str]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    return [item.strip() for item in str(value).split(",")]


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass
class Stats:
    """Object holding the Radio Browser stats."""

    supported_version: int
    software_version: str
    status: str
    stations: int
    stations_broken: int
    tags: int
    clicks_last_hour: int
    clicks_last_day: int
    languages: int
    countries: int

    @classmethod
    def from_dict(cls, data: dict) -> "Stats":
        return cls(
            supported_version=data.get("supported_version", 0),
            software_version=str(data.get("software_version", "")),
            status=data.get("status", ""),
            stations=data.get("stations", 0),
            stations_broken=data.get("stations_broken", 0),
            tags=data.get("tags", 0),
            clicks_last_hour=data.get("clicks_last_hour", 0),
            clicks_last_day=data.get("clicks_last_day", 0),
            languages=data.get("languages", 0),
            countries=data.get("countries", 0),
        )


@dataclass
class Station:
    """Object information for a station from the Radio Browser."""

    bitrate: int
    change_uuid: str
    click_count: int
    click_timestamp: Optional[datetime]
    click_trend: int
    codec: str
    country_code: str
    favicon: str
    latitude: Optional[float]
    longitude: Optional[float]
    has_extended_info: bool
    hls: bool
    homepage: str
    iso_3166_2: Optional[str]
    language: list[str]
    language_codes: list[str]
    lastchange_time: Optional[datetime]
    lastcheckok: bool
    last_check_ok_time: Optional[datetime]
    last_check_time: Optional[datetime]
    last_local_check_time: Optional[datetime]
    name: str
    ssl_error: int
    state: str
    uuid: str
    tags: list[str]
    url_resolved: str
    url: str
    votes: int

    @property
    def country(self) -> Optional[str]:
        """Return country name of this station."""
        if resolved_country := pycountry.countries.get(alpha_2=self.country_code):
            return cast(str, resolved_country.name)
        return None

    @classmethod
    def from_dict(cls, data: dict) -> "Station":
        return cls(
            bitrate=data.get("bitrate", 0),
            change_uuid=data.get("changeuuid", ""),
            click_count=data.get("clickcount", 0),
            click_timestamp=_parse_datetime(data.get("clicktimestamp_iso8601")),
            click_trend=data.get("clicktrend", 0),
            codec=data.get("codec", ""),
            country_code=data.get("countrycode", ""),
            favicon=data.get("favicon", ""),
            latitude=data.get("geo_lat"),
            longitude=data.get("geo_long"),
            has_extended_info=bool(data.get("has_extended_info", False)),
            hls=bool(data.get("hls", False)),
            homepage=data.get("homepage", ""),
            iso_3166_2=data.get("iso_3166_2"),
            language=_split_csv(data.get("language")),
            language_codes=_split_csv(data.get("languagecodes")),
            lastchange_time=_parse_datetime(data.get("lastchangetime_iso8601")),
            lastcheckok=bool(data.get("lastcheckok", False)),
            last_check_ok_time=_parse_datetime(data.get("lastcheckoktime_iso8601")),
            last_check_time=_parse_datetime(data.get("lastchecktime_iso8601")),
            last_local_check_time=_parse_datetime(data.get("lastlocalchecktime_iso8601")),
            name=data.get("name", ""),
            ssl_error=data.get("ssl_error", 0),
            state=data.get("state", ""),
            uuid=data.get("stationuuid", ""),
            tags=_split_csv(data.get("tags")),
            url_resolved=data.get("url_resolved", ""),
            url=data.get("url", ""),
            votes=data.get("votes", 0),
        )


@dataclass
class Country:
    """Object information for a country from the Radio Browser."""

    code: str
    name: str
    station_count: str

    @property
    def favicon(self) -> str:
        return f"https://flagcdn.com/256x192/{self.code.lower()}.png"

    @classmethod
    def from_dict(cls, data: dict) -> "Country":
        return cls(
            code=data.get("code", ""),
            name=data.get("name", ""),
            station_count=str(data.get("stationcount", "0")),
        )


@dataclass
class Language:
    """Object information for a language from the Radio Browser."""

    code: Optional[str]
    name: str
    station_count: str

    @property
    def favicon(self) -> Optional[str]:
        if self.code:
            return f"https://flagcdn.com/256x192/{self.code.lower()}.png"
        return None

    @classmethod
    def from_dict(cls, data: dict) -> "Language":
        return cls(
            code=data.get("iso_639"),
            name=data.get("name", ""),
            station_count=str(data.get("stationcount", "0")),
        )


@dataclass
class Tag:
    """Object information for a tag from the Radio Browser."""

    name: str
    station_count: str

    @classmethod
    def from_dict(cls, data: dict) -> "Tag":
        return cls(
            name=data.get("name", ""),
            station_count=str(data.get("stationcount", "0")),
        )

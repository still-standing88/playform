"""Persists which AnnouncementCategory values are enabled for speech output
(see signal_manager.announce() / gui.main_window._on_categorized_message).
Backed by app_settings (user.sqlite3) -- everything defaults to enabled so
existing behavior is unchanged until the user opts a category out via
Preferences -> Accessibility -> Announcements."""

import logging

from utilities.announcement_categories import AnnouncementCategory

SETTINGS_KEY = "announcement_categories_enabled"


def get_enabled_map() -> dict:
    try:
        from app_db import app_settings
        data = app_settings.get(SETTINGS_KEY, {})
        return data if isinstance(data, dict) else {}
    except Exception:
        logging.exception("announcement_settings.get_enabled_map failed; treating everything as enabled")
        return {}


def is_category_enabled(category_value: str) -> bool:
    return get_enabled_map().get(category_value, True)


def set_category_enabled(category_value: str, enabled: bool) -> None:
    try:
        from app_db import app_settings
        enabled_map = get_enabled_map()
        enabled_map[category_value] = enabled
        app_settings.set(SETTINGS_KEY, enabled_map)
    except Exception:
        logging.exception("announcement_settings.set_category_enabled failed")


def set_enabled_map(enabled_map: dict) -> None:
    try:
        from app_db import app_settings
        app_settings.set(SETTINGS_KEY, dict(enabled_map))
    except Exception:
        logging.exception("announcement_settings.set_enabled_map failed")

"""Taxonomy for speech-announcement filtering (see signal_manager.announce()
and gui.dialogs.announcement_settings_dialog). Every status-bar message
that should also be *speakable* gets tagged with one of these categories at
its call site, so the user can enable/disable speech per category via a
checkable tree in Preferences -> Accessibility without losing the status
bar text (which always shows regardless of the speech setting).
"""

from enum import Enum


class AnnouncementCategory(Enum):
    PLAYBACK = "playback"
    EXPLORER = "explorer"
    PLAYLISTS = "playlists"
    TOOLS = "tools"
    DIALOGS = "dialogs"
    DOWNLOADS = "downloads"
    DATABASE = "database"
    PODCASTS_RADIO = "podcasts_radio"
    SUBTITLES = "subtitles"
    CAPTURE = "capture"
    GENERAL = "general"


def category_label(category: "AnnouncementCategory") -> str:
    labels = {
        AnnouncementCategory.PLAYBACK: _("Playback"),
        AnnouncementCategory.EXPLORER: _("File Explorer"),
        AnnouncementCategory.PLAYLISTS: _("Playlists"),
        AnnouncementCategory.TOOLS: _("Tools"),
        AnnouncementCategory.DIALOGS: _("Dialogs & Windows"),
        AnnouncementCategory.DOWNLOADS: _("Downloads"),
        AnnouncementCategory.DATABASE: _("Database & Cataloging"),
        AnnouncementCategory.PODCASTS_RADIO: _("Podcasts & Radio"),
        AnnouncementCategory.SUBTITLES: _("Subtitles"),
        AnnouncementCategory.CAPTURE: _("Multi Device Capture"),
        AnnouncementCategory.GENERAL: _("General"),
    }
    return labels.get(category, category.value)

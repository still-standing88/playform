"""Domain model for the Multi Device Capture panel.

Ported from the standalone capture_module.py prototype. Kept Qt-light on
purpose (only `MediaType.is_video` cares about video-vs-audio, nothing here
touches QtMultimedia directly) so registries/settings/engine can all import
it without pulling in a QApplication.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class MediaType(Enum):
    AUDIO_INPUT = auto()
    AUDIO_OUTPUT = auto()
    CAMERA = auto()
    MONITOR = auto()
    WINDOW = auto()

    @property
    def label(self) -> str:
        return {
            MediaType.AUDIO_INPUT: _("Audio input"),
            MediaType.AUDIO_OUTPUT: _("Audio output"),
            MediaType.CAMERA: _("Camera"),
            MediaType.MONITOR: _("Monitor"),
            MediaType.WINDOW: _("Window"),
        }[self]

    @property
    def is_video(self) -> bool:
        return self in (MediaType.CAMERA, MediaType.MONITOR, MediaType.WINDOW)

    @property
    def is_audio(self) -> bool:
        return self in (MediaType.AUDIO_INPUT, MediaType.AUDIO_OUTPUT)


def new_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class CaptureSource:
    """One configured capture source. Lives in the source pool, independent
    of any session. Sessions reference sources by id."""
    id: str
    friendly_name: str
    media_type: MediaType
    device_id: str = ""            # QAudioDevice.id() / QCameraDevice.id(), bytes->str
    window_description: str = ""   # only for MediaType.WINDOW - window handles
                                    # aren't stable across relaunches, so we key
                                    # on the description shown at pick-time instead
    settings: dict = field(default_factory=dict)
    enabled: bool = True

    def status_text(self) -> str:
        if self.media_type in (MediaType.AUDIO_INPUT, MediaType.AUDIO_OUTPUT):
            rate = self.settings.get("sample_rate", "?")
            ch = self.settings.get("channels", "?")
            return f"{rate} Hz - {ch} ch"
        if self.media_type == MediaType.CAMERA:
            res = self.settings.get("resolution", "?")
            fps = self.settings.get("fps", "?")
            return f"{res} @ {fps}fps"
        if self.media_type == MediaType.MONITOR:
            return self.settings.get("screen_name", "")
        if self.media_type == MediaType.WINDOW:
            return self.window_description
        return ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "friendly_name": self.friendly_name,
            "media_type": self.media_type.name,
            "device_id": self.device_id,
            "window_description": self.window_description,
            "settings": self.settings,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CaptureSource":
        return cls(
            id=data["id"],
            friendly_name=data.get("friendly_name", ""),
            media_type=MediaType[data["media_type"]],
            device_id=data.get("device_id", ""),
            window_description=data.get("window_description", ""),
            settings=dict(data.get("settings", {})),
            enabled=data.get("enabled", True),
        )


@dataclass
class Session:
    """A saved capture configuration. Stores its own settings snapshot for
    any field it overrides; anything not overridden resolves against the
    global Settings tab at capture-start time."""
    id: str
    name: str
    source_ids: list[str] = field(default_factory=list)
    output_dir: str = ""
    container_format: str = "mkv"
    settings_override: Optional[dict] = None  # None => fully inherits globals

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "source_ids": list(self.source_ids),
            "output_dir": self.output_dir,
            "container_format": self.container_format,
            "settings_override": self.settings_override,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            source_ids=list(data.get("source_ids", [])),
            output_dir=data.get("output_dir", ""),
            container_format=data.get("container_format", "mkv"),
            settings_override=data.get("settings_override"),
        )

"""Domain model for the Multi Device Capture panel.

Thin Qt-facing layer over media_core.av_capture.models: MediaType is the
same MediaKind enum the ffmpeg engine uses (so a source's `media_type` can
be handed straight to CaptureCapabilities/CaptureSessionRunner with no
translation step), with a translated `.label` lookup and is_video/is_audio
helpers added here rather than on MediaKind itself, since media_core stays
Qt/gettext-free.
"""
from __future__ import annotations

from typing import Optional

from media_core.av_capture.models import (
    AUDIO_KINDS,
    VIDEO_KINDS,
    CaptureSessionConfig,
    CaptureSourceConfig,
    MediaKind,
    new_id,
)

MediaType = MediaKind

_LABELS = {
    MediaType.AUDIO_INPUT: lambda: _("Audio input"),
    MediaType.AUDIO_OUTPUT: lambda: _("Audio output"),
    MediaType.CAMERA: lambda: _("Camera"),
    MediaType.MONITOR: lambda: _("Monitor"),
    MediaType.WINDOW: lambda: _("Window"),
}


def media_type_label(media_type: MediaType) -> str:
    return _LABELS[media_type]()


def is_video(media_type: MediaType) -> bool:
    return media_type in VIDEO_KINDS


def is_audio(media_type: MediaType) -> bool:
    return media_type in AUDIO_KINDS


class CaptureSource(CaptureSourceConfig):
    """CaptureSourceConfig plus a UI-only `status_text()` summary and a
    `media_type`/`window_description` alias pair kept for source
    compatibility with the previous QtMultimedia-era field names."""

    def __init__(self, id: str, friendly_name: str, media_type: MediaType, device_id: str = "",
                 window_description: str = "", settings: Optional[dict] = None, enabled: bool = True):
        super().__init__(
            id=id, friendly_name=friendly_name, kind=media_type, device_id=device_id,
            device_name=window_description, settings=settings or {}, enabled=enabled,
        )

    @property
    def media_type(self) -> MediaType:
        return self.kind

    @media_type.setter
    def media_type(self, value: MediaType) -> None:
        self.kind = value

    @property
    def window_description(self) -> str:
        return self.device_name

    @window_description.setter
    def window_description(self, value: str) -> None:
        self.device_name = value

    def status_text(self) -> str:
        if self.media_type in AUDIO_KINDS:
            rate = self.settings.get("sample_rate", "?")
            ch = self.settings.get("channels", "?")
            return f"{rate} Hz - {ch} ch"
        if self.media_type == MediaType.CAMERA:
            res = self.settings.get("resolution", "?")
            fps = self.settings.get("fps", "?")
            return f"{res} @ {fps}fps"
        if self.media_type == MediaType.MONITOR:
            return self.device_name
        if self.media_type == MediaType.WINDOW:
            return self.window_description
        return ""

    @classmethod
    def from_dict(cls, data: dict) -> "CaptureSource":
        return cls(
            id=data["id"],
            friendly_name=data.get("friendly_name", ""),
            media_type=MediaType[data["media_type"]] if "media_type" in data else MediaType[data["kind"]],
            device_id=data.get("device_id", ""),
            window_description=data.get("window_description", data.get("device_name", "")),
            settings=dict(data.get("settings", {})),
            enabled=data.get("enabled", True),
        )

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


class Session(CaptureSessionConfig):
    """CaptureSessionConfig with the previous `container_format` field name
    kept as the public attribute (persisted JSON already uses it)."""

    def __init__(self, id: str, name: str, source_ids: Optional[list] = None, output_dir: str = "",
                 container_format: str = "mkv", settings_override: Optional[dict] = None):
        super().__init__(
            id=id, name=name, source_ids=source_ids or [], output_dir=output_dir,
            container=container_format, settings_override=settings_override,
        )

    @property
    def container_format(self) -> str:
        return self.container

    @container_format.setter
    def container_format(self, value: str) -> None:
        self.container = value

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            source_ids=list(data.get("source_ids", [])),
            output_dir=data.get("output_dir", ""),
            container_format=data.get("container_format", data.get("container", "mkv")),
            settings_override=data.get("settings_override"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "source_ids": list(self.source_ids),
            "output_dir": self.output_dir,
            "container_format": self.container_format,
            "settings_override": self.settings_override,
        }


__all__ = ["CaptureSource", "MediaType", "Session", "is_audio", "is_video", "media_type_label", "new_id"]

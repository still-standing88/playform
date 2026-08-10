"""Domain model for the ffmpeg-based capture engine.

Deliberately Qt-light (no PySide6 import, no `_()` translation calls) so
capabilities/backends/session_runner can all import it without pulling in a
QApplication - translation of labels for display is the Qt wrapper layer's
job (multi_device_capture/), same split as
media_core.m4b_tools/media_core.ffmpeg vs. their tools/ wrappers.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class MediaKind(Enum):
    AUDIO_INPUT = auto()
    AUDIO_OUTPUT = auto()
    CAMERA = auto()
    MONITOR = auto()
    WINDOW = auto()


VIDEO_KINDS = (MediaKind.CAMERA, MediaKind.MONITOR, MediaKind.WINDOW)
AUDIO_KINDS = (MediaKind.AUDIO_INPUT, MediaKind.AUDIO_OUTPUT)


def new_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass(frozen=True)
class CaptureDevice:
    """One device/window/monitor as enumerated by the platform backend,
    using ffmpeg's own device-listing mechanism wherever ffmpeg provides one
    (dshow -list_devices, avfoundation -list_devices, v4l2 sysfs names) and
    the platform's native tool where it doesn't (gdigrab has no window
    listing of its own, so Windows window enumeration goes through
    EnumWindows; x11grab has none either, so Linux goes through wmctrl).

    `id` is whatever value command_builder needs to plug into the ffmpeg
    input url/options for *this* backend - it is not a display string. For
    dshow that's the device's "Alternative name" (@device_... - stable
    across friendly-name collisions and renames); for a Windows window it's
    the HWND; for a monitor it's "x,y,w,h"; for avfoundation/v4l2 it's the
    device index/node ffmpeg expects.
    """

    kind: MediaKind
    id: str
    name: str
    backend: str = ""  # "dshow" | "gdigrab" | "avfoundation" | "v4l2" | "x11grab" | "pulse" | "alsa"
    extra: dict = field(default_factory=dict)
    loopback_hint: bool = False
    """True when this device was enumerated as a normal input but is known
    or likely to actually carry system audio output - a PulseAudio
    `.monitor` source, or a dshow/ALSA device whose name matches a common
    virtual-cable/stereo-mix pattern. Purely informational for the UI; the
    capture path is identical to any other audio input either way."""


@dataclass
class CaptureFormatOption:
    """One (resolution, frame rate[, codec/pixel format]) combination a
    camera device actually reported via `-list_options true` (dshow),
    `-list_formats all` (v4l2), or the avfoundation pixel-format list -
    never guessed."""

    width: int
    height: int
    fps: float
    codec: str = ""          # dshow "vcodec=..." (e.g. "mjpeg"), else ""
    pixel_format: str = ""   # dshow/v4l2/avfoundation raw pixel format, if reported

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"


@dataclass
class CaptureSourceConfig:
    """One configured capture source. Lives in the source pool, independent
    of any session - a session references sources by id rather than owning
    them."""

    id: str
    friendly_name: str
    kind: MediaKind
    device_id: str = ""
    device_name: str = ""
    settings: dict = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "friendly_name": self.friendly_name,
            "kind": self.kind.name,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "settings": self.settings,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CaptureSourceConfig":
        return cls(
            id=data["id"],
            friendly_name=data.get("friendly_name", ""),
            kind=MediaKind[data["kind"]],
            device_id=data.get("device_id", ""),
            device_name=data.get("device_name", ""),
            settings=dict(data.get("settings", {})),
            enabled=data.get("enabled", True),
        )


@dataclass
class CaptureSessionConfig:
    """A saved capture configuration. Stores its own settings snapshot for
    any field it overrides; anything not overridden resolves against global
    defaults at capture-start time."""

    id: str
    name: str
    source_ids: list[str] = field(default_factory=list)
    output_dir: str = ""
    container: str = "mkv"
    settings_override: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "source_ids": list(self.source_ids),
            "output_dir": self.output_dir,
            "container": self.container,
            "settings_override": self.settings_override,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CaptureSessionConfig":
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            source_ids=list(data.get("source_ids", [])),
            output_dir=data.get("output_dir", ""),
            container=data.get("container", data.get("container_format", "mkv")),
            settings_override=data.get("settings_override"),
        )

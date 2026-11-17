from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Self


class MediaKind(Enum):
    AUDIO_INPUT = auto()
    AUDIO_OUTPUT = auto()
    CAMERA = auto()
    MONITOR = auto()
    WINDOW = auto()
    AUDIO_PROCESS = auto()
    AUDIO_MIX = auto()


VIDEO_KINDS = (MediaKind.CAMERA, MediaKind.MONITOR, MediaKind.WINDOW)
AUDIO_KINDS = (MediaKind.AUDIO_INPUT, MediaKind.AUDIO_OUTPUT, MediaKind.AUDIO_PROCESS, MediaKind.AUDIO_MIX)
VIDEO_CONTAINERS = ("mkv", "mp4", "webm")
AUDIO_CONTAINERS = ("m4a", "wav", "flac", "mp3", "opus")
DEFAULT_VIDEO_FORMAT = "mkv"
DEFAULT_AUDIO_FORMAT = "wav"


def output_formats(audio=None, video=None, legacy=None) -> dict[str, str]:
    if legacy == "mov":
        legacy = "mp4"
    audio_default = legacy if legacy in AUDIO_CONTAINERS else DEFAULT_AUDIO_FORMAT
    video_default = legacy if legacy in VIDEO_CONTAINERS else DEFAULT_VIDEO_FORMAT
    return {
        "audio_format": audio if audio in AUDIO_CONTAINERS else audio_default,
        "video_format": video if video in VIDEO_CONTAINERS else video_default,
    }


def new_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass(frozen=True)
class CaptureDevice:

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
    id: str
    name: str
    source_ids: list[str] = field(default_factory=list)
    output_dir: str = ""
    audio_format: str = DEFAULT_AUDIO_FORMAT
    video_format: str = DEFAULT_VIDEO_FORMAT
    settings_override: Optional[dict] = None

    def __post_init__(self) -> None:
        formats = output_formats(self.audio_format, self.video_format)
        self.audio_format = formats["audio_format"]
        self.video_format = formats["video_format"]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "source_ids": list(self.source_ids),
            "output_dir": self.output_dir,
            "audio_format": self.audio_format,
            "video_format": self.video_format,
            "settings_override": self.settings_override,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            source_ids=list(data.get("source_ids", [])),
            output_dir=data.get("output_dir", ""),
            settings_override=data.get("settings_override"),
            **output_formats(
                data.get("audio_format"), data.get("video_format"),
                data.get("container_format") or data.get("container"),
            ),
        )

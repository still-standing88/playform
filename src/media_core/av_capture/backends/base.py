"""Per-platform capture backend interface.

One backend == one platform's ffmpeg avdevice mechanism. Every method must
answer from what is actually detected right now (installed ffmpeg build,
connected devices, running desktop session) - never a hardcoded guess, per
the same "central place that answers can this platform offer X right now"
rule the previous QtMultimedia-based platform_capabilities.py followed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from media_core.av_capture.models import CaptureDevice, CaptureFormatOption, MediaKind


@dataclass
class InputSpec:
    """Everything command_builder needs to add one ffmpeg -i for a source:
    the input url/name ffmpeg expects for this backend's demuxer, the
    per-input options dict (video_size=, framerate=, sample_rate=, ...), and
    the demuxer name itself (`-f <format>`)."""

    format: str
    url: str
    options: dict = field(default_factory=dict)


class CaptureBackend:
    """Abstract per-platform backend. Concrete backends only need to
    override what they can actually support - unsupported kinds simply
    return an empty list / False, which the UI turns into an honest
    empty-state rather than a fake control."""

    name = "base"

    def __init__(self, ffmpeg_executable: str = "ffmpeg"):
        self.ffmpeg_executable = ffmpeg_executable

    # -- availability -------------------------------------------------

    def demuxer_available(self, demuxer: str) -> bool:
        """Whether the running ffmpeg build actually has this avdevice
        demuxer compiled in (`ffmpeg -devices`) - a custom/minimal ffmpeg
        build may lack dshow/gdigrab/v4l2/x11grab/pulse entirely, and we
        must not offer a type we can't actually open."""
        raise NotImplementedError

    def supported_kinds(self) -> set:
        """Which MediaKinds are structurally possible on this platform with
        this ffmpeg build - independent of whether any device currently
        exists for them (capabilities.available_kinds() handles the
        transient-empty vs. permanently-impossible distinction on top of
        this)."""
        return set()

    # -- enumeration ----------------------------------------------------

    def list_audio_inputs(self) -> list[CaptureDevice]:
        return []

    def list_audio_outputs(self) -> list[CaptureDevice]:
        return []

    def list_cameras(self) -> list[CaptureDevice]:
        return []

    def list_monitors(self) -> list[CaptureDevice]:
        return []

    def list_windows(self) -> list[CaptureDevice]:
        return []

    def camera_formats(self, device: CaptureDevice) -> list[CaptureFormatOption]:
        return []

    # -- capability notes (surfaced verbatim in the UI) ------------------

    def loopback_supported(self) -> bool:
        return False

    def loopback_note(self) -> str:
        return "Recording system audio output is not supported on this platform/ffmpeg build."

    def window_capture_supported(self) -> bool:
        return False

    def window_capture_note(self) -> str:
        return "Window capture is not supported on this platform/ffmpeg build."

    def screen_capture_note(self) -> str:
        return ""

    # -- command building -------------------------------------------------

    def build_input(self, kind: MediaKind, device: CaptureDevice, settings: dict) -> Optional[InputSpec]:
        """Build the ffmpeg `-f <format> [options] -i <url>` for one source.
        Returns None if the kind/device combination can't be captured (the
        caller reports that as a per-source error, same as a vanished
        device)."""
        raise NotImplementedError

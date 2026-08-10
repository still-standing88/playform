"""macOS capture backend: avfoundation, grounded in the ffmpeg-devices manual
section 3.3 (see archive/docs/ffmpeg-manuals/ffmpeg-devices/3-input-devices/
avfoundation.md). avfoundation is the one backend where ffmpeg itself
enumerates cameras *and* screens *and* microphones in a single
`-list_devices true` call - no platform-native enumeration needed at all.

avfoundation has no per-window capture device (only whole-screen "Capture
screen N" entries) and no loopback/system-audio-output device, so Window and
Audio-output stay honestly unsupported here rather than faking a path -
same posture as the previous QtMultimedia module took for these.
"""
from __future__ import annotations

import re
from typing import Optional

from media_core.av_capture.backends.base import CaptureBackend, InputSpec
from media_core.av_capture.device_probe import run_probe
from media_core.av_capture.models import CaptureDevice, MediaKind

_SECTION_LINE = re.compile(r"AVFoundation (?P<section>video|audio) devices:")
_DEVICE_LINE = re.compile(r"\[(?P<index>\d+)\]\s+(?P<name>.+?)\s*$")
_LOOPBACK_NAME_HINTS = ("blackhole", "soundflower", "loopback")


class MacOSBackend(CaptureBackend):
    name = "macos"

    def demuxer_available(self, demuxer: str) -> bool:
        result = run_probe([self.ffmpeg_executable, "-hide_banner", "-devices"], timeout=6.0)
        return result.ok and bool(re.search(rf"\b{re.escape(demuxer)}\b", result.text))

    def supported_kinds(self) -> set:
        if not self.demuxer_available("avfoundation"):
            return set()
        return {MediaKind.AUDIO_INPUT, MediaKind.CAMERA, MediaKind.MONITOR}

    def _list_devices(self) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
        result = run_probe(
            [self.ffmpeg_executable, "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
            timeout=8.0,
        )
        video: list[tuple[int, str]] = []
        audio: list[tuple[int, str]] = []
        section: Optional[str] = None
        for line in result.text.splitlines():
            section_match = _SECTION_LINE.search(line)
            if section_match:
                section = section_match.group("section")
                continue
            device_match = _DEVICE_LINE.search(line)
            if device_match and section:
                entry = (int(device_match.group("index")), device_match.group("name"))
                (video if section == "video" else audio).append(entry)
        return video, audio

    def list_cameras(self) -> list[CaptureDevice]:
        video, _ = self._list_devices()
        return [
            CaptureDevice(kind=MediaKind.CAMERA, id=str(idx), name=name, backend="avfoundation")
            for idx, name in video if not name.lower().startswith("capture screen")
        ]

    def list_monitors(self) -> list[CaptureDevice]:
        video, _ = self._list_devices()
        return [
            CaptureDevice(kind=MediaKind.MONITOR, id=str(idx), name=name, backend="avfoundation")
            for idx, name in video if name.lower().startswith("capture screen")
        ]

    def list_audio_inputs(self) -> list[CaptureDevice]:
        _, audio = self._list_devices()
        return [
            CaptureDevice(
                kind=MediaKind.AUDIO_INPUT, id=str(idx), name=name, backend="avfoundation",
                loopback_hint=any(h in name.lower() for h in _LOOPBACK_NAME_HINTS),
            )
            for idx, name in audio
        ]

    def list_audio_outputs(self) -> list[CaptureDevice]:
        return []

    def loopback_supported(self) -> bool:
        return False

    def loopback_note(self) -> str:
        return (
            "macOS has no built-in loopback capture device in avfoundation. Install a "
            "virtual audio device (e.g. BlackHole) and pick it as an 'Audio input' "
            "source instead - it will be flagged as a likely loopback route."
        )

    def window_capture_supported(self) -> bool:
        return False

    def window_capture_note(self) -> str:
        return "avfoundation only exposes whole displays ('Capture screen N'), not individual windows."

    def screen_capture_note(self) -> str:
        return ""

    def build_input(self, kind: MediaKind, device: CaptureDevice, settings: dict) -> Optional[InputSpec]:
        options: dict = {}
        if settings.get("fps"):
            options["framerate"] = str(settings["fps"])
        if settings.get("resolution"):
            options["video_size"] = settings["resolution"]
        if settings.get("capture_cursor") is not None:
            options["capture_cursor"] = "1" if settings.get("capture_cursor") else "0"

        if kind in (MediaKind.CAMERA, MediaKind.MONITOR):
            return InputSpec(format="avfoundation", url=f"{device.id}:none", options=options)
        if kind == MediaKind.AUDIO_INPUT:
            options = {}
            return InputSpec(format="avfoundation", url=f"none:{device.id}", options=options)
        return None

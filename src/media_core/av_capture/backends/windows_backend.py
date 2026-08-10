"""Windows capture backend: dshow (camera + audio input) and gdigrab
(desktop/window), grounded in the ffmpeg-devices manual sections 3.5 (dshow)
and 3.7 (gdigrab) - see archive/docs/ffmpeg-manuals/ffmpeg-devices/
3-input-devices/{dshow,gdigrab}.md.

ffmpeg's Windows build has no WASAPI/loopback avdevice (confirmed against
the bundled bin/ffmpeg.exe: `-devices` lists only dshow/gdigrab/vfwcap/
lavfi), so "Audio output" capture is genuinely unavailable here rather than
just unimplemented - loopback_supported() reports that honestly instead of
faking a working path. A dshow audio device that already routes system
output (VB-Audio Cable, Stereo Mix, VoiceMeeter, ...) still shows up as a
perfectly normal audio *input* device and is flagged via
CaptureDevice.loopback_hint so the UI can point the user at it.
"""
from __future__ import annotations

import re
from typing import Optional

from media_core.av_capture.backends.base import CaptureBackend, InputSpec
from media_core.av_capture.device_probe import run_probe
from media_core.av_capture.models import CaptureDevice, CaptureFormatOption, MediaKind

_LOOPBACK_NAME_HINTS = (
    "cable", "stereo mix", "virtual", "voicemeeter", "loopback", "what u hear", "wave out mix",
)

_DEVICE_LINE = re.compile(r'"(?P<name>[^"]+)"\s+\((?P<kind>video|audio)\)')
_ALT_NAME_LINE = re.compile(r'Alternative name\s+"(?P<alt>[^"]+)"')
_FORMAT_LINE = re.compile(
    r"(?P<key>vcodec|pixel_format)=(?P<value>\S+)\s+min s=\d+x\d+ fps=[\d.]+\s+"
    r"max s=(?P<w>\d+)x(?P<h>\d+) fps=(?P<fps>[\d.]+)"
)


def _looks_like_loopback(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in _LOOPBACK_NAME_HINTS)


class WindowsBackend(CaptureBackend):
    name = "windows"

    def __init__(self, ffmpeg_executable: str = "ffmpeg"):
        super().__init__(ffmpeg_executable)
        self._devices_text_cache: Optional[str] = None

    # -- availability -------------------------------------------------

    def demuxer_available(self, demuxer: str) -> bool:
        result = run_probe([self.ffmpeg_executable, "-hide_banner", "-devices"], timeout=6.0)
        if not result.ok:
            return False
        return bool(re.search(rf"\b{re.escape(demuxer)}\b", result.text))

    def supported_kinds(self) -> set:
        kinds = set()
        if self.demuxer_available("dshow"):
            kinds |= {MediaKind.AUDIO_INPUT, MediaKind.CAMERA}
            if self.loopback_supported():
                kinds.add(MediaKind.AUDIO_OUTPUT)
        if self.demuxer_available("gdigrab"):
            kinds.add(MediaKind.MONITOR)
            if self.window_capture_supported():
                kinds.add(MediaKind.WINDOW)
        return kinds

    # -- dshow enumeration ------------------------------------------------

    def _dshow_list(self) -> str:
        if self._devices_text_cache is None:
            result = run_probe(
                [self.ffmpeg_executable, "-hide_banner", "-f", "dshow", "-list_devices", "true", "-i", "dummy"],
                timeout=8.0,
            )
            self._devices_text_cache = result.text
        return self._devices_text_cache

    def refresh(self) -> None:
        """Devices can appear/disappear (USB mic unplugged, camera driver
        reinitializing) while a panel is open - callers refresh explicitly
        rather than this class silently re-probing on every call, since
        dshow enumeration takes a real ffmpeg process spin-up (a few hundred
        ms to ~1s)."""
        self._devices_text_cache = None

    def _dshow_devices(self) -> list[tuple[str, str, str]]:
        """Returns (name, alt_name, kind) tuples, kind in {"video","audio"}."""
        text = self._dshow_list()
        devices = []
        pending: Optional[tuple[str, str]] = None
        for line in text.splitlines():
            match = _DEVICE_LINE.search(line)
            if match:
                if pending:
                    devices.append((pending[0], pending[0], pending[1]))
                pending = (match.group("name"), match.group("kind"))
                continue
            alt_match = _ALT_NAME_LINE.search(line)
            if alt_match and pending:
                devices.append((pending[0], alt_match.group("alt"), pending[1]))
                pending = None
        if pending:
            devices.append((pending[0], pending[0], pending[1]))
        return devices

    def list_cameras(self) -> list[CaptureDevice]:
        return [
            CaptureDevice(kind=MediaKind.CAMERA, id=alt, name=name, backend="dshow")
            for name, alt, kind in self._dshow_devices()
            if kind == "video"
        ]

    def list_audio_inputs(self) -> list[CaptureDevice]:
        return [
            CaptureDevice(
                kind=MediaKind.AUDIO_INPUT, id=alt, name=name, backend="dshow",
                loopback_hint=_looks_like_loopback(name),
            )
            for name, alt, kind in self._dshow_devices()
            if kind == "audio"
        ]

    def list_audio_outputs(self) -> list[CaptureDevice]:
        return []  # no WASAPI loopback avdevice - see module docstring

    def camera_formats(self, device: CaptureDevice) -> list[CaptureFormatOption]:
        result = run_probe(
            [
                self.ffmpeg_executable, "-hide_banner", "-f", "dshow",
                "-list_options", "true", "-i", f'video="{device.id}"',
            ],
            timeout=8.0,
        )
        formats = []
        seen = set()
        for line in result.text.splitlines():
            match = _FORMAT_LINE.search(line)
            if not match:
                continue
            key = (match.group("w"), match.group("h"), match.group("fps"), match.group("key"), match.group("value"))
            if key in seen:
                continue
            seen.add(key)
            formats.append(CaptureFormatOption(
                width=int(match.group("w")),
                height=int(match.group("h")),
                fps=float(match.group("fps")),
                codec=match.group("value") if match.group("key") == "vcodec" else "",
                pixel_format=match.group("value") if match.group("key") == "pixel_format" else "",
            ))
        return formats

    # -- gdigrab: monitors / windows ------------------------------------

    def list_monitors(self) -> list[CaptureDevice]:
        try:
            from media_core.av_capture.backends import _win32_enum
        except Exception:
            return []
        devices = []
        for index, mon in enumerate(_win32_enum.enum_monitors()):
            w, h = mon["right"] - mon["left"], mon["bottom"] - mon["top"]
            label = f"Monitor {index + 1} ({w}x{h}){' - primary' if mon['primary'] else ''}"
            devices.append(CaptureDevice(
                kind=MediaKind.MONITOR,
                id=f"{mon['left']},{mon['top']},{w},{h}",
                name=label,
                backend="gdigrab",
                extra={"x": mon["left"], "y": mon["top"], "w": w, "h": h, "primary": mon["primary"]},
            ))
        return devices

    def list_windows(self) -> list[CaptureDevice]:
        try:
            from media_core.av_capture.backends import _win32_enum
        except Exception:
            return []
        devices = []
        for hwnd, title in _win32_enum.enum_windows():
            devices.append(CaptureDevice(
                kind=MediaKind.WINDOW, id=str(hwnd), name=title, backend="gdigrab",
                extra={"hwnd": hwnd, "title": title},
            ))
        return devices

    # -- notes -------------------------------------------------------

    def loopback_supported(self) -> bool:
        return False

    def loopback_note(self) -> str:
        return (
            "Recording system/application audio output requires WASAPI loopback, which "
            "this ffmpeg build's dshow input does not expose (no 'wasapi' entry in "
            "`ffmpeg -devices`). If a virtual audio device (VB-Audio Cable, VoiceMeeter, "
            "Stereo Mix) is installed, add it as an 'Audio input' source instead - it "
            "captures the same signal and is flagged as a likely loopback route in the "
            "device list."
        )

    def window_capture_supported(self) -> bool:
        return True

    def window_capture_note(self) -> str:
        return ""

    def screen_capture_note(self) -> str:
        return ""

    # -- command building -------------------------------------------------

    def build_input(self, kind: MediaKind, device: CaptureDevice, settings: dict) -> Optional[InputSpec]:
        if kind == MediaKind.CAMERA:
            options = {}
            resolution = settings.get("resolution")
            fps = settings.get("fps")
            if resolution:
                options["video_size"] = resolution
            if fps:
                options["framerate"] = str(fps)
            pixel_format = settings.get("pixel_format")
            if pixel_format:
                options["pixel_format"] = pixel_format
            return InputSpec(format="dshow", url=f'video="{device.id}"', options=options)

        if kind == MediaKind.AUDIO_INPUT:
            options = {}
            if settings.get("sample_rate"):
                options["sample_rate"] = str(settings["sample_rate"])
            if settings.get("channels"):
                options["channels"] = str(settings["channels"])
            return InputSpec(format="dshow", url=f'audio="{device.id}"', options=options)

        if kind == MediaKind.MONITOR:
            options = {"framerate": str(settings.get("fps") or 30)}
            if settings.get("capture_cursor") is not None:
                options["draw_mouse"] = "1" if settings.get("capture_cursor") else "0"
            x, y, w, h = device.extra.get("x", 0), device.extra.get("y", 0), device.extra.get("w"), device.extra.get("h")
            if w and h:
                options["offset_x"] = str(x)
                options["offset_y"] = str(y)
                options["video_size"] = f"{w}x{h}"
            return InputSpec(format="gdigrab", url="desktop", options=options)

        if kind == MediaKind.WINDOW:
            options = {"framerate": str(settings.get("fps") or 30)}
            if settings.get("capture_cursor") is not None:
                options["draw_mouse"] = "1" if settings.get("capture_cursor") else "0"
            hwnd = device.extra.get("hwnd", device.id)
            return InputSpec(format="gdigrab", url=f"hwnd={hwnd}", options=options)

        return None

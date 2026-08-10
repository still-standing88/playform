"""Linux capture backend: v4l2 (camera), x11grab (desktop/window), pulse
with alsa fallback (audio) - grounded in the ffmpeg-devices manual sections
3.18 (v4l2), 3.20 (x11grab), 3.16 (pulse) and 3.1 (alsa); see
archive/docs/ffmpeg-manuals/ffmpeg-devices/3-input-devices/.

None of v4l2/x11grab/pulse/alsa have a `-list_devices` of their own the way
dshow/avfoundation do, so enumeration goes through the exact external tools
those manual pages themselves point at: `pactl list sources` (the pulse
manual's own suggestion) and X11's own `xrandr`/`wmctrl` (in the spirit of
the x11grab manual's `xdpyinfo`/`xwininfo` pointers - wmctrl gives window
*titles* directly, which xwininfo does not without a manual click). Sysfs
(`/sys/class/video4linux/*/name`) supplies camera friendly names, since v4l2
itself only exposes a `/dev/videoN` node.
"""
from __future__ import annotations

import glob
import os
import re
from typing import Optional

from media_core.av_capture.backends.base import CaptureBackend, InputSpec
from media_core.av_capture.device_probe import run_probe, tool_available
from media_core.av_capture.models import CaptureDevice, CaptureFormatOption, MediaKind

_RESOLUTION_TOKEN = re.compile(r"\b(\d{2,5})x(\d{2,5})\b")
_PIXFMT_LINE = re.compile(r"^\s*\[\d+\]\s*'(?P<fourcc>[^']+)'\s*:\s*(?P<desc>.+)$")
_XRANDR_LINE = re.compile(
    r"^(?P<name>\S+)\s+connected\s+(?P<primary>primary\s+)?(?P<w>\d+)x(?P<h>\d+)\+(?P<x>\d+)\+(?P<y>\d+)"
)
_WMCTRL_LINE = re.compile(r"^(?P<id>0x[0-9a-fA-F]+)\s+-?\d+\s+\S+\s+(?P<title>.+)$")


class LinuxBackend(CaptureBackend):
    name = "linux"

    def demuxer_available(self, demuxer: str) -> bool:
        result = run_probe([self.ffmpeg_executable, "-hide_banner", "-devices"], timeout=6.0)
        return result.ok and bool(re.search(rf"\b{re.escape(demuxer)}\b", result.text))

    def supported_kinds(self) -> set:
        kinds = set()
        if self.demuxer_available("v4l2"):
            kinds.add(MediaKind.CAMERA)
        if self.demuxer_available("x11grab"):
            kinds.add(MediaKind.MONITOR)
            if self.window_capture_supported():
                kinds.add(MediaKind.WINDOW)
        if self.demuxer_available("pulse") or self.demuxer_available("alsa"):
            kinds.add(MediaKind.AUDIO_INPUT)
        if self.loopback_supported():
            kinds.add(MediaKind.AUDIO_OUTPUT)
        return kinds

    # -- v4l2 cameras -----------------------------------------------------

    def list_cameras(self) -> list[CaptureDevice]:
        devices = []
        for node in sorted(glob.glob("/dev/video*")):
            name = self._v4l2_name(node) or os.path.basename(node)
            devices.append(CaptureDevice(kind=MediaKind.CAMERA, id=node, name=f"{name} ({node})", backend="v4l2"))
        return devices

    @staticmethod
    def _v4l2_name(node: str) -> str:
        sysfs_name = f"/sys/class/video4linux/{os.path.basename(node)}/name"
        try:
            with open(sysfs_name, "r", encoding="utf-8", errors="replace") as handle:
                return handle.read().strip()
        except OSError:
            return ""

    def camera_formats(self, device: CaptureDevice) -> list[CaptureFormatOption]:
        result = run_probe(
            [self.ffmpeg_executable, "-hide_banner", "-f", "v4l2", "-list_formats", "all", "-i", device.id],
            timeout=8.0,
        )
        formats = []
        seen = set()
        current_pixfmt = ""
        for line in result.text.splitlines():
            fmt_match = _PIXFMT_LINE.search(line)
            if fmt_match:
                current_pixfmt = fmt_match.group("fourcc")
            for w, h in _RESOLUTION_TOKEN.findall(line):
                key = (current_pixfmt, w, h)
                if key in seen:
                    continue
                seen.add(key)
                # v4l2's -list_formats output does not pair a frame rate with
                # each resolution (that needs a separate per-size query this
                # backend does not perform) - fps is left at 0, meaning
                # "let the device use its own default" (see build_input()).
                formats.append(CaptureFormatOption(width=int(w), height=int(h), fps=0, pixel_format=current_pixfmt))
        return formats

    # -- x11grab: monitors / windows ------------------------------------

    def list_monitors(self) -> list[CaptureDevice]:
        if not tool_available("xrandr"):
            return []
        result = run_probe(["xrandr", "--query"], timeout=5.0)
        if not result.ok:
            return []
        devices = []
        for line in result.stdout.splitlines():
            match = _XRANDR_LINE.match(line.strip())
            if not match:
                continue
            x, y, w, h = int(match.group("x")), int(match.group("y")), int(match.group("w")), int(match.group("h"))
            label = f"{match.group('name')} ({w}x{h}){' - primary' if match.group('primary') else ''}"
            devices.append(CaptureDevice(
                kind=MediaKind.MONITOR, id=f"{x},{y},{w},{h}", name=label, backend="x11grab",
                extra={"x": x, "y": y, "w": w, "h": h, "primary": bool(match.group("primary"))},
            ))
        return devices

    def list_windows(self) -> list[CaptureDevice]:
        if not tool_available("wmctrl"):
            return []
        result = run_probe(["wmctrl", "-l"], timeout=5.0)
        if not result.ok:
            return []
        devices = []
        for line in result.stdout.splitlines():
            match = _WMCTRL_LINE.match(line.strip())
            if not match:
                continue
            devices.append(CaptureDevice(
                kind=MediaKind.WINDOW, id=match.group("id"), name=match.group("title").strip(), backend="x11grab",
                extra={"window_id": int(match.group("id"), 16)},
            ))
        return devices

    def window_capture_supported(self) -> bool:
        return tool_available("wmctrl")

    def window_capture_note(self) -> str:
        if tool_available("wmctrl"):
            return ""
        return "Window capture needs the 'wmctrl' utility to list window ids for x11grab; install it and refresh."

    def screen_capture_note(self) -> str:
        if not tool_available("xrandr"):
            return "Install 'xrandr' to list individual monitors; falling back to the primary X11 display otherwise."
        return ""

    # -- audio: pulse (with real loopback) or alsa fallback ---------------

    def _pulse_sources(self) -> Optional[list[dict]]:
        if not tool_available("pactl"):
            return None
        result = run_probe(["pactl", "list", "short", "sources"], timeout=5.0)
        if not result.ok:
            return None
        sources = []
        for line in result.stdout.splitlines():
            columns = line.split("\t")
            if len(columns) < 2:
                continue
            sources.append({"index": columns[0], "name": columns[1]})
        return sources

    def list_audio_inputs(self) -> list[CaptureDevice]:
        sources = self._pulse_sources()
        if sources is not None:
            return [
                CaptureDevice(kind=MediaKind.AUDIO_INPUT, id=s["name"], name=s["name"], backend="pulse")
                for s in sources if not s["name"].endswith(".monitor")
            ]
        return self._alsa_cards()

    def list_audio_outputs(self) -> list[CaptureDevice]:
        sources = self._pulse_sources()
        if sources is None:
            return []  # alsa fallback has no generic loopback source enumeration
        return [
            CaptureDevice(kind=MediaKind.AUDIO_OUTPUT, id=s["name"], name=s["name"], backend="pulse")
            for s in sources if s["name"].endswith(".monitor")
        ]

    @staticmethod
    def _alsa_cards() -> list[CaptureDevice]:
        try:
            with open("/proc/asound/cards", "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            return []
        devices = []
        for match in re.finditer(r"^\s*(\d+)\s+\[(\S+?)\s*\]:\s*(.+)$", text, re.MULTILINE):
            index, short_name, description = match.groups()
            devices.append(CaptureDevice(
                kind=MediaKind.AUDIO_INPUT, id=f"hw:{index}", name=f"{description.strip()} ({short_name})",
                backend="alsa", loopback_hint="loopback" in description.lower(),
            ))
        return devices

    def loopback_supported(self) -> bool:
        return self._pulse_sources() is not None

    def loopback_note(self) -> str:
        if self._pulse_sources() is not None:
            return ""
        return (
            "System-audio-output capture needs PulseAudio/PipeWire's pulse compatibility "
            "layer (a sink's '.monitor' source) - install/enable it, or add an ALSA "
            "loopback ('snd-aloop') card as an 'Audio input' source instead."
        )

    # -- command building -------------------------------------------------

    def build_input(self, kind: MediaKind, device: CaptureDevice, settings: dict) -> Optional[InputSpec]:
        if kind == MediaKind.CAMERA:
            options = {}
            if settings.get("resolution"):
                options["video_size"] = settings["resolution"]
            if settings.get("fps"):
                options["framerate"] = str(settings["fps"])
            if settings.get("pixel_format"):
                options["pixel_format"] = settings["pixel_format"]
            return InputSpec(format="v4l2", url=device.id, options=options)

        if kind in (MediaKind.AUDIO_INPUT, MediaKind.AUDIO_OUTPUT):
            if device.backend == "alsa":
                options = {}
                if settings.get("sample_rate"):
                    options["sample_rate"] = str(settings["sample_rate"])
                return InputSpec(format="alsa", url=device.id, options=options)
            options = {}
            if settings.get("sample_rate"):
                options["sample_rate"] = str(settings["sample_rate"])
            if settings.get("channels"):
                options["channels"] = str(settings["channels"])
            return InputSpec(format="pulse", url=device.id, options=options)

        if kind == MediaKind.MONITOR:
            display = os.environ.get("DISPLAY", ":0")
            x, y = device.extra.get("x", 0), device.extra.get("y", 0)
            options = {"framerate": str(settings.get("fps") or 25)}
            if settings.get("capture_cursor") is not None:
                options["draw_mouse"] = "1" if settings.get("capture_cursor") else "0"
            w, h = device.extra.get("w"), device.extra.get("h")
            if w and h:
                options["video_size"] = f"{w}x{h}"
            return InputSpec(format="x11grab", url=f"{display}+{x},{y}", options=options)

        if kind == MediaKind.WINDOW:
            display = os.environ.get("DISPLAY", ":0")
            options = {
                "framerate": str(settings.get("fps") or 25),
                "window_id": str(device.extra.get("window_id", device.id)),
            }
            if settings.get("capture_cursor") is not None:
                options["draw_mouse"] = "1" if settings.get("capture_cursor") else "0"
            return InputSpec(format="x11grab", url=display, options=options)

        return None

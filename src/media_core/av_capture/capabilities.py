"""Single entry point that answers "what can this machine capture right
now" - UI and session_runner code should always ask here rather than
assuming, since the real answer depends on the platform, the installed
ffmpeg build's compiled-in avdevices, and which devices/windows/monitors
are actually attached/open at this moment.

Mirrors the role the previous QtMultimedia-based
multi_device_capture.platform_capabilities.PlatformCapabilities played, but
every answer now traces back to an actual ffmpeg (or ffmpeg-doc-recommended
platform tool) invocation instead of a Qt Multimedia API call - see
backends/ for the per-platform grounding.
"""
from __future__ import annotations

from typing import Optional

from media_core.av_capture.backends import create_backend
from media_core.av_capture.models import AUDIO_KINDS, VIDEO_KINDS, CaptureDevice, CaptureFormatOption, MediaKind

# Kinds worth offering as a selectable *type* even with zero devices
# enumerated right now - both are prone to transient-empty results in a way
# audio/monitor essentially never are on a real machine (camera enumeration
# can lag driver/hot-plug init; window capture depends on some window
# actually being open). The UI shows an empty-state + Refresh for these
# instead of hiding the type outright.
_ALWAYS_OFFERED_IF_STRUCTURALLY_POSSIBLE = (MediaKind.CAMERA, MediaKind.WINDOW)


class CaptureCapabilities:
    def __init__(self, ffmpeg_executable: str = "ffmpeg"):
        self.ffmpeg_executable = ffmpeg_executable
        self._backend = create_backend(ffmpeg_executable)

    @property
    def backend(self):
        return self._backend

    def refresh(self) -> None:
        """Devices can appear/disappear while a panel is open - callers
        refresh explicitly rather than every call silently re-probing,
        since device enumeration means spinning up a real ffmpeg/platform
        process."""
        refresh = getattr(self._backend, "refresh", None)
        if callable(refresh):
            refresh()

    # -- kind/device enumeration ------------------------------------------

    def available_kinds(self) -> list[MediaKind]:
        supported = self._backend.supported_kinds()
        kinds = []
        for kind in (MediaKind.AUDIO_INPUT, MediaKind.AUDIO_OUTPUT, MediaKind.CAMERA, MediaKind.MONITOR, MediaKind.WINDOW):
            if kind not in supported:
                continue
            if kind in _ALWAYS_OFFERED_IF_STRUCTURALLY_POSSIBLE:
                kinds.append(kind)
            elif self.list_devices(kind):
                kinds.append(kind)
        return kinds

    def list_devices(self, kind: MediaKind) -> list[CaptureDevice]:
        if kind == MediaKind.AUDIO_INPUT:
            return self._backend.list_audio_inputs()
        if kind == MediaKind.AUDIO_OUTPUT:
            return self._backend.list_audio_outputs()
        if kind == MediaKind.CAMERA:
            return self._backend.list_cameras()
        if kind == MediaKind.MONITOR:
            return self._backend.list_monitors()
        if kind == MediaKind.WINDOW:
            return self._backend.list_windows()
        return []

    def find_device(self, kind: MediaKind, device_id: str) -> Optional[CaptureDevice]:
        for device in self.list_devices(kind):
            if device.id == device_id:
                return device
        return None

    def camera_formats(self, device: CaptureDevice) -> list[CaptureFormatOption]:
        return self._backend.camera_formats(device)

    # -- capability notes --------------------------------------------------

    def loopback_supported(self) -> bool:
        return self._backend.loopback_supported()

    def loopback_note(self) -> str:
        return self._backend.loopback_note()

    def window_capture_supported(self) -> bool:
        return self._backend.window_capture_supported()

    def window_capture_note(self) -> str:
        return self._backend.window_capture_note()

    def screen_capture_note(self) -> str:
        return self._backend.screen_capture_note()

    @staticmethod
    def is_video(kind: MediaKind) -> bool:
        return kind in VIDEO_KINDS

    @staticmethod
    def is_audio(kind: MediaKind) -> bool:
        return kind in AUDIO_KINDS

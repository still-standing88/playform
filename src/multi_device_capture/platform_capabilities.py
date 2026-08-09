"""Central place that answers 'can this platform/device offer capture X right
now'. UI and engine code should always ask here rather than assuming - Qt
Multimedia's actual capability surface varies a lot by OS and backend, and
guessing produces controls that look real but silently do nothing.
"""
from __future__ import annotations

import glob
import os
import platform as _platform
from typing import Optional


def _select_ffmpeg_backend_if_available() -> None:
    """QWindowCapture is only implemented by Qt Multimedia's FFmpeg backend -
    on every native backend (the default on Windows/macOS) it silently
    enumerates zero windows forever, which is exactly the "window capture
    devices exist but never show up" symptom. Must run before the first real
    QtMultimedia call (backend plugins load lazily on first use, not on
    import), which is why this module - the one thing everything else in
    this package funnels device queries through - does it at import time,
    before its own QtMultimedia import below.

    Only forces the switch if the ffmpeg plugin is actually present next to
    this install and the caller/environment hasn't already picked a backend;
    a strip-installed PySide6 without the plugin would otherwise lose every
    backend, not just gain window capture.
    """
    if os.environ.get("QT_MEDIA_BACKEND"):
        return
    try:
        import PySide6

        plugin_dir = os.path.join(os.path.dirname(PySide6.__file__), "plugins", "multimedia")
        has_ffmpeg_plugin = bool(glob.glob(os.path.join(plugin_dir, "*ffmpeg*")))
    except Exception:
        has_ffmpeg_plugin = False
    if has_ffmpeg_plugin:
        os.environ["QT_MEDIA_BACKEND"] = "ffmpeg"


_select_ffmpeg_backend_if_available()

from PySide6.QtGui import QGuiApplication
from PySide6.QtMultimedia import (
    QAudioDevice,
    QCameraDevice,
    QCapturableWindow,
    QMediaDevices,
    QWindowCapture,
)

from .models import MediaType

CURRENT_OS = _platform.system()  # "Windows" / "Darwin" / "Linux"


class PlatformCapabilities:
    """Device/type enumeration plus platform-specific gating.

    None of this caches: every call re-queries QMediaDevices/QGuiApplication,
    since devices can appear/disappear (USB mic unplugged, external monitor
    detached, capturable window closed) while the panel is open.
    """

    # -- raw enumeration ---------------------------------------------------

    @staticmethod
    def audio_inputs() -> list[QAudioDevice]:
        return list(QMediaDevices.audioInputs())

    @staticmethod
    def audio_outputs() -> list[QAudioDevice]:
        return list(QMediaDevices.audioOutputs())

    @staticmethod
    def cameras() -> list[QCameraDevice]:
        return list(QMediaDevices.videoInputs())

    @staticmethod
    def screens():
        return list(QGuiApplication.screens())

    @staticmethod
    def capturable_windows() -> list[QCapturableWindow]:
        # Empty on backends/platforms where QWindowCapture isn't supported
        # (non-FFmpeg Qt Multimedia backend, or a Wayland compositor without
        # portal support). We don't try to distinguish "not supported" from
        # "no windows open" - either way there's nothing to offer.
        try:
            return list(QWindowCapture.capturableWindows())
        except Exception:
            return []

    @classmethod
    def available_types(cls) -> list[MediaType]:
        """Types to offer in the Add Source wizard's Type dropdown.

        Camera and Window are always offered, even with zero devices
        currently enumerated: both are prone to transient/empty results in a
        way Audio/Monitor essentially never are on a real machine - camera
        enumeration can lag behind driver/hot-plug init, and window capture
        depends on the active Qt Multimedia backend actually implementing it
        (see _select_ffmpeg_backend_if_available() above). Hiding the type
        outright when that first query came back empty left no way to even
        retry; the wizard now shows an empty-state + Refresh instead. Audio/
        Monitor stay gated on actually having ≥1 device, since a genuinely
        input-device-less or headless machine has nothing real to offer there.
        """
        available = []
        if cls.audio_inputs():
            available.append(MediaType.AUDIO_INPUT)
        if cls.audio_outputs():
            available.append(MediaType.AUDIO_OUTPUT)
        available.append(MediaType.CAMERA)
        if cls.screens():
            available.append(MediaType.MONITOR)
        available.append(MediaType.WINDOW)
        return available

    # -- platform-specific gating ------------------------------------------

    @classmethod
    def loopback_capture_supported(cls) -> bool:
        """Whether 'Audio output' sources can actually be *recorded*, not
        just listed.

        Qt Multimedia's public API has no loopback-recording primitive on
        any platform: QMediaDevices.audioOutputs() enumerates playback sinks,
        but QMediaCaptureSession.setAudioInput() only accepts an *input*-mode
        QAudioDevice. Recording what a speaker is playing needs a
        platform-native loopback path:
          - Windows: WASAPI loopback (IAudioClient with
            AUDCLNT_STREAMFLAGS_LOOPBACK), not exposed by QtMultimedia.
          - macOS: no built-in loopback; requires a virtual audio device
            (e.g. BlackHole) that then shows up as a normal input.
          - Linux/PulseAudio: the monitor source of a sink shows up as a
            regular input device, so it's technically reachable through
            QMediaDevices.audioInputs() rather than audioOutputs().
        We report False everywhere rather than faking a working path; the
        engine surfaces this as a per-source error instead of silently
        producing a silent/empty recording.
        """
        return False

    @classmethod
    def loopback_capture_note(cls) -> str:
        if CURRENT_OS == "Windows":
            return _(
                "Recording system/application audio output requires WASAPI loopback, "
                "which is not exposed by Qt Multimedia's public API. Select the PulseAudio-"
                "style monitor source is not applicable on Windows; use an 'Audio input' "
                "source instead (e.g. 'Stereo Mix' if your driver exposes one)."
            )
        if CURRENT_OS == "Darwin":
            return _(
                "macOS has no built-in loopback capture. Install a virtual audio device "
                "(e.g. BlackHole) and pick it as an 'Audio input' source instead."
            )
        if CURRENT_OS == "Linux":
            return _(
                "On PulseAudio/PipeWire, a sink's monitor source is usually listed under "
                "'Audio input' rather than 'Audio output' - pick it there instead."
            )
        return _("Loopback capture of audio output is not supported through Qt Multimedia.")

    @classmethod
    def window_capture_note(cls) -> str:
        return _(
            "Window capture requires Qt Multimedia's FFmpeg backend and may be "
            "unavailable depending on platform/compositor (e.g. Wayland without "
            "portal support)."
        )

    @classmethod
    def screen_capture_note(cls) -> str:
        return _(
            "Qt Multimedia does not expose cursor capture, crop, or a frame-rate cap "
            "for screen capture through this API."
        )

    @staticmethod
    def device_identity(dev: QAudioDevice | QCameraDevice) -> str:
        """Stable id string for a device, used for persistence and for
        re-matching a device across app restarts (device order in
        QMediaDevices is not guaranteed stable)."""
        return bytes(dev.id()).decode(errors="replace")

    @classmethod
    def find_audio_device(cls, device_id: str, is_input: bool) -> Optional[QAudioDevice]:
        pool = cls.audio_inputs() if is_input else cls.audio_outputs()
        for dev in pool:
            if cls.device_identity(dev) == device_id:
                return dev
        return None

    @classmethod
    def find_camera_device(cls, device_id: str) -> Optional[QCameraDevice]:
        for dev in cls.cameras():
            if cls.device_identity(dev) == device_id:
                return dev
        return None

    @classmethod
    def find_screen(cls, name: str):
        for scr in cls.screens():
            if scr.name() == name:
                return scr
        return None

    @classmethod
    def find_capturable_window(cls, description: str) -> Optional[QCapturableWindow]:
        for win in cls.capturable_windows():
            if win.description() == description:
                return win
        return None

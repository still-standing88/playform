"""Multi-device capture engine.

Unlike media_core.ffmpeg.conversion_job.ConversionRunner (which shells out to
an ffmpeg subprocess and can therefore run its blocking loop on a worker
QThread), QCamera/QScreenCapture/QWindowCapture/QMediaRecorder are live Qt
Multimedia objects driven by the Qt event loop and are not meant to be
constructed off the GUI thread. So this engine is Qt-native by necessity: it
depends on QtMultimedia and emits Qt signals, but nothing from tabs/, dialogs/,
or app_config - a tab/dialog widget drives it, not the other way around.

One CaptureSource == one QMediaCaptureSession + QMediaRecorder pair, so a
session with N enabled sources records N files in parallel (a "multi-device"
capture is literally N independent single-device captures started/paused/
stopped together).
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import (
    QAudioInput,
    QCamera,
    QMediaCaptureSession,
    QMediaFormat,
    QMediaRecorder,
    QScreenCapture,
    QWindowCapture,
)

from .models import CaptureSource, MediaType, Session
from .platform_capabilities import PlatformCapabilities

_CONTAINER_TO_FILE_FORMAT = {
    "mkv": QMediaFormat.FileFormat.Matroska,
    "mp4": QMediaFormat.FileFormat.MPEG4,
    "mov": QMediaFormat.FileFormat.QuickTime,
}


def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", name).strip()
    return cleaned or "source"


class _SourceRuntime:
    __slots__ = (
        "source", "capture_session", "recorder", "camera",
        "screen_capture", "window_capture", "audio_input", "output_path",
    )

    def __init__(self, source: CaptureSource):
        self.source = source
        self.capture_session: Optional[QMediaCaptureSession] = None
        self.recorder: Optional[QMediaRecorder] = None
        self.camera: Optional[QCamera] = None
        self.screen_capture: Optional[QScreenCapture] = None
        self.window_capture: Optional[QWindowCapture] = None
        self.audio_input: Optional[QAudioInput] = None
        self.output_path: str = ""


class CaptureEngine(QObject):
    source_started = Signal(str, str)     # source_id, output_path
    source_error = Signal(str, str)       # source_id, message
    source_stopped = Signal(str)          # source_id
    duration_changed = Signal(str, int)   # source_id, milliseconds
    state_changed = Signal(str)           # "idle" | "recording" | "paused" | "stopped"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._runtimes: dict[str, _SourceRuntime] = {}
        self._active = False
        self._paused = False

    def is_active(self) -> bool:
        return self._active

    def is_paused(self) -> bool:
        return self._paused

    # -- transport -----------------------------------------------------

    def start(self, session: Session, sources: list[CaptureSource]) -> bool:
        if self._active:
            return False
        self._teardown()

        output_dir = session.output_dir or os.getcwd()
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as exc:
            self.source_error.emit("", _("Could not create output directory: {error}").format(error=exc))
            return False

        started_any = False
        for source in sources:
            if not source.enabled:
                continue
            runtime = self._build_runtime(source, output_dir, session.container_format)
            if runtime is None:
                continue
            self._runtimes[source.id] = runtime
            try:
                runtime.recorder.record()
                started_any = True
                self.source_started.emit(source.id, runtime.output_path)
            except Exception as exc:
                self.source_error.emit(source.id, str(exc))

        if not started_any:
            self._teardown()
            return False

        self._active = True
        self._paused = False
        self.state_changed.emit("recording")
        return True

    def pause(self) -> None:
        if not self._active or self._paused:
            return
        for runtime in self._runtimes.values():
            if runtime.recorder is not None:
                try:
                    runtime.recorder.pause()
                except Exception:
                    pass
        self._paused = True
        self.state_changed.emit("paused")

    def resume(self) -> None:
        if not self._active or not self._paused:
            return
        for runtime in self._runtimes.values():
            if runtime.recorder is not None:
                try:
                    runtime.recorder.record()
                except Exception:
                    pass
        self._paused = False
        self.state_changed.emit("recording")

    def stop(self) -> None:
        if not self._active:
            return
        for source_id, runtime in self._runtimes.items():
            if runtime.recorder is not None:
                try:
                    runtime.recorder.stop()
                except Exception:
                    pass
            self.source_stopped.emit(source_id)
        self._teardown()
        self._active = False
        self._paused = False
        self.state_changed.emit("stopped")

    # -- per-source setup ------------------------------------------------

    def _build_runtime(self, source: CaptureSource, output_dir: str, container_format: str) -> Optional[_SourceRuntime]:
        if source.media_type == MediaType.AUDIO_OUTPUT and not PlatformCapabilities.loopback_capture_supported():
            self.source_error.emit(source.id, PlatformCapabilities.loopback_capture_note())
            return None

        runtime = _SourceRuntime(source)
        runtime.capture_session = QMediaCaptureSession(self)

        try:
            if source.media_type == MediaType.AUDIO_INPUT:
                device = PlatformCapabilities.find_audio_device(source.device_id, is_input=True)
                if device is None:
                    self.source_error.emit(source.id, _("Audio input device is no longer available."))
                    return None
                runtime.audio_input = QAudioInput(device, self)
                volume = source.settings.get("volume", 100)
                runtime.audio_input.setVolume(max(0.0, min(1.0, volume / 100.0)))
                runtime.capture_session.setAudioInput(runtime.audio_input)

            elif source.media_type == MediaType.CAMERA:
                device = PlatformCapabilities.find_camera_device(source.device_id)
                if device is None:
                    self.source_error.emit(source.id, _("Camera is no longer available."))
                    return None
                runtime.camera = QCamera(device, self)
                fmt = self._match_camera_format(device, source.settings)
                if fmt is not None:
                    runtime.camera.setCameraFormat(fmt)
                runtime.capture_session.setCamera(runtime.camera)
                runtime.camera.start()

            elif source.media_type == MediaType.MONITOR:
                screen_name = source.device_id or source.settings.get("screen_name", "")
                screen = PlatformCapabilities.find_screen(screen_name)
                if screen is None:
                    self.source_error.emit(source.id, _("Monitor is no longer available."))
                    return None
                runtime.screen_capture = QScreenCapture(self)
                runtime.screen_capture.setScreen(screen)
                runtime.capture_session.setScreenCapture(runtime.screen_capture)
                runtime.screen_capture.start()

            elif source.media_type == MediaType.WINDOW:
                window = PlatformCapabilities.find_capturable_window(source.window_description)
                if window is None:
                    self.source_error.emit(
                        source.id,
                        _("Capturable window is no longer available ({note})").format(
                            note=PlatformCapabilities.window_capture_note()
                        ),
                    )
                    return None
                runtime.window_capture = QWindowCapture(self)
                runtime.window_capture.setWindow(window)
                runtime.capture_session.setWindowCapture(runtime.window_capture)
                runtime.window_capture.start()

            else:
                self.source_error.emit(source.id, _("Unsupported source type."))
                return None

        except Exception as exc:
            self.source_error.emit(source.id, str(exc))
            return None

        recorder = QMediaRecorder(self)
        file_format = _CONTAINER_TO_FILE_FORMAT.get(container_format, QMediaFormat.FileFormat.Matroska)
        media_format = QMediaFormat()
        media_format.setFileFormat(file_format)
        recorder.setMediaFormat(media_format)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = container_format if container_format in _CONTAINER_TO_FILE_FORMAT else "mkv"
        filename = f"{_sanitize_filename(source.friendly_name)}_{timestamp}.{extension}"
        output_path = os.path.join(output_dir, filename)
        recorder.setOutputLocation(QUrl.fromLocalFile(output_path))
        recorder.errorOccurred.connect(
            lambda error, error_string, sid=source.id: self.source_error.emit(sid, error_string)
        )
        recorder.durationChanged.connect(
            lambda ms, sid=source.id: self.duration_changed.emit(sid, ms)
        )

        runtime.capture_session.setRecorder(recorder)
        runtime.recorder = recorder
        runtime.output_path = output_path
        return runtime

    @staticmethod
    def _match_camera_format(device, settings: dict):
        resolution = settings.get("resolution")
        fps = settings.get("fps")
        if not resolution:
            return None
        try:
            width, height = (int(v) for v in resolution.split("x"))
        except (ValueError, AttributeError):
            return None
        best = None
        for fmt in device.videoFormats():
            res = fmt.resolution()
            if res.width() != width or res.height() != height:
                continue
            if fps and not (fmt.minFrameRate() <= fps <= fmt.maxFrameRate()):
                continue
            best = fmt
            break
        return best

    def _teardown(self) -> None:
        for runtime in self._runtimes.values():
            for obj in (runtime.camera, runtime.screen_capture, runtime.window_capture):
                if obj is not None:
                    try:
                        obj.stop()
                    except Exception:
                        pass
            for obj in (
                runtime.recorder, runtime.audio_input, runtime.camera,
                runtime.screen_capture, runtime.window_capture, runtime.capture_session,
            ):
                if obj is not None:
                    try:
                        obj.deleteLater()
                    except Exception:
                        pass
        self._runtimes.clear()

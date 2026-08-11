"""Qt wrapper around media_core.av_capture.video_preview.VideoPreviewProbe -
re-emits its plain callbacks as signals, same pattern as
dialogs/audio_level_meter.py.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from media_core.av_capture.capabilities import CaptureCapabilities
from media_core.av_capture.models import CaptureDevice, MediaKind
from media_core.av_capture.video_preview import VideoPreviewProbe


class VideoPreview(QObject):
    frame_ready = Signal(bytes)  # one complete JPEG image per frame
    error = Signal(str)

    def __init__(
        self, capabilities: CaptureCapabilities, device: CaptureDevice, kind: MediaKind,
        settings: dict | None = None, ffmpeg_executable: str = "ffmpeg", parent=None,
    ):
        super().__init__(parent)
        self._probe = VideoPreviewProbe(
            capabilities, device, kind, settings, ffmpeg_executable,
            on_frame=self.frame_ready.emit, on_error=self.error.emit,
        )

    def start(self) -> bool:
        return self._probe.start()

    def stop(self) -> None:
        self._probe.stop()

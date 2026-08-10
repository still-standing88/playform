"""Qt wrapper around media_core.av_capture.level_meter.AudioLevelProbe -
re-emits its plain callbacks as signals. See that module for why this reads
real `astats` peak-level metadata off an actual ffmpeg capture of the
device instead of a separate QAudioSource tap.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from media_core.av_capture.capabilities import CaptureCapabilities
from media_core.av_capture.level_meter import AudioLevelProbe
from media_core.av_capture.models import CaptureDevice, MediaKind


class AudioLevelMeter(QObject):
    level_changed = Signal(float)  # peak amplitude, 0.0-1.0
    error = Signal(str)

    def __init__(
        self, capabilities: CaptureCapabilities, device: CaptureDevice, kind: MediaKind,
        ffmpeg_executable: str = "ffmpeg", parent=None,
    ):
        super().__init__(parent)
        self._probe = AudioLevelProbe(
            capabilities, device, kind, ffmpeg_executable=ffmpeg_executable,
            on_level=self.level_changed.emit, on_error=self.error.emit,
        )

    def start(self) -> bool:
        return self._probe.start()

    def stop(self) -> None:
        self._probe.stop()

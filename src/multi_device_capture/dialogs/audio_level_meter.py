"""Real-time audio input level metering for the Preview page.

QAudioInput (the class QMediaCaptureSession/QMediaRecorder use for actual
recording) exposes no raw sample access - it's purely a "route this device
into a capture session" handle. Reading live PCM for a level meter needs the
lower-level QAudioSource instead, which is otherwise unrelated to the actual
recording path (this class is preview-only; engine.py never touches it).
"""
from __future__ import annotations

import struct

from PySide6.QtCore import QObject, Signal
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat, QAudioSource


class AudioLevelMeter(QObject):
    level_changed = Signal(float)  # peak amplitude, 0.0-1.0
    error = Signal(str)

    def __init__(self, device: QAudioDevice, parent=None):
        super().__init__(parent)
        fmt = QAudioFormat()
        preferred = device.preferredFormat()
        fmt.setSampleRate(preferred.sampleRate() or 44100)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(fmt):
            fmt = preferred
        self._format = fmt
        self._sample_size = 2 if fmt.sampleFormat() == QAudioFormat.SampleFormat.Int16 else 4
        self._source = QAudioSource(device, fmt, self)
        self._io = None

    def start(self) -> bool:
        try:
            self._io = self._source.start()
        except Exception as exc:
            self.error.emit(str(exc))
            return False
        if self._io is None:
            self.error.emit(_("Could not open this input device for preview."))
            return False
        self._io.readyRead.connect(self._on_ready_read)
        return True

    def stop(self) -> None:
        if self._io is not None:
            try:
                self._io.readyRead.disconnect(self._on_ready_read)
            except (RuntimeError, TypeError):
                pass
            self._io = None
        try:
            self._source.stop()
        except Exception:
            pass

    def _on_ready_read(self) -> None:
        if self._io is None:
            return
        data = bytes(self._io.readAll())
        sample_count = len(data) // self._sample_size
        if sample_count == 0:
            return
        if self._format.sampleFormat() == QAudioFormat.SampleFormat.Int16:
            samples = struct.unpack(f"<{sample_count}h", data[: sample_count * 2])
            peak = max((abs(s) for s in samples), default=0) / 32768.0
        else:
            samples = struct.unpack(f"<{sample_count}f", data[: sample_count * 4])
            peak = max((abs(s) for s in samples), default=0.0)
        self.level_changed.emit(min(1.0, peak))

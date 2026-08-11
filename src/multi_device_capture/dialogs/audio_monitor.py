"""Qt wrapper around media_core.av_capture.audio_monitor.AudioMonitorProbe.

Owns a QAudioSink for actual playback - the one narrow, deliberate
reintroduction of QtMultimedia in this module. It's a fundamentally
different use than the QCamera/QScreenCapture/QWindowCapture/QMediaRecorder
engine that got replaced by media_core.av_capture: this is raw-PCM *output*
to the system's default speaker, an area QtMultimedia was never the
problem (the migration was about its *capture* limitations - no cursor
toggle, no crop, no FPS cap, no loopback, Window capture needing a
non-default backend). ffmpeg has no local-playback avdevice on this
Windows build (`-devices` lists only dshow/gdigrab/vfwcap/lavfi, and even
where an avdevice output exists like `sdl2`/`alsa`, it plays to a device
ffmpeg opens itself, not something embeddable as "the app's own audio
output" from the outside), so this stays the practical option for "let the
user hear the mic they're about to record".
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices

from media_core.av_capture.audio_monitor import AudioMonitorProbe
from media_core.av_capture.capabilities import CaptureCapabilities
from media_core.av_capture.models import CaptureDevice


class AudioMonitor(QObject):
    level_changed = Signal(float)
    error = Signal(str)

    _pcm_ready = Signal(bytes)

    def __init__(
        self, capabilities: CaptureCapabilities, device: CaptureDevice,
        ffmpeg_executable: str = "ffmpeg", parent=None,
    ):
        super().__init__(parent)
        self._sink = None
        self._io = None
        self._probe = AudioMonitorProbe(
            capabilities, device, ffmpeg_executable,
            on_level=self.level_changed.emit, on_pcm_chunk=self._pcm_ready.emit, on_error=self.error.emit,
        )
        # PCM chunks arrive from AudioMonitorProbe's background thread -
        # writing into the QAudioSink's push-mode QIODevice must happen on
        # the thread the sink was created on (the GUI thread here), so this
        # marshals through a signal rather than writing directly from that
        # thread, same reasoning as every other cross-thread callback in
        # this package.
        self._pcm_ready.connect(self._write_chunk)

    def start(self) -> bool:
        fmt = QAudioFormat()
        fmt.setSampleRate(self._probe.sample_rate)
        fmt.setChannelCount(self._probe.channels)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        output_device = QMediaDevices.defaultAudioOutput()
        if output_device.isNull():
            self.error.emit(_("No default audio output device is available to preview through."))
            return False
        if not output_device.isFormatSupported(fmt):
            self.error.emit(_("The default audio output device does not support the preview format."))
            return False

        self._sink = QAudioSink(output_device, fmt, self)
        self._io = self._sink.start()
        if self._io is None:
            self.error.emit(_("Could not open the default audio output device for preview."))
            return False

        return self._probe.start()

    def _write_chunk(self, chunk: bytes) -> None:
        if self._io is not None:
            self._io.write(chunk)

    def stop(self) -> None:
        self._probe.stop()
        if self._sink is not None:
            try:
                self._sink.stop()
            except RuntimeError:
                pass
        self._sink = None
        self._io = None

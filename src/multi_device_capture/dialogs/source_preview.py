from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices

from media_core.av_capture.preview import CapturePreview


_IMAGE_FORMATS = {
    "bgra": QImage.Format.Format_RGB32,
    "rgba": QImage.Format.Format_RGBA8888,
    "bgr24": QImage.Format.Format_BGR888,
    "rgb24": QImage.Format.Format_RGB888,
}
_SAMPLE_FORMATS = {
    "u8": ("B", 128, 128, QAudioFormat.SampleFormat.UInt8),
    "s16le": ("h", 0, 32768, QAudioFormat.SampleFormat.Int16),
    "s32le": ("i", 0, 2147483648, QAudioFormat.SampleFormat.Int32),
    "f32le": ("f", 0, 1, QAudioFormat.SampleFormat.Float),
    "f64le": ("d", 0, 1, None),
}


class SourcePreview(QObject):
    frame_ready = Signal(QImage)
    level_changed = Signal(float)
    error = Signal(str)
    finished = Signal()
    _audio_ready = Signal(dict, bytes)

    def __init__(self, executable, device, settings, *, listen=False, parent=None):
        super().__init__(parent)
        self._listen = listen
        self._sink = None
        self._output = None
        self._running = True
        self._audio_ready.connect(self._play)
        self._capture = CapturePreview(
            executable, device, settings,
            on_frame=self._on_frame, on_error=self.error.emit, on_finished=self.finished.emit,
        )

    def start(self):
        self._capture.start()

    def stop(self):
        self._running = False
        self._capture.stop()
        if self._sink is not None:
            self._sink.stop()
            self._sink = None
            self._output = None

    def _on_frame(self, metadata, payload):
        if metadata["type"] == "video":
            fmt = _IMAGE_FORMATS.get(metadata["pixel_format"])
            if fmt is not None:
                image = QImage(payload, metadata["width"], metadata["height"],
                               metadata["planes"][0]["row_bytes"], fmt)
                if metadata["orientation"] == "bottom-up":
                    image = image.mirrored()
                self.frame_ready.emit(image.copy() if image.width() == 400 else image.scaledToWidth(400))
            return

        layout = _SAMPLE_FORMATS.get(metadata["sample_format"])
        if layout is not None:
            sample_type, center, scale, _ = layout
            samples = memoryview(payload).cast(sample_type)
            if samples:
                self.level_changed.emit(min(1.0, max(abs(min(samples) - center), abs(max(samples) - center)) / scale))
        if self._listen:
            self._audio_ready.emit(metadata, payload)

    @Slot(dict, bytes)
    def _play(self, metadata, payload):
        if not self._running or not self._listen:
            return
        if self._sink is None:
            layout = _SAMPLE_FORMATS.get(metadata["sample_format"])
            if not layout or layout[3] is None:
                self._listen = False
                return
            fmt = QAudioFormat()
            fmt.setSampleRate(metadata["sample_rate"])
            fmt.setChannelCount(metadata["channels"])
            fmt.setSampleFormat(layout[3])
            target = QMediaDevices.defaultAudioOutput()
            if not target.isFormatSupported(fmt):
                self._listen = False
                return
            self._sink = QAudioSink(target, fmt, self)
            self._output = self._sink.start()
        if self._output is not None:
            self._output.write(payload)

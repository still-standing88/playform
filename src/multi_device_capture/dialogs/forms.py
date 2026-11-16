from PySide6.QtWidgets import QComboBox, QFormLayout, QSpinBox, QWidget

from media_core.av_capture.models import MediaKind


VIDEO_SIZES = (
    "640x360", "640x480", "854x480", "960x540", "1280x720",
    "1920x1080", "2560x1440", "3840x2160",
)
VIDEO_CODECS = ("h264", "vp9", "av1")
AUDIO_CODECS = ("aac", "opus", "vorbis", "flac", "mp3", "pcm")
CAMERA_PIXEL_FORMATS = ("bgra", "bgr24", "rgba", "rgb24", "nv12", "i420")


def _number(minimum, maximum, default, suffix=""):
    widget = QSpinBox()
    widget.setRange(minimum, maximum)
    widget.setValue(default)
    widget.setSuffix(suffix)
    return widget


def _choices(default_label, default_value, values):
    widget = QComboBox()
    widget.addItem(default_label, default_value)
    for value in values:
        widget.addItem(value, value)
    return widget


def _select(widget, value, *, allow_custom=False):
    index = widget.findData(value)
    if index < 0 and allow_custom and value:
        widget.addItem(value, value)
        index = widget.count() - 1
    widget.setCurrentIndex(max(0, index))


class AudioSettingsForm(QWidget):
    def __init__(self, kind=None, microphones=(), outputs=(), parent=None):
        super().__init__(parent)
        form = QFormLayout(self)
        self.sample_rate = _number(8000, 384000, 48000, _(" Hz"))
        self.sample_rate.setSingleStep(1000)
        self.channels = QComboBox()
        self.channels.addItem(_("Mono"), 1)
        self.channels.addItem(_("Stereo"), 2)
        self.volume = _number(0, 300, 100, _(" %"))
        self.codec = _choices(_("Automatic"), "auto", AUDIO_CODECS)
        self.bitrate = _number(8, 1536, 192, _(" kbps"))
        self.route_fields = {}

        if kind == MediaKind.AUDIO_MIX:
            for key, label, devices in (
                ("mic", _("Microphone"), microphones), ("system", _("System output"), outputs),
            ):
                selector = _choices(_("System default"), "", ())
                for device in devices:
                    if audio_id := device.extra.get("audio_id"):
                        selector.addItem(device.name, audio_id)
                gain = _number(0, 300, 100, _(" %"))
                self.route_fields[key] = (selector, gain)
                form.addRow(label, selector)
                form.addRow(_("{source} gain").format(source=label), gain)

        form.addRow(_("Sample rate"), self.sample_rate)
        form.addRow(_("Channels"), self.channels)
        form.addRow(_("Gain"), self.volume)
        form.addRow(_("Audio codec"), self.codec)
        form.addRow(_("Audio bitrate"), self.bitrate)
        self.from_settings({})

    def to_settings(self):
        settings = {
            "sample_rate": self.sample_rate.value(),
            "channels": self.channels.currentData(),
            "volume": self.volume.value(),
            "audio_codec": self.codec.currentData(),
            "audio_bitrate": self.bitrate.value() * 1000,
        }
        for key, (selector, gain) in self.route_fields.items():
            settings[f"{key}_device"] = selector.currentData()
            settings[f"{key}_volume"] = gain.value()
        return settings

    def from_settings(self, settings):
        self.sample_rate.setValue(settings.get("sample_rate", 48000))
        _select(self.channels, settings.get("channels", 2))
        self.volume.setValue(settings.get("volume", 100))
        _select(self.codec, settings.get("audio_codec", "auto"))
        self.bitrate.setValue(settings.get("audio_bitrate", 192000) // 1000)
        for key, (selector, gain) in self.route_fields.items():
            _select(selector, settings.get(f"{key}_device", ""), allow_custom=True)
            gain.setValue(settings.get(f"{key}_volume", 100))


class VideoSettingsForm(QWidget):
    def __init__(self, kind=None, parent=None):
        super().__init__(parent)
        self.kind = kind
        form = QFormLayout(self)
        if kind == MediaKind.CAMERA:
            self.resolution = _choices(_("Device default"), "", ())
            self.capture_fps = _number(1, 240, 30)
            self.pixel_format = _choices(_("Automatic"), "", CAMERA_PIXEL_FORMATS)
            form.addRow(_("Camera resolution"), self.resolution)
            form.addRow(_("Camera frame rate"), self.capture_fps)
            form.addRow(_("Camera pixel format"), self.pixel_format)
        elif kind in (MediaKind.MONITOR, MediaKind.WINDOW):
            self.capture_interval = _number(1, 60000, 33, _(" ms"))
            form.addRow(_("Capture interval"), self.capture_interval)

        self.output_size = _choices(_("Source size"), "", VIDEO_SIZES)
        self.fps = _number(1, 240, 30)
        self.codec = _choices(_("Automatic"), "auto", VIDEO_CODECS)
        self.bitrate = _number(100, 200000, 8000, _(" kbps"))
        form.addRow(_("Output resolution"), self.output_size)
        form.addRow(_("Output frame rate"), self.fps)
        form.addRow(_("Video codec"), self.codec)
        form.addRow(_("Video bitrate"), self.bitrate)

    def load_camera_formats(self, formats):
        for size in dict.fromkeys(fmt.resolution for fmt in formats):
            if self.resolution.findData(size) < 0:
                self.resolution.addItem(size, size)

    def to_settings(self):
        settings = {
            "output_size": self.output_size.currentData(),
            "fps": self.fps.value(),
            "video_codec": self.codec.currentData(),
            "video_bitrate": self.bitrate.value() * 1000,
        }
        if self.kind == MediaKind.CAMERA:
            settings["resolution"] = self.resolution.currentData()
            settings["capture_fps"] = self.capture_fps.value()
            settings["pixel_format"] = self.pixel_format.currentData()
        elif self.kind in (MediaKind.MONITOR, MediaKind.WINDOW):
            settings["capture_interval"] = self.capture_interval.value()
        return settings

    def from_settings(self, settings):
        fps = int(settings.get("fps") or 30)
        output_size = settings.get("output_size", settings.get("resolution_cap", ""))
        _select(self.output_size, "" if output_size == "Passthrough" else output_size, allow_custom=True)
        self.fps.setValue(fps)
        _select(self.codec, settings.get("video_codec", "auto"))
        self.bitrate.setValue(settings.get("video_bitrate", 8000000) // 1000)
        if self.kind == MediaKind.CAMERA:
            _select(self.resolution, settings.get("resolution", ""), allow_custom=True)
            self.capture_fps.setValue(int(settings.get("capture_fps") or fps))
            _select(self.pixel_format, settings.get("pixel_format", ""))
        elif self.kind in (MediaKind.MONITOR, MediaKind.WINDOW):
            self.capture_interval.setValue(settings.get("capture_interval", max(1, round(1000 / fps))))

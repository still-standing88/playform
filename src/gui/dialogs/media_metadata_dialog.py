from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QApplication
from PySide6.QtCore import Qt


def _format_size(num_bytes) -> str:
    try:
        num_bytes = float(num_bytes)
    except (TypeError, ValueError):
        return "-"
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"


def _format_duration(seconds) -> str:
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        return "-"
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"


class MediaMetadataDialog(QDialog):
    def __init__(self, title: str, rows: list[tuple[str, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(500, 500)
        self.setup_ui(rows)

    def setup_ui(self, rows: list[tuple[str, str]]):
        layout = QVBoxLayout(self)

        self.metadata_edit = QTextEdit(self)
        self.metadata_edit.setReadOnly(True)
        self.metadata_edit.setTabChangesFocus(True)
        self.metadata_edit.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.metadata_edit.setPlainText(self._rows_to_text(rows))
        layout.addWidget(self.metadata_edit, 1)

        button_layout = QHBoxLayout()

        self.copy_button = QPushButton(_("Copy"), self)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(self.copy_button)

        button_layout.addStretch()

        self.close_button = QPushButton(_("Close"), self)
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    @staticmethod
    def _rows_to_text(rows: list[tuple[str, str]]) -> str:
        return "\n".join(f"{label}: {value}" for label, value in rows)

    def copy_to_clipboard(self):
        QApplication.clipboard().setText(self.metadata_edit.toPlainText())

    @classmethod
    def from_local_metadata(cls, path: str, metadata: dict, parent=None) -> "MediaMetadataDialog":
        rows = []
        fmt = metadata.get("format", {})
        rows.append((_("File"), path))
        rows.append((_("Format"), fmt.get("format_long_name") or fmt.get("format_name") or "-"))
        rows.append((_("Duration"), _format_duration(fmt.get("duration"))))
        rows.append((_("Size"), _format_size(fmt.get("size"))))
        bit_rate = fmt.get("bit_rate")
        if bit_rate:
            rows.append((_("Bitrate"), f"{int(bit_rate) // 1000} kb/s"))

        for stream in metadata.get("streams", []):
            codec_type = stream.get("codec_type", "unknown")
            codec_name = stream.get("codec_name", "-")
            if codec_type == "video":
                width, height = stream.get("width"), stream.get("height")
                resolution = f"{width}x{height}" if width and height else "-"
                fps = stream.get("r_frame_rate", "-")
                rows.append((_("Video codec"), codec_name))
                rows.append((_("Resolution"), resolution))
                rows.append((_("Frame rate"), fps))
            elif codec_type == "audio":
                rows.append((_("Audio codec"), codec_name))
                rows.append((_("Sample rate"), f"{stream.get('sample_rate', '-')} Hz"))
                rows.append((_("Channels"), str(stream.get("channels", "-"))))
            else:
                rows.append((_("Stream ({type})").format(type=codec_type), codec_name))

        return cls(_("Media Metadata"), rows, parent=parent)

    @classmethod
    def from_url_info(cls, url: str, info: dict, parent=None) -> "MediaMetadataDialog":
        rows = [
            (_("URL"), url),
            (_("Extension"), info.get("ext") or "-"),
            (_("Video codec"), info.get("vcodec") or "-"),
            (_("Audio codec"), info.get("acodec") or "-"),
        ]
        width, height = info.get("width"), info.get("height")
        if width and height:
            rows.append((_("Resolution"), f"{width}x{height}"))
        if info.get("fps"):
            rows.append((_("Frame rate"), str(info.get("fps"))))

        bitrate = info.get("tbr") or info.get("vbr") or info.get("abr")
        if bitrate:
            rows.append((_("Bitrate"), f"{bitrate:.0f} kb/s"))

        filesize = info.get("filesize") or info.get("filesize_approx")
        if filesize:
            rows.append((_("File size"), _format_size(filesize)))

        if info.get("duration"):
            rows.append((_("Duration"), _format_duration(info.get("duration"))))

        rows.append((_("Format ID"), info.get("format_id") or "-"))
        rows.append((_("Protocol"), info.get("protocol") or "-"))

        return cls(_("Media Metadata"), rows, parent=parent)

    @classmethod
    def from_mpv_properties(cls, properties: dict, parent=None) -> "MediaMetadataDialog":
        """Live decoder state rather than a container probe, so it reports
        what is actually being played (active hwdec, current vo/ao, A/V sync
        drift, dropped frames) and works for streams ffprobe would have to
        re-fetch. Every field is optional -- get_media_properties() omits
        whatever the current media has no value for."""
        def value_of(key, default="-"):
            value = properties.get(key)
            return default if value is None else value

        rows = [
            (_("File"), value_of("filename")),
            (_("Title"), value_of("media_title")),
            (_("Container"), value_of("file_format")),
        ]
        if "file_size" in properties:
            rows.append((_("Size"), _format_size(properties["file_size"])))
        if "duration" in properties:
            rows.append((_("Duration"), _format_duration(properties["duration"])))
        if "percent_pos" in properties:
            rows.append((_("Position"), f"{float(properties['percent_pos']):.1f}%"))

        video_params = properties.get("video_params") or {}
        if "video_codec" in properties or video_params:
            rows.append((_("Video codec"), value_of("video_codec")))
            width = properties.get("width") or video_params.get("w")
            height = properties.get("height") or video_params.get("h")
            if width and height:
                rows.append((_("Resolution"), f"{width}x{height}"))
            if video_params.get("pixelformat"):
                rows.append((_("Pixel format"), video_params["pixelformat"]))
            for label, key in ((_("Color space"), "colormatrix"),
                               (_("Color levels"), "colorlevels"),
                               (_("Primaries"), "primaries"),
                               (_("Transfer"), "gamma")):
                if video_params.get(key):
                    rows.append((label, video_params[key]))
            if "container_fps" in properties:
                rows.append((_("Frame rate"), f"{float(properties['container_fps']):.3f}"))
            if "estimated_vf_fps" in properties:
                rows.append((_("Estimated output FPS"), f"{float(properties['estimated_vf_fps']):.3f}"))
            if "video_bitrate" in properties:
                rows.append((_("Video bitrate"), f"{int(properties['video_bitrate']) // 1000} kb/s"))

        audio_params = properties.get("audio_params") or {}
        if "audio_codec_name" in properties or audio_params:
            rows.append((_("Audio codec"), value_of("audio_codec_name")))
            if audio_params.get("samplerate"):
                rows.append((_("Sample rate"), f"{audio_params['samplerate']} Hz"))
            if audio_params.get("channels"):
                rows.append((_("Channels"), str(audio_params["channels"])))
            if audio_params.get("format"):
                rows.append((_("Sample format"), audio_params["format"]))
            if "audio_bitrate" in properties:
                rows.append((_("Audio bitrate"), f"{int(properties['audio_bitrate']) // 1000} kb/s"))

        rows.append((_("Video output"), value_of("current_vo")))
        rows.append((_("Audio output"), value_of("current_ao")))
        rows.append((_("Audio device"), value_of("audio_device")))
        rows.append((_("Hardware decoding"), value_of("hwdec_current")))

        if "avsync" in properties:
            rows.append((_("A/V sync"), f"{float(properties['avsync']):.4f} s"))
        if "frame_drop_count" in properties:
            rows.append((_("Dropped frames"), str(properties["frame_drop_count"])))
        if "decoder_frame_drop_count" in properties:
            rows.append((_("Decoder dropped frames"), str(properties["decoder_frame_drop_count"])))
        if "demuxer_cache_duration" in properties:
            rows.append((_("Cached ahead"), f"{float(properties['demuxer_cache_duration']):.1f} s"))
        if properties.get("paused_for_cache"):
            rows.append((_("Buffering"), _("Yes")))
        if "chapters" in properties:
            rows.append((_("Chapters"), str(properties["chapters"])))

        for track in properties.get("track_list") or []:
            kind = track.get("type", "?")
            parts = [f"#{track.get('id', '?')}", track.get("codec") or "-"]
            if track.get("lang"):
                parts.append(track["lang"])
            if track.get("title"):
                parts.append(track["title"])
            if track.get("selected"):
                parts.append(_("selected"))
            rows.append((_("Track ({type})").format(type=kind), " / ".join(str(p) for p in parts)))

        for key, value in (properties.get("metadata") or {}).items():
            rows.append((f"{_('Tag')}: {key}", str(value)))

        return cls(_("Media Metadata (MPV)"), rows, parent=parent)

from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton
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

        self.metadata_list = QListWidget(self)
        self.metadata_list.setAlternatingRowColors(True)
        self.metadata_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        for label, value in rows:
            item = QListWidgetItem(f"{label}:  {value}")
            item.setToolTip(value)
            self.metadata_list.addItem(item)
        layout.addWidget(self.metadata_list, 1)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.close_button = QPushButton(_("Close"), self)
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

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

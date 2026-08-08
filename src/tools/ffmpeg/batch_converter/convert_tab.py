from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QRadioButton,
    QButtonGroup, QStackedWidget, QComboBox, QCheckBox, QLabel, QSpinBox,
    QDoubleSpinBox, QLineEdit
)

from media_core.ffmpeg.format_capabilities import AUDIO_FORMATS, get_format
from tools.ffmpeg.batch_converter.param_widgets import make_param_widget, read_param_widget
from tools.utils import get_video_formats_map


class AudioConvertPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._option_inputs: dict = {}
        self._build_ui()
        self._on_format_changed()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.format_combo = QComboBox(self)
        for format_id, fmt in AUDIO_FORMATS.items():
            self.format_combo.addItem(fmt.label, format_id)
        form.addRow(_("Format"), self.format_combo)

        self.sample_rate_combo = QComboBox(self)
        form.addRow(_("Sample Rate"), self.sample_rate_combo)

        self.bit_rate_combo = QComboBox(self)
        form.addRow(_("Bit Rate"), self.bit_rate_combo)

        self.vbr_check = QCheckBox(_("Use Variable Bit Rate (Quality)"), self)
        form.addRow("", self.vbr_check)

        self.bit_depth_combo = QComboBox(self)
        form.addRow(_("Bit Depth"), self.bit_depth_combo)

        self.codec_options_group = QGroupBox(_("Codec Options"), self)
        self.codec_options_form = QFormLayout(self.codec_options_group)
        layout.addWidget(self.codec_options_group)
        layout.addStretch()

        self.format_combo.currentIndexChanged.connect(self._on_format_changed)

    def _clear_codec_options(self):
        while self.codec_options_form.rowCount():
            self.codec_options_form.removeRow(0)
        self._option_inputs.clear()

    def _on_format_changed(self):
        fmt = get_format(self.current_format_id())

        self.sample_rate_combo.clear()
        self.sample_rate_combo.addItem(_("Keep Original"), 0)
        for rate in fmt.sample_rates or []:
            self.sample_rate_combo.addItem(f"{rate} Hz", rate)
        self.sample_rate_combo.setCurrentIndex(0)

        has_bitrate = bool(fmt.bitrates_kbps)
        self.bit_rate_combo.setVisible(has_bitrate)
        self.vbr_check.setVisible(has_bitrate and bool(fmt.vbr_quality_range))
        self.bit_rate_combo.clear()
        if has_bitrate:
            self.bit_rate_combo.addItem(_("Keep Original (Encoder Default)"), 0)
            for rate in fmt.bitrates_kbps:
                self.bit_rate_combo.addItem(f"{rate} kbps", rate)
            self.bit_rate_combo.setCurrentIndex(0)

        has_bit_depth = bool(fmt.bit_depths)
        self.bit_depth_combo.setVisible(has_bit_depth)
        self.bit_depth_combo.clear()
        if has_bit_depth:
            self.bit_depth_combo.addItem(_("Keep Original"), 0)
            for depth in fmt.bit_depths:
                self.bit_depth_combo.addItem(f"{depth}-bit", depth)
            self.bit_depth_combo.setCurrentIndex(0)

        self._clear_codec_options()
        self.codec_options_group.setVisible(bool(fmt.codec_options))
        for option in fmt.codec_options:
            widget = make_param_widget(self, option.kind, option.choices, option.value_range,
                                        option.default, "")
            self._option_inputs[option.key] = widget
            self.codec_options_form.addRow(option.label, widget)

        self._rebuild_tab_order()

    def _rebuild_tab_order(self):
        # Codec-option widgets are destroyed and recreated on every format change, so Qt
        # appends the new instances to the end of the window's tab order (after widgets
        # created later, like the Begin button) unless explicitly re-chained here.
        previous = self.bit_depth_combo
        for widget in self._option_inputs.values():
            self.setTabOrder(previous, widget)
            previous = widget

    def current_format_id(self) -> str:
        return self.format_combo.currentData() or next(iter(AUDIO_FORMATS))

    def selected_options(self) -> dict:
        fmt = get_format(self.current_format_id())
        result = {
            "format_id": fmt.id,
            "sample_rate": self.sample_rate_combo.currentData(),
            "bit_rate_kbps": self.bit_rate_combo.currentData() if not self.vbr_check.isChecked() else None,
            "vbr_quality": (fmt.default_vbr_quality if self.vbr_check.isChecked() else None),
            "bit_depth": self.bit_depth_combo.currentData(),
            "codec_option_values": {key: read_param_widget(widget) for key, widget in self._option_inputs.items()},
        }
        return result

    def load_options(self, state: dict):
        if not state:
            return

        format_index = self.format_combo.findData(state.get("format_id"))
        if format_index >= 0:
            self.format_combo.setCurrentIndex(format_index)

        rate_index = self.sample_rate_combo.findData(state.get("sample_rate"))
        if rate_index >= 0:
            self.sample_rate_combo.setCurrentIndex(rate_index)

        self.vbr_check.setChecked(state.get("vbr_quality") is not None)
        bitrate_index = self.bit_rate_combo.findData(state.get("bit_rate_kbps"))
        if bitrate_index >= 0:
            self.bit_rate_combo.setCurrentIndex(bitrate_index)

        depth_index = self.bit_depth_combo.findData(state.get("bit_depth"))
        if depth_index >= 0:
            self.bit_depth_combo.setCurrentIndex(depth_index)

        for key, value in (state.get("codec_option_values") or {}).items():
            widget = self._option_inputs.get(key)
            if widget is None:
                continue
            if isinstance(widget, QComboBox):
                index = widget.findData(value)
                if index >= 0:
                    widget.setCurrentIndex(index)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.setValue(value)
            elif isinstance(widget, QLineEdit):
                widget.setText(str(value))


class VideoConvertPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.format_combo = QComboBox(self)
        for label in get_video_formats_map():
            self.format_combo.addItem(label)
        form.addRow(_("Format"), self.format_combo)

        self.resolution_combo = QComboBox(self)
        self.resolution_combo.addItems([_("Keep Original"), "3840x2160", "1920x1080", "1280x720", "854x480"])
        form.addRow(_("Resolution"), self.resolution_combo)

        self.bit_rate_combo = QComboBox(self)
        self.bit_rate_combo.addItem(_("Keep Original (Encoder Default)"))
        self.bit_rate_combo.addItems(["500k", "1000k", "2000k", "4000k", "6000k", "8000k", "12000k"])
        self.bit_rate_combo.setCurrentIndex(0)
        form.addRow(_("Video Bit Rate"), self.bit_rate_combo)

        self.framerate_combo = QComboBox(self)
        self.framerate_combo.addItems([_("Keep Original"), "24", "25", "30", "50", "60"])
        form.addRow(_("Frame Rate"), self.framerate_combo)

        layout.addStretch()

    def selected_options(self) -> dict:
        return {
            "format_label": self.format_combo.currentText(),
            "codec": get_video_formats_map().get(self.format_combo.currentText()),
            "resolution": None if self.resolution_combo.currentIndex() == 0 else self.resolution_combo.currentText(),
            "video_bit_rate": None if self.bit_rate_combo.currentIndex() == 0 else self.bit_rate_combo.currentText(),
            "framerate": None if self.framerate_combo.currentIndex() == 0 else self.framerate_combo.currentText(),
        }

    def load_options(self, state: dict):
        if not state:
            return

        format_index = self.format_combo.findText(state.get("format_label", ""))
        if format_index >= 0:
            self.format_combo.setCurrentIndex(format_index)

        resolution = state.get("resolution")
        self.resolution_combo.setCurrentIndex(self.resolution_combo.findText(resolution) if resolution else 0)

        bit_rate = state.get("video_bit_rate")
        self.bit_rate_combo.setCurrentIndex(self.bit_rate_combo.findText(bit_rate) if bit_rate else 0)

        framerate = state.get("framerate")
        self.framerate_combo.setCurrentIndex(self.framerate_combo.findText(framerate) if framerate else 0)


class ConvertTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        mode_row = QHBoxLayout()
        self.audio_radio = QRadioButton(_("Audio"), self)
        self.video_radio = QRadioButton(_("Video"), self)
        self.audio_radio.setChecked(True)
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.audio_radio, 0)
        self.mode_group.addButton(self.video_radio, 1)
        mode_row.addWidget(self.audio_radio)
        mode_row.addWidget(self.video_radio)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        self.stack = QStackedWidget(self)
        self.audio_panel = AudioConvertPanel(self)
        self.video_panel = VideoConvertPanel(self)
        self.stack.addWidget(self.audio_panel)
        self.stack.addWidget(self.video_panel)
        layout.addWidget(self.stack)

        self.audio_radio.toggled.connect(lambda checked: checked and self.stack.setCurrentIndex(0))
        self.video_radio.toggled.connect(lambda checked: checked and self.stack.setCurrentIndex(1))

    def is_video_mode(self) -> bool:
        return self.video_radio.isChecked()

    def selected_options(self) -> dict:
        if self.is_video_mode():
            return {"mode": "video", **self.video_panel.selected_options()}
        return {"mode": "audio", **self.audio_panel.selected_options()}

    def load_options(self, state: dict):
        if not state:
            return

        if state.get("mode") == "video":
            self.video_radio.setChecked(True)
            self.video_panel.load_options(state)
        else:
            self.audio_radio.setChecked(True)
            self.audio_panel.load_options(state)

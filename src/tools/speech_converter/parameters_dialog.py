from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QCheckBox, QPushButton, QComboBox
)
from PySide6.QtCore import Qt

from tools.speech_converter.engine import SpeechEngine


class ParametersDialog(QDialog):

    def __init__(self, engine: SpeechEngine, values: dict, parent=None):
        super().__init__(parent)
        self.engine = engine
        self._values = dict(values)
        self.setWindowTitle(_("Speech Parameters"))
        self.setMinimumWidth(360)
        self._build_ui()

    def _make_slider_row(self, label: str, low: int, high: int, value: int):
        row = QHBoxLayout()
        label_widget = QLabel(label)
        row.addWidget(label_widget)
        slider = QSlider(Qt.Orientation.Horizontal, self)
        slider.setRange(low, high)
        slider.setValue(value)
        slider.setAccessibleName(label)
        label_widget.setBuddy(slider)
        value_label = QLabel(str(value), self)
        value_label.setFixedWidth(40)
        slider.valueChanged.connect(lambda v: value_label.setText(str(v)))
        row.addWidget(slider)
        row.addWidget(value_label)
        return row, slider

    def _make_combo_row(self, label: str):
        row = QHBoxLayout()
        label_widget = QLabel(label)
        row.addWidget(label_widget)
        combo = QComboBox(self)
        combo.setAccessibleName(label)
        label_widget.setBuddy(combo)
        row.addWidget(combo, stretch=1)
        return row, combo

    def _build_voice_selection(self, layout):
        language_row, self.language_combo = self._make_combo_row(_("Language"))
        layout.addLayout(language_row)

        voice_row, self.voice_combo = self._make_combo_row(_("Voice"))
        layout.addLayout(voice_row)

        seen = set()
        entries = []
        for locale in self.engine.available_locales():
            name = locale.name()
            if name in seen:
                continue
            seen.add(name)
            entries.append((locale.nativeLanguageName() or name, name))
        for display, name in sorted(entries):
            self.language_combo.addItem(display, name)

        current_locale = self._values.get("locale") or self.engine.current_locale().name()
        index = self.language_combo.findData(current_locale)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)

        self.language_combo.currentIndexChanged.connect(self._populate_voices)
        self._populate_voices()

    def _populate_voices(self):
        locale_name = self.language_combo.currentData()
        if not locale_name:
            return
        wanted = self.voice_combo.currentText() or self._values.get("voice") or ""
        self.voice_combo.clear()
        for _locale, voice in self.engine.voices_for_locale_name(locale_name):
            self.voice_combo.addItem(voice.name())
        index = self.voice_combo.findText(wanted)
        self.voice_combo.setCurrentIndex(index if index >= 0 else 0)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self._build_voice_selection(layout)

        volume_row, self.volume_slider = self._make_slider_row(
            _("Volume"), 0, 100, int(self._values.get("volume", 1.0) * 100)
        )
        layout.addLayout(volume_row)

        speed_row, self.speed_slider = self._make_slider_row(
            _("Speed"), -100, 100, int(self._values.get("rate", 0.0) * 100)
        )
        layout.addLayout(speed_row)

        self.pitch_row, self.pitch_slider = self._make_slider_row(
            _("Pitch"), -100, 100, int(self._values.get("pitch", 0.0) * 100)
        )
        layout.addLayout(self.pitch_row)

        self.pitch_xml_row, self.pitch_xml_slider = self._make_slider_row(
            _("Pitch (SAPI XML tag)"), -10, 10, int(self._values.get("pitch_xml_middle", 0))
        )
        layout.addLayout(self.pitch_xml_row)

        self.use_pitch_xml_check = QCheckBox(_("Use pitch parameter through XML tags"), self)
        self.use_pitch_xml_check.setChecked(bool(self._values.get("use_pitch_xml", False)))
        self.use_pitch_xml_check.toggled.connect(self._update_pitch_mode)
        self.use_pitch_xml_check.setVisible(self.engine.supports_pitch_xml())
        layout.addWidget(self.use_pitch_xml_check)

        button_row = QHBoxLayout()
        self.ok_button = QPushButton(_("OK"), self)
        self.cancel_button = QPushButton(_("Cancel"), self)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        button_row.addStretch()
        button_row.addWidget(self.ok_button)
        button_row.addWidget(self.cancel_button)
        layout.addLayout(button_row)

        self._update_pitch_mode(self.use_pitch_xml_check.isChecked())

    def _update_pitch_mode(self, use_xml: bool):
        show_normal_pitch = not use_xml and self.engine.supports_normal_pitch()
        for i in range(self.pitch_row.count()):
            widget = self.pitch_row.itemAt(i).widget()
            if widget:
                widget.setVisible(show_normal_pitch)
        for i in range(self.pitch_xml_row.count()):
            widget = self.pitch_xml_row.itemAt(i).widget()
            if widget:
                widget.setVisible(use_xml and self.engine.supports_pitch_xml())

    def values(self) -> dict:
        return {
            "locale": self.language_combo.currentData() or "",
            "voice": self.voice_combo.currentText(),
            "volume": self.volume_slider.value() / 100.0,
            "rate": self.speed_slider.value() / 100.0,
            "pitch": self.pitch_slider.value() / 100.0,
            "use_pitch_xml": self.use_pitch_xml_check.isChecked(),
            "pitch_xml_middle": self.pitch_xml_slider.value(),
        }

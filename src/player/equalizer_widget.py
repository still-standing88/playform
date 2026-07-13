from typing import List, Optional

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                                QComboBox, QCheckBox)
from PySide6.QtCore import Qt

from app_config import prefs
from gui_controls.player_key_event_filter import KeyEventFilter


class EqualizerWidget(QWidget):
    def __init__(self, parent=None, player=None):
        super().__init__(parent)
        self.player = player
        self._building = False
        self._band_sliders: List[QSlider] = []
        self._key_event_filter = KeyEventFilter(self)

        self.setup_ui()
        self.connect_signals()
        self._install_event_filter()
        self.setEnabled(False)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(6)

        self.enabled_checkbox = QCheckBox(_("Enable Equalizer"), self)
        layout.addWidget(self.enabled_checkbox)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel(_("Preset"), self))
        self.preset_combo = QComboBox(self)
        preset_row.addWidget(self.preset_combo, 1)
        layout.addLayout(preset_row)

        preamp_row = QHBoxLayout()
        preamp_row.addWidget(QLabel(_("Preamp"), self))
        self.preamp_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.preamp_slider.setRange(-20, 20)
        self.preamp_slider.setValue(0)
        self.preamp_slider.setAccessibleName(_("Preamp"))
        preamp_row.addWidget(self.preamp_slider, 1)
        layout.addLayout(preamp_row)

        self.bands_layout = QHBoxLayout()
        layout.addLayout(self.bands_layout)

    def connect_signals(self):
        self.enabled_checkbox.toggled.connect(self._on_enabled_toggled)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self.preamp_slider.valueChanged.connect(self._on_slider_changed)

    def set_player(self, player):
        self.player = player
        self._populate_from_player()

    def _populate_from_player(self):
        if not self.player:
            return

        self._building = True
        try:
            self._build_band_sliders(self.player.get_equalizer_bands())

            self.preset_combo.clear()
            self.preset_combo.addItem(_("Custom"), -1)
            for i, name in enumerate(self.player.get_equalizer_presets()):
                self.preset_combo.addItem(name, i)
        finally:
            self._building = False

        self.setEnabled(True)
        self._key_event_filter.install_on_widgets(self._band_sliders)
        self._load_saved_state()

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                continue
            child_layout = item.layout()
            if child_layout:
                EqualizerWidget._clear_layout(child_layout)

    def _build_band_sliders(self, frequencies: List[float]):
        self._clear_layout(self.bands_layout)
        self._band_sliders = []
        for freq in frequencies:
            column = QVBoxLayout()
            slider = QSlider(Qt.Orientation.Vertical, self)
            slider.setRange(-20, 20)
            slider.setValue(0)
            slider.setMinimumHeight(100)
            slider.setAccessibleName(self._format_freq(freq))
            slider.valueChanged.connect(self._on_slider_changed)
            label = QLabel(self._format_freq(freq), self)
            label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            column.addWidget(slider, 0, Qt.AlignmentFlag.AlignHCenter)
            column.addWidget(label)
            self.bands_layout.addLayout(column)
            self._band_sliders.append(slider)

    @staticmethod
    def _format_freq(freq: float) -> str:
        if freq >= 1000:
            return f"{freq / 1000:.1f}k"
        return f"{freq:.0f}"

    def _load_saved_state(self):
        self._building = True
        try:
            self.enabled_checkbox.setChecked(bool(prefs.prefs.get("equalizer_enabled", False)))
            self.preamp_slider.setValue(int(prefs.prefs.get("equalizer_preamp", 0.0)))

            bands = prefs.prefs.get("equalizer_bands") or []
            for slider, amp in zip(self._band_sliders, bands):
                slider.setValue(int(amp))

            preset = prefs.prefs.get("equalizer_preset", -1)
            preset = preset if preset is not None else -1
            idx = self.preset_combo.findData(preset)
            self.preset_combo.setCurrentIndex(idx if idx >= 0 else 0)
        finally:
            self._building = False

    def _current_band_amps(self) -> List[float]:
        return [float(slider.value()) for slider in self._band_sliders]

    def _apply(self):
        if not self.player:
            return
        preset = self.preset_combo.currentData()
        self.player.set_equalizer(
            self._current_band_amps(),
            preamp=float(self.preamp_slider.value()),
            preset=preset if preset is not None and preset >= 0 else None,
        )

    def _on_enabled_toggled(self, checked: bool):
        if self._building:
            return
        if checked:
            self._apply()
        elif self.player:
            self.player.disable_equalizer()

    def _on_preset_changed(self, index: int):
        if self._building:
            return
        preset = self.preset_combo.itemData(index)
        if preset is not None and preset >= 0 and self.player:
            amps = self.player.get_preset_amps(preset)
            self._building = True
            try:
                for slider, amp in zip(self._band_sliders, amps):
                    slider.setValue(int(amp))
            finally:
                self._building = False
        if self.enabled_checkbox.isChecked():
            self._apply()

    def _on_slider_changed(self, _value: int):
        if self._building:
            return
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(0)
        self.preset_combo.blockSignals(False)
        if self.enabled_checkbox.isChecked():
            self._apply()

    def _install_event_filter(self):
        self._key_event_filter.install_on_widgets(
            [self.enabled_checkbox, self.preset_combo, self.preamp_slider]
        )

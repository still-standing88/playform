from typing import List, Optional

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox,
                                QComboBox, QCheckBox)
from PySide6.QtCore import Qt

from app_config import prefs
from gui_controls.player_key_event_filter import KeyEventFilter
from gui_controls.flow_layout import FlowLayout, FlowContainer


class EqualizerWidget(QWidget):
    def __init__(self, parent=None, player=None):
        super().__init__(parent)
        self.player = player
        self._building = False
        self._band_spins: List[QDoubleSpinBox] = []
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
        self.preamp_spin = self._make_band_spin()
        self.preamp_spin.setAccessibleName(_("Preamp"))
        preamp_row.addWidget(self.preamp_spin, 1)
        layout.addLayout(preamp_row)

        # A single un-wrapping QHBoxLayout forced every band's width to sum
        # into the widget's minimum (measured at 1274px for a typical band
        # count) - the same "N items in one fixed row" problem already fixed
        # for the Panels toolbar and the transport controls, via the same
        # FlowLayout, so it wraps onto as many rows as the available width
        # (now a narrow accordion side panel) actually allows.
        self.bands_container = FlowContainer(self)
        self.bands_flow = FlowLayout(self.bands_container, margin=0, h_spacing=8, v_spacing=6)
        layout.addWidget(self.bands_container)

    @staticmethod
    def _make_band_spin() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(-20.0, 20.0)
        spin.setDecimals(1)
        spin.setSingleStep(0.5)
        spin.setValue(0.0)
        return spin

    def connect_signals(self):
        self.enabled_checkbox.toggled.connect(self._on_enabled_toggled)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self.preamp_spin.valueChanged.connect(self._on_value_changed)

    def set_player(self, player):
        self.player = player
        self._populate_from_player()

    def _populate_from_player(self):
        if not self.player:
            return

        self._building = True
        try:
            self._build_band_spins(self.player.get_equalizer_bands())

            self.preset_combo.clear()
            self.preset_combo.addItem(_("Custom"), -1)
            for i, name in enumerate(self.player.get_equalizer_presets()):
                self.preset_combo.addItem(name, i)
        finally:
            self._building = False

        self.setEnabled(True)
        self._key_event_filter.install_on_widgets(self._band_spins)
        self._load_saved_state()

    def _build_band_spins(self, frequencies: List[float]):
        while self.bands_flow.count():
            item = self.bands_flow.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._band_spins = []
        prev_widget = self.preamp_spin
        for freq in frequencies:
            band_widget = QWidget(self.bands_container)
            column = QVBoxLayout(band_widget)
            column.setContentsMargins(0, 0, 0, 0)
            label = QLabel(self._format_freq(freq), band_widget)
            label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            spin = self._make_band_spin()
            spin.setAccessibleName(_("{freq} band gain").format(freq=self._format_freq_full(freq)))
            spin.valueChanged.connect(self._on_value_changed)
            column.addWidget(label)
            column.addWidget(spin)
            self.bands_flow.addWidget(band_widget)
            self._band_spins.append(spin)
            # Band spinboxes are (re)built after the whole accordion is already
            # constructed, so Qt's default tab order would otherwise append them
            # after unrelated widgets built later (e.g. the next section's
            # header) instead of right after the preamp spinbox.
            QWidget.setTabOrder(prev_widget, spin)
            prev_widget = spin

    @staticmethod
    def _format_freq(freq: float) -> str:
        if freq >= 1000:
            return f"{freq / 1000:.1f}k"
        return f"{freq:.0f}"

    @staticmethod
    def _format_freq_full(freq: float) -> str:
        if freq >= 1000:
            return f"{freq / 1000:.1f} kHz"
        return f"{freq:.0f} Hz"

    def _load_saved_state(self):
        self._building = True
        try:
            self.enabled_checkbox.setChecked(bool(prefs.prefs.get("equalizer_enabled", False)))
            self.preamp_spin.setValue(float(prefs.prefs.get("equalizer_preamp", 0.0)))

            bands = prefs.prefs.get("equalizer_bands") or []
            for spin, amp in zip(self._band_spins, bands):
                spin.setValue(float(amp))

            preset = prefs.prefs.get("equalizer_preset", -1)
            preset = preset if preset is not None else -1
            idx = self.preset_combo.findData(preset)
            self.preset_combo.setCurrentIndex(idx if idx >= 0 else 0)
        finally:
            self._building = False

    def _current_band_amps(self) -> List[float]:
        return [float(spin.value()) for spin in self._band_spins]

    def _apply(self):
        if not self.player:
            return
        preset = self.preset_combo.currentData()
        self.player.set_equalizer(
            self._current_band_amps(),
            preamp=float(self.preamp_spin.value()),
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
                for spin, amp in zip(self._band_spins, amps):
                    spin.setValue(float(amp))
            finally:
                self._building = False
        if self.enabled_checkbox.isChecked():
            self._apply()

    def _on_value_changed(self, _value: float):
        if self._building:
            return
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(0)
        self.preset_combo.blockSignals(False)
        if self.enabled_checkbox.isChecked():
            self._apply()

    def _install_event_filter(self):
        self._key_event_filter.install_on_widgets(
            [self.enabled_checkbox, self.preset_combo, self.preamp_spin]
        )

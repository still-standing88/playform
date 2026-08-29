from typing import Optional

import utilities.mpv_bootstrap
import media_core.av_play as av_play

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QDoubleSpinBox, QPushButton, QComboBox, QCheckBox)

from app_config import prefs
from gui_controls.player_key_event_filter import KeyEventFilter


class AudioSyncWidget(QWidget):
    """A/V sync offset plus ReplayGain. Both are global mpv properties that
    survive file changes, so they are pushed once on change rather than
    re-applied per track, and persisted so the choice sticks across runs."""

    def __init__(self, parent: Optional[QWidget] = None, player=None):
        super().__init__(parent)
        self.player = player
        self._building = False
        self._key_event_filter = KeyEventFilter(self)

        self.setup_ui()
        self.connect_signals()
        self._install_event_filter()
        self.setEnabled(False)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(6)

        delay_row = QHBoxLayout()
        delay_label = QLabel(_("Audio Delay (seconds)"), self)
        delay_row.addWidget(delay_label)
        self.delay_spin = QDoubleSpinBox(self)
        self.delay_spin.setRange(-10.0, 10.0)
        self.delay_spin.setDecimals(3)
        self.delay_spin.setSingleStep(0.05)
        self.delay_spin.setValue(0.0)
        self.delay_spin.setAccessibleName(_("Audio Delay (seconds)"))
        self.delay_spin.setToolTip(_("Positive values delay audio, negative values advance it"))
        delay_label.setBuddy(self.delay_spin)
        delay_row.addWidget(self.delay_spin, 1)
        self.reset_delay_button = QPushButton(_("Reset"), self)
        self.reset_delay_button.setToolTip(_("Reset audio delay to zero"))
        delay_row.addWidget(self.reset_delay_button)
        layout.addLayout(delay_row)

        gain_row = QHBoxLayout()
        gain_label = QLabel(_("ReplayGain"), self)
        gain_row.addWidget(gain_label)
        self.gain_combo = QComboBox(self)
        self.gain_combo.setAccessibleName(_("ReplayGain"))
        self.gain_combo.addItem(_("Off"), "no")
        self.gain_combo.addItem(_("Track"), "track")
        self.gain_combo.addItem(_("Album"), "album")
        gain_label.setBuddy(self.gain_combo)
        gain_row.addWidget(self.gain_combo, 1)
        layout.addLayout(gain_row)

        preamp_row = QHBoxLayout()
        preamp_label = QLabel(_("ReplayGain Preamp (dB)"), self)
        preamp_row.addWidget(preamp_label)
        self.preamp_spin = QDoubleSpinBox(self)
        self.preamp_spin.setRange(-15.0, 15.0)
        self.preamp_spin.setDecimals(1)
        self.preamp_spin.setSingleStep(0.5)
        self.preamp_spin.setValue(0.0)
        self.preamp_spin.setAccessibleName(_("ReplayGain Preamp (dB)"))
        preamp_label.setBuddy(self.preamp_spin)
        preamp_row.addWidget(self.preamp_spin, 1)
        layout.addLayout(preamp_row)

        self.clip_check = QCheckBox(_("Allow ReplayGain clipping"), self)
        self.clip_check.setToolTip(_("Skip the volume reduction that prevents clipping"))
        layout.addWidget(self.clip_check)

        layout.addStretch()

    def connect_signals(self):
        self.delay_spin.valueChanged.connect(self._on_delay_changed)
        self.reset_delay_button.clicked.connect(lambda: self.delay_spin.setValue(0.0))
        self.gain_combo.currentIndexChanged.connect(self._on_replaygain_changed)
        self.preamp_spin.valueChanged.connect(self._on_replaygain_changed)
        self.clip_check.toggled.connect(self._on_replaygain_changed)

    def set_player(self, player):
        self.player = player
        self.setEnabled(player is not None)
        self._load_saved_state()

    def _load_saved_state(self):
        self._building = True
        try:
            self.delay_spin.setValue(float(prefs.prefs.get("audio_delay", 0.0)))
            mode = prefs.prefs.get("replaygain_mode", "no")
            index = self.gain_combo.findData(mode)
            self.gain_combo.setCurrentIndex(index if index >= 0 else 0)
            self.preamp_spin.setValue(float(prefs.prefs.get("replaygain_preamp", 0.0)))
            self.clip_check.setChecked(bool(prefs.prefs.get("replaygain_clip", False)))
        finally:
            self._building = False
        self._apply_delay()
        self._apply_replaygain()

    def _on_delay_changed(self, _value: float):
        if self._building:
            return
        prefs.prefs["audio_delay"] = float(self.delay_spin.value())
        self._apply_delay()

    def _on_replaygain_changed(self, *_args):
        if self._building:
            return
        prefs.prefs["replaygain_mode"] = self.gain_combo.currentData() or "no"
        prefs.prefs["replaygain_preamp"] = float(self.preamp_spin.value())
        prefs.prefs["replaygain_clip"] = bool(self.clip_check.isChecked())
        self._apply_replaygain()

    def _apply_delay(self):
        if not self.player:
            return
        try:
            self.player.set_audio_delay(float(self.delay_spin.value()))
        except Exception:
            pass

    def _apply_replaygain(self):
        if not self.player:
            return
        mode = self.gain_combo.currentData() or "no"
        try:
            self.player.set_replaygain(
                None if mode == "no" else mode,
                preamp=float(self.preamp_spin.value()),
                clip=bool(self.clip_check.isChecked()),
            )
        except Exception:
            pass

    def _install_event_filter(self):
        self._key_event_filter.install_on_widgets([
            self.delay_spin, self.reset_delay_button, self.gain_combo,
            self.preamp_spin, self.clip_check,
        ])

    def set_media_available(self, available: bool):
        # Both properties are global and settable with no media loaded, so
        # unlike the filter panels this stays usable either way.
        pass

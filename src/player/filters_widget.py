from typing import Optional
import av_play

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QSpinBox
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from gui_controls.toggle_button import ToggleButton
from gui_controls.player_key_event_filter import KeyEventFilter


class FiltersWidget(QWidget):
	def __init__(self, parent: Optional[QWidget] = None, player: Optional[av_play.VLCVideoPlayer] = None):
		super().__init__(parent)
		self.player: Optional[av_play.VLCVideoPlayer] = player
		self._building = False
		self._key_event_filter = KeyEventFilter(self)
		self.setup_ui()
		self.connect_signals()
		self._install_event_filter()
		
		self.controls_container.setVisible(False)
		self.toggle_btn.setText("Show Filters")
		self.toggle_btn.setActuated(True)
		self.reset_filters()

	def setup_ui(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(5, 5, 5, 5)
		layout.setSpacing(5)

		header_layout = QHBoxLayout()

		self.title_label = QLabel("Filters", self)
		self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
		header_layout.addWidget(self.title_label)

		header_layout.addStretch()

		self.toggle_btn = ToggleButton("Hide Filters", self)
		self.toggle_btn.setFixedSize(60, 25)
		header_layout.addWidget(self.toggle_btn)

		layout.addLayout(header_layout)

		self.controls_container = QWidget(self)
		controls_layout = QVBoxLayout(self.controls_container)
		controls_layout.setContentsMargins(0, 0, 0, 0)
		controls_layout.setSpacing(6)

		row1 = QHBoxLayout()
		row2 = QHBoxLayout()

		self.brightness_spin = QDoubleSpinBox(self)
		self._setup_dspin(self.brightness_spin, 0.0, 2.0, 0.1, 1.0, "Brightness")
		row1.addWidget(QLabel("Brightness", self))
		row1.addWidget(self.brightness_spin, 1)

		self.contrast_spin = QDoubleSpinBox(self)
		self._setup_dspin(self.contrast_spin, 0.0, 2.0, 0.1, 1.0, "Contrast")
		row1.addWidget(QLabel("Contrast", self))
		row1.addWidget(self.contrast_spin, 1)

		self.gamma_spin = QDoubleSpinBox(self)
		self._setup_dspin(self.gamma_spin, 0.1, 10.0, 0.1, 1.0, "Gamma")
		row2.addWidget(QLabel("Gamma", self))
		row2.addWidget(self.gamma_spin, 1)

		self.hue_spin = QSpinBox(self)
		self._setup_ispin(self.hue_spin, -180, 180, 0, "Hue")
		row2.addWidget(QLabel("Hue", self))
		row2.addWidget(self.hue_spin, 1)

		self.saturation_spin = QDoubleSpinBox(self)
		self._setup_dspin(self.saturation_spin, 0.0, 3.0, 0.1, 1.0, "Saturation")
		row2.addWidget(QLabel("Saturation", self))
		row2.addWidget(self.saturation_spin, 1)

		controls_layout.addLayout(row1)
		controls_layout.addLayout(row2)

		layout.addWidget(self.controls_container)

	def _setup_dspin(self, spin: QDoubleSpinBox, minimum: float, maximum: float, step: float, value: float, name: str):
		spin.setRange(minimum, maximum)
		spin.setSingleStep(step)
		spin.setDecimals(2)
		spin.setValue(value)
		spin.setKeyboardTracking(True)
		spin.setAccessibleName(name)

	def _setup_ispin(self, spin: QSpinBox, minimum: int, maximum: int, value: int, name: str):
		spin.setRange(minimum, maximum)
		spin.setSingleStep(1)
		spin.setValue(value)
		spin.setKeyboardTracking(True)
		spin.setAccessibleName(name)

	def connect_signals(self):
		self.toggle_btn.actuated.connect(self.toggle_filters)
		self.brightness_spin.valueChanged.connect(lambda v: self._on_value_changed("brightness", float(v)))
		self.contrast_spin.valueChanged.connect(lambda v: self._on_value_changed("contrast", float(v)))
		self.gamma_spin.valueChanged.connect(lambda v: self._on_value_changed("gamma", float(v)))
		self.hue_spin.valueChanged.connect(lambda v: self._on_value_changed("hue", float(v)))
		self.saturation_spin.valueChanged.connect(lambda v: self._on_value_changed("saturation", float(v)))

	def set_player(self, player: av_play.VLCVideoPlayer):
		self.player = player
		self.reset_filters()

	def toggle_filters(self, hidden: bool):
		self.controls_container.setVisible(not hidden)
		if hidden:
			self.toggle_btn.setText("Show Filters")
		else:
			self.toggle_btn.setText("Hide Filters")

	def _on_value_changed(self, name: str, value: float):
		if self._building:
			return
		if not self.player:
			return
		try:
			self.player.set_video_adjust_float(name, float(value))
		except Exception:
			pass

	def reset_filters(self):
		self._building = True
		try:
			self._set_spin_silent(self.brightness_spin, 1.0)
			self._set_spin_silent(self.contrast_spin, 1.0)
			self._set_spin_silent(self.gamma_spin, 1.0)
			self._set_spin_silent(self.hue_spin, 0)
			self._set_spin_silent(self.saturation_spin, 1.0)
		finally:
			self._building = False
		self._on_value_changed("brightness", float(self.brightness_spin.value()))
		self._on_value_changed("contrast", float(self.contrast_spin.value()))
		self._on_value_changed("gamma", float(self.gamma_spin.value()))
		self._on_value_changed("hue", float(self.hue_spin.value()))
		self._on_value_changed("saturation", float(self.saturation_spin.value()))

	def _set_spin_silent(self, spin, value):
		spin.blockSignals(True)
		spin.setValue(value)
		spin.blockSignals(False)

	def _install_event_filter(self):
		widgets = [
			self.brightness_spin, self.contrast_spin, self.gamma_spin,
			self.hue_spin, self.saturation_spin, self.toggle_btn
		]
		self._key_event_filter.install_on_widgets(widgets)


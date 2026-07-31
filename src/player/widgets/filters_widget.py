from typing import Optional
import utilities.mpv_bootstrap
import media_core.av_play as av_play

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QSpinBox
from PySide6.QtCore import Qt

from gui_controls.player_key_event_filter import KeyEventFilter
from gui_controls.flow_layout import FlowLayout, FlowContainer


class FiltersWidget(QWidget):
	def __init__(self, parent: Optional[QWidget] = None, player: Optional[av_play.VideoPlayer] = None):
		super().__init__(parent)
		self.player: Optional[av_play.VideoPlayer] = player
		self._building = False
		self._key_event_filter = KeyEventFilter(self)
		self.setup_ui()
		self.connect_signals()
		self._install_event_filter()

		self.reset_filters()

	def setup_ui(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(5, 5, 5, 5)
		layout.setSpacing(5)

		self.controls_container = QWidget(self)
		controls_layout = QVBoxLayout(self.controls_container)
		controls_layout.setContentsMargins(0, 0, 0, 0)
		controls_layout.setSpacing(6)

		# Two fixed rows of 2-3 label+spinbox pairs each, all with equal
		# stretch, forced this widget's minimum width to 682px - the same
		# "several items in one un-wrapping row" problem already fixed for
		# the Panels toolbar and the transport controls, via the same
		# FlowLayout, so the pairs wrap onto as many rows as the available
		# width (now a narrow accordion side panel) actually allows.
		self.filters_container = FlowContainer(self)
		self.filters_flow = FlowLayout(self.filters_container, margin=0, h_spacing=12, v_spacing=6)

		self.brightness_spin = QDoubleSpinBox(self)
		self._setup_dspin(self.brightness_spin, 0.0, 2.0, 0.1, 1.0, _("Brightness"))
		self.filters_flow.addWidget(self._make_filter_row(_("Brightness"), self.brightness_spin))

		self.contrast_spin = QDoubleSpinBox(self)
		self._setup_dspin(self.contrast_spin, 0.0, 2.0, 0.1, 1.0, _("Contrast"))
		self.filters_flow.addWidget(self._make_filter_row(_("Contrast"), self.contrast_spin))

		self.gamma_spin = QDoubleSpinBox(self)
		self._setup_dspin(self.gamma_spin, 0.1, 10.0, 0.1, 1.0, _("Gamma"))
		self.filters_flow.addWidget(self._make_filter_row(_("Gamma"), self.gamma_spin))

		self.hue_spin = QSpinBox(self)
		self._setup_ispin(self.hue_spin, -180, 180, 0, _("Hue"))
		self.filters_flow.addWidget(self._make_filter_row(_("Hue"), self.hue_spin))

		self.saturation_spin = QDoubleSpinBox(self)
		self._setup_dspin(self.saturation_spin, 0.0, 3.0, 0.1, 1.0, _("Saturation"))
		self.filters_flow.addWidget(self._make_filter_row(_("Saturation"), self.saturation_spin))

		controls_layout.addWidget(self.filters_container)

		layout.addWidget(self.controls_container)

	def _make_filter_row(self, label_text: str, spin: QDoubleSpinBox | QSpinBox) -> QWidget:
		row_widget = QWidget(self.filters_container)
		row_layout = QHBoxLayout(row_widget)
		row_layout.setContentsMargins(0, 0, 0, 0)
		row_layout.addWidget(QLabel(label_text, row_widget))
		row_layout.addWidget(spin)
		return row_widget

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
		self.brightness_spin.valueChanged.connect(lambda v: self._on_value_changed("brightness", float(v)))
		self.contrast_spin.valueChanged.connect(lambda v: self._on_value_changed("contrast", float(v)))
		self.gamma_spin.valueChanged.connect(lambda v: self._on_value_changed("gamma", float(v)))
		self.hue_spin.valueChanged.connect(lambda v: self._on_value_changed("hue", float(v)))
		self.saturation_spin.valueChanged.connect(lambda v: self._on_value_changed("saturation", float(v)))

	def set_player(self, player: av_play.VideoPlayer):
		self.player = player
		self.reset_filters()

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
			self.hue_spin, self.saturation_spin
		]
		self._key_event_filter.install_on_widgets(widgets)

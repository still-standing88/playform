from typing import Optional
import utilities.mpv_bootstrap
import media_core.av_play as av_play

from PySide6.QtWidgets import QWidget, QVBoxLayout, QCheckBox

from gui_controls.player_key_event_filter import KeyEventFilter


class VideoEffectsWidget(QWidget):
	def __init__(self, parent: Optional[QWidget] = None, player: Optional[av_play.VideoPlayer] = None):
		super().__init__(parent)
		self.player: Optional[av_play.VideoPlayer] = player
		self._building = False
		self._key_event_filter = KeyEventFilter(self)
		self.setup_ui()
		self.connect_signals()
		self._install_event_filter()

		self.reset_effects()

	def setup_ui(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(5, 5, 5, 5)
		layout.setSpacing(6)

		self.deinterlace_check = QCheckBox(_("Deinterlace"), self)
		layout.addWidget(self.deinterlace_check)

		self.deband_check = QCheckBox(_("Deband"), self)
		layout.addWidget(self.deband_check)

		layout.addStretch()

	def connect_signals(self):
		self.deinterlace_check.toggled.connect(lambda v: self._on_toggled("deinterlace", v))
		self.deband_check.toggled.connect(lambda v: self._on_toggled("deband", v))

	def set_player(self, player: av_play.VideoPlayer):
		self.player = player
		self.reset_effects()

	def _on_toggled(self, name: str, enabled: bool):
		if self._building or not self.player:
			return
		try:
			if name == "deinterlace":
				self.player.set_deinterlace(enabled)
			elif name == "deband":
				self.player.set_deband(enabled)
		except Exception:
			pass

	def reset_effects(self):
		self._building = True
		try:
			self.deinterlace_check.setChecked(False)
			self.deband_check.setChecked(False)
		finally:
			self._building = False
		if not self.player:
			return
		try:
			self.player.set_deinterlace(False)
			self.player.set_deband(False)
		except Exception:
			pass

	def _install_event_filter(self):
		self._key_event_filter.install_on_widgets([self.deinterlace_check, self.deband_check])

	def set_media_available(self, available: bool):
		self.setEnabled(available)

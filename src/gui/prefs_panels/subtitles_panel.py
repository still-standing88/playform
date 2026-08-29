"""Subtitle preferences: language for yt-dlp sources, plus mpv's on-video
rendering style. Style lives here rather than on the player panel because
these are set-once-and-forget appearance choices, unlike delay/track which
change per file.
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QGroupBox,
                               QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox,
                               QFontComboBox)

from app_constance.misc import title_lngs, subtitle_ass_override_modes
from gui_controls.color_button import ColorButton


class SubtitlesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        source_group = QGroupBox(_("Source"))
        source_layout = QFormLayout(source_group)
        self.language_combo = QComboBox()
        self.language_combo.setAccessibleName(_("Preferred subtitle language"))
        for code, name in title_lngs.items():
            self.language_combo.addItem(name, code)
        source_layout.addRow(_("Preferred Language:"), self.language_combo)
        layout.addWidget(source_group)

        render_group = QGroupBox(_("On-Video Rendering"))
        render_layout = QFormLayout(render_group)

        self.render_check = QCheckBox(_("Draw subtitles on the video"))
        self.render_check.setToolTip(
            _("The Subtitles panel's text list is shown either way")
        )
        self.render_check.toggled.connect(self._on_render_toggled)
        render_layout.addRow(self.render_check)

        self.font_combo = QFontComboBox()
        self.font_combo.setEditable(True)
        self.font_combo.setAccessibleName(_("Subtitle font"))
        self.font_combo.setToolTip(
            _("Generic families such as sans-serif and monospace are accepted")
        )
        render_layout.addRow(_("Font:"), self.font_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 200)
        self.font_size_spin.setAccessibleName(_("Subtitle font size"))
        render_layout.addRow(_("Font Size:"), self.font_size_spin)

        self.bold_check = QCheckBox(_("Bold"))
        render_layout.addRow(self.bold_check)

        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.1, 5.0)
        self.scale_spin.setSingleStep(0.1)
        self.scale_spin.setDecimals(2)
        self.scale_spin.setAccessibleName(_("Subtitle scale"))
        self.scale_spin.setToolTip(_("Multiplier applied on top of the font size"))
        render_layout.addRow(_("Scale:"), self.scale_spin)

        self.color_button = ColorButton(_("Text colour"))
        render_layout.addRow(_("Text Colour:"), self.color_button)

        self.back_color_button = ColorButton(_("Background colour"))
        render_layout.addRow(_("Background Colour:"), self.back_color_button)

        self.border_color_button = ColorButton(_("Outline colour"))
        render_layout.addRow(_("Outline Colour:"), self.border_color_button)

        self.border_size_spin = QDoubleSpinBox()
        self.border_size_spin.setRange(0.0, 20.0)
        self.border_size_spin.setSingleStep(0.25)
        self.border_size_spin.setDecimals(2)
        self.border_size_spin.setAccessibleName(_("Outline thickness"))
        render_layout.addRow(_("Outline Thickness:"), self.border_size_spin)

        self.shadow_spin = QDoubleSpinBox()
        self.shadow_spin.setRange(0.0, 20.0)
        self.shadow_spin.setSingleStep(0.25)
        self.shadow_spin.setDecimals(2)
        self.shadow_spin.setAccessibleName(_("Shadow offset"))
        render_layout.addRow(_("Shadow Offset:"), self.shadow_spin)

        self.position_spin = QSpinBox()
        self.position_spin.setRange(0, 100)
        self.position_spin.setAccessibleName(_("Vertical position"))
        self.position_spin.setToolTip(_("0 is the top of the video, 100 the bottom"))
        render_layout.addRow(_("Vertical Position:"), self.position_spin)

        self.ass_override_combo = QComboBox()
        self.ass_override_combo.setAccessibleName(_("ASS/SSA style handling"))
        self.ass_override_combo.setToolTip(
            _("ASS and SSA subtitles carry their own styling; this decides whether "
              "the settings above override it")
        )
        for label, value in subtitle_ass_override_modes:
            self.ass_override_combo.addItem(_(label), value)
        render_layout.addRow(_("ASS/SSA Styling:"), self.ass_override_combo)

        layout.addWidget(render_group)
        layout.addStretch()

    def _on_render_toggled(self, checked: bool):
        for widget in (self.font_combo, self.font_size_spin, self.bold_check,
                       self.scale_spin, self.color_button, self.back_color_button,
                       self.border_color_button, self.border_size_spin,
                       self.shadow_spin, self.position_spin,
                       self.ass_override_combo):
            widget.setEnabled(checked)

    def load_settings(self, prefs):
        index = self.language_combo.findData(prefs.get("subtitle-language", "en-US"))
        self.language_combo.setCurrentIndex(index if index >= 0 else 0)

        self.render_check.setChecked(bool(prefs.get("subtitle_render_on_video", True)))
        # setCurrentText, not setCurrentFont: mpv accepts generic family names
        # like "sans-serif" that aren't installed fonts, and setCurrentFont
        # would resolve those away to a concrete family.
        self.font_combo.setCurrentText(prefs.get("subtitle_font", "sans-serif"))
        self.font_size_spin.setValue(int(prefs.get("subtitle_font_size", 38)))
        self.bold_check.setChecked(bool(prefs.get("subtitle_bold", False)))
        self.scale_spin.setValue(float(prefs.get("subtitle_scale", 1.0)))
        self.color_button.set_color(prefs.get("subtitle_color", "#FFFFFFFF"))
        self.back_color_button.set_color(prefs.get("subtitle_back_color", "#AF000000"))
        self.border_color_button.set_color(prefs.get("subtitle_border_color", "#FF000000"))
        self.border_size_spin.setValue(float(prefs.get("subtitle_border_size", 1.65)))
        self.shadow_spin.setValue(float(prefs.get("subtitle_shadow_offset", 0.0)))
        self.position_spin.setValue(int(prefs.get("subtitle_position", 100)))

        override_index = self.ass_override_combo.findData(prefs.get("subtitle_ass_override", "scale"))
        self.ass_override_combo.setCurrentIndex(override_index if override_index >= 0 else 0)

        self._on_render_toggled(self.render_check.isChecked())

    def save_settings(self, prefs):
        prefs["subtitle-language"] = self.language_combo.currentData() or "en-US"
        prefs["subtitle_render_on_video"] = self.render_check.isChecked()
        prefs["subtitle_font"] = self.font_combo.currentText()
        prefs["subtitle_font_size"] = self.font_size_spin.value()
        prefs["subtitle_bold"] = self.bold_check.isChecked()
        prefs["subtitle_scale"] = self.scale_spin.value()
        prefs["subtitle_color"] = self.color_button.color()
        prefs["subtitle_back_color"] = self.back_color_button.color()
        prefs["subtitle_border_color"] = self.border_color_button.color()
        prefs["subtitle_border_size"] = self.border_size_spin.value()
        prefs["subtitle_shadow_offset"] = self.shadow_spin.value()
        prefs["subtitle_position"] = self.position_spin.value()
        prefs["subtitle_ass_override"] = self.ass_override_combo.currentData() or "scale"

import os

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
                                QPushButton, QComboBox, QMenu, QMessageBox, QInputDialog, QDialog)
from PySide6.QtCore import Qt, Signal

from gui_controls.list_tab import ListTabCtrl
from gui_controls.player_key_event_filter import KeyEventFilter
from gui_controls.param_widgets import make_param_widget, read_param_widget, connect_param_widget_changed
from gui_controls.categorized_effect_picker import CategorizedEffectPickerDialog
from media_core.av_play.mpv_effects_catalog import MPV_EFFECTS, get_mpv_effect
from media_core.av_play import mpv_effect_presets
from utilities.functions import get_ir_dir


def _categories_for(entries):
    seen = []
    for entry in entries:
        if entry.category not in seen:
            seen.append(entry.category)
    return seen


class EffectSummaryPanel(QWidget):
    """Compact per-tab content: effect label + a short current-settings
    line + an "Edit Parameters..." button. Replaces the old always-inline
    parameter form, which ate too much vertical space once several
    effects can be added at once -- full editing now lives in a popup
    (EffectParamPopup) instead, freeing the accordion panel for the
    effects list itself."""

    editRequested = Signal()

    def __init__(self, effect_label: str, summary_text: str, enabled: bool, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        title = QLabel(effect_label, self)
        title_font = title.font()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        self.summary_label = QLabel(summary_text, self)
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        self.edit_button = QPushButton(_("Edit Parameters..."), self)
        self.edit_button.clicked.connect(self.editRequested.emit)
        layout.addWidget(self.edit_button)
        layout.addStretch()
        self.set_effect_enabled(enabled)

    def set_summary(self, text: str):
        self.summary_label.setText(text)

    def set_effect_enabled(self, enabled: bool):
        # Editing a disabled effect's parameters produces no audible
        # feedback, so the edit affordance follows the same checked/
        # unchecked state as the tab's own checkbox.
        self.edit_button.setVisible(enabled)


class EffectParamPopup(QDialog):
    """Edit an already-added effect's parameters, with a per-effect preset
    row (combo + New/Delete) on top. Kept as its own popup rather than
    inline specifically to save vertical space in the accordion panel --
    see EffectSummaryPanel.

    Every value change (dragging a spinbox, picking a preset, ...) applies
    immediately via on_param_changed, matching the old always-inline panel's
    real-time behavior -- there is deliberately no OK/Cancel here (nothing
    to discard: by the time you could click Cancel, you already heard the
    change). Live changes are applied with persist=False for responsiveness
    (skips a disk write per spinbox tick); on_closed fires once when the
    popup closes so the caller can do a single final persist.
    """

    def __init__(self, effect_id: str, values: dict, on_param_changed, on_closed, parent=None):
        super().__init__(parent)
        self.effect_id = effect_id
        self._effect = get_mpv_effect(effect_id)
        self._param_inputs: dict = {}
        self._on_param_changed = on_param_changed
        self._on_closed = on_closed
        self._building = False

        self.setWindowTitle(_("Edit {effect}").format(effect=self._effect.label))
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel(_("Preset"), self))
        self.preset_combo = QComboBox(self)
        preset_row.addWidget(self.preset_combo, 1)
        self.new_preset_button = QPushButton(_("New..."), self)
        self.delete_preset_button = QPushButton(_("Delete"), self)
        preset_row.addWidget(self.new_preset_button)
        preset_row.addWidget(self.delete_preset_button)
        layout.addLayout(preset_row)

        self.param_form_container = QWidget(self)
        self.param_form = QFormLayout(self.param_form_container)
        layout.addWidget(self.param_form_container)

        button_row = QHBoxLayout()
        self.close_button = QPushButton(_("Close"), self)
        button_row.addStretch()
        button_row.addWidget(self.close_button)
        layout.addLayout(button_row)

        self.close_button.clicked.connect(self.accept)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        self.new_preset_button.clicked.connect(self._on_new_preset)
        self.delete_preset_button.clicked.connect(self._on_delete_preset)

        self._build_param_form(values)
        self._reload_presets()

    def _build_param_form(self, values: dict):
        while self.param_form.rowCount():
            self.param_form.removeRow(0)
        self._param_inputs.clear()

        if not self._effect.params:
            self.param_form.addRow(QLabel(_("This effect has no configurable parameters.")))
            return

        default_dir = get_ir_dir() if self.effect_id == "convolution_reverb" else ""
        self._building = True
        try:
            for param in self._effect.params:
                current_value = values.get(param.key, param.default)
                widget = make_param_widget(
                    self, param.kind, param.choices, param.value_range, current_value, param.suffix,
                    default_dir=default_dir,
                )
                self._param_inputs[param.key] = widget
                self.param_form.addRow(param.label, widget)
                connect_param_widget_changed(widget, lambda key=param.key, w=widget: self._on_field_changed(key, w))
        finally:
            self._building = False

    def _on_field_changed(self, key: str, widget):
        if self._building:
            return
        self._apply(key, read_param_widget(widget))
        self._mark_custom()

    def _apply(self, key: str, value):
        self._on_param_changed(key, value)

    def _mark_custom(self):
        if self.preset_combo.currentData() is not None:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(0)
            self.preset_combo.blockSignals(False)
            self.delete_preset_button.setEnabled(False)

    def _current_values(self) -> dict:
        return {key: read_param_widget(widget) for key, widget in self._param_inputs.items()}

    def _reload_presets(self, select: str = None):
        self.preset_combo.blockSignals(True)
        try:
            self.preset_combo.clear()
            self.preset_combo.addItem(_("Custom"), None)
            for name in mpv_effect_presets.list_presets(self.effect_id):
                self.preset_combo.addItem(name, name)
            if select:
                index = self.preset_combo.findData(select)
                self.preset_combo.setCurrentIndex(index if index >= 0 else 0)
            else:
                self.preset_combo.setCurrentIndex(0)
        finally:
            self.preset_combo.blockSignals(False)
        self.delete_preset_button.setEnabled(bool(self.preset_combo.currentData()))

    def _on_preset_selected(self, index: int):
        name = self.preset_combo.itemData(index)
        self.delete_preset_button.setEnabled(bool(name))
        if not name:
            return
        try:
            values = mpv_effect_presets.load_preset(self.effect_id, name)
        except OSError:
            return
        self._build_param_form(values)
        # Selecting a preset should be heard immediately, same as any other
        # live edit -- apply every value it carries right away rather than
        # waiting for the user to touch each field individually.
        for key, value in values.items():
            self._apply(key, value)

    def _on_new_preset(self):
        name, ok = QInputDialog.getText(self, _("New Preset"), _("Preset name:"))
        name = name.strip()
        if not ok or not name:
            return
        mpv_effect_presets.save_preset(self.effect_id, name, self._current_values())
        self._reload_presets(select=name)

    def _on_delete_preset(self):
        name = self.preset_combo.currentData()
        if not name:
            return
        if QMessageBox.question(
            self, _("Delete Preset"), _("Delete preset \"{name}\"?").format(name=name),
        ) != QMessageBox.StandardButton.Yes:
            return
        mpv_effect_presets.delete_preset(self.effect_id, name)
        self._reload_presets()

    def done(self, result):
        # Covers every way the dialog can close (Close button, Esc, [x]) --
        # fires the caller's one final persist regardless of exit path.
        super().done(result)
        if self._on_closed:
            self._on_closed()


class AudioFiltersWidget(QWidget):
    def __init__(self, parent=None, player=None):
        super().__init__(parent)
        self.player = player
        self._building = False
        self._names = []
        self._key_event_filter = KeyEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.list_tab = ListTabCtrl(self)
        layout.addWidget(self.list_tab)
        self.list_tab.tabLabels.itemChanged.connect(self._on_item_changed)
        self.list_tab.tabLabels.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_tab.tabLabels.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_tab.tabLabels.customContextMenuRequested.connect(self._show_context_menu)
        self._key_event_filter.install_on_widgets([self.list_tab.tabLabels])

    def set_player(self, player):
        self.player = player
        self._populate()

    def _populate(self, select_effect_id: str = None):
        if not self.player:
            return
        self._building = True
        try:
            self.list_tab.deleteTabs()
            self._names = []
            for effect_id in self.player.get_audio_filter_names():
                self._add_tab_for(effect_id)
            if self._names:
                target = self._names.index(select_effect_id) if select_effect_id in self._names else 0
                self.list_tab.tabLabels.setCurrentRow(target)
        finally:
            self._building = False

    def _add_tab_for(self, effect_id: str):
        effect = get_mpv_effect(effect_id)
        if effect is None:
            return
        spec = self.player.get_audio_filter_param_spec(effect_id)
        values = spec[1] if spec else {}
        enabled = self.player.is_audio_filter_enabled(effect_id)
        panel = EffectSummaryPanel(effect.label, self._summarize(effect_id, values), enabled, self)
        panel.editRequested.connect(lambda eid=effect_id: self._open_edit_popup(eid))
        self.list_tab.addTab(_(effect.label), panel)
        self._names.append(effect_id)
        tab = self.list_tab.getTab(len(self._names) - 1)
        if tab is not None:
            tab.setActivated(enabled)

    @staticmethod
    def _summarize(effect_id: str, values: dict) -> str:
        if effect_id == "convolution_reverb":
            path = values.get("impulse_response_path") or ""
            return _("IR file: {name}").format(name=os.path.basename(path)) if path else _("No IR file selected")
        if not values:
            return ""
        parts = [f"{key}={value}" for key, value in list(values.items())[:3]]
        return ", ".join(parts)

    def _refresh_tab_summary(self, effect_id: str):
        if effect_id not in self._names:
            return
        index = self._names.index(effect_id)
        tab = self.list_tab.getTab(index)
        panel = getattr(tab, "widget", None)
        if not isinstance(panel, EffectSummaryPanel):
            return
        spec = self.player.get_audio_filter_param_spec(effect_id)
        values = spec[1] if spec else {}
        panel.set_summary(self._summarize(effect_id, values))

    def _on_item_changed(self, item):
        if self._building or not self.player:
            return
        index = self.list_tab.tabLabels.row(item)
        if 0 <= index < len(self._names):
            enabled = item.checkState() == Qt.CheckState.Checked
            self.player.set_audio_filter_enabled(self._names[index], enabled)
            panel = getattr(item, "widget", None)
            if isinstance(panel, EffectSummaryPanel):
                panel.set_effect_enabled(enabled)

    def _on_item_double_clicked(self, item):
        index = self.list_tab.tabLabels.row(item)
        if 0 <= index < len(self._names):
            self._open_edit_popup(self._names[index])

    def _show_context_menu(self, position):
        item = self.list_tab.tabLabels.itemAt(position)
        menu = QMenu(self)
        add_action = menu.addAction(_("Add Effect..."))
        delete_action = menu.addAction(_("Delete"))
        delete_action.setEnabled(item is not None)
        menu.addSeparator()
        clear_action = menu.addAction(_("Clear All"))
        clear_action.setEnabled(len(self._names) > 0)

        chosen = menu.exec(self.list_tab.tabLabels.mapToGlobal(position))
        if chosen is None:
            return
        if chosen is add_action:
            self._add_effect()
        elif chosen is delete_action and item is not None:
            index = self.list_tab.tabLabels.row(item)
            if 0 <= index < len(self._names):
                self._delete_effect(self._names[index])
        elif chosen is clear_action:
            self._clear_all()

    def _add_effect(self):
        if not self.player:
            return
        existing = set(self.player.get_audio_filter_names())
        available = [effect for effect in MPV_EFFECTS if effect.id not in existing]
        if not available:
            QMessageBox.information(
                self, _("Add Effect"), _("All available effects have already been added.")
            )
            return

        dialog = CategorizedEffectPickerDialog(
            entries=available,
            categories_fn=lambda: _categories_for(available),
            get_entry_fn=get_mpv_effect,
            parent=self,
            title=_("Add Effect"),
            list_title=_("Available Effects"),
            default_file_dir=get_ir_dir(),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        effect_id, values = dialog.result_effect()
        if not effect_id:
            return
        self.player.add_audio_filter(effect_id, values, enabled=True)
        # Jump straight to the effect just added -- otherwise _populate()'s
        # default (row 0) can leave you looking at an unrelated tab while
        # the one you just added scrolls out of the tab strip, unseen.
        self._populate(select_effect_id=effect_id)

    def _delete_effect(self, effect_id: str):
        if not self.player:
            return
        self.player.remove_audio_filter(effect_id)
        self._populate()

    def _clear_all(self):
        if not self.player or not self._names:
            return
        if QMessageBox.question(
            self, _("Clear All Effects"), _("Remove all added effects?"),
        ) != QMessageBox.StandardButton.Yes:
            return
        self.player.clear_audio_filters()
        self._populate()

    def _open_edit_popup(self, effect_id: str):
        if not self.player:
            return
        spec = self.player.get_audio_filter_param_spec(effect_id)
        values = spec[1] if spec else {}

        def on_param_changed(key, value):
            # persist=False: this fires on every drag/tick while the popup
            # is open, so skip the disk write here and do exactly one on
            # close (on_closed below) -- matches the old inline panel's
            # real-time feel without a persist-per-keystroke cost.
            self.player.set_audio_filter_parameter(effect_id, key, value, persist=False)
            self._refresh_tab_summary(effect_id)

        def on_closed():
            self.player.persist_audio_effects_chain()

        popup = EffectParamPopup(effect_id, values, on_param_changed, on_closed, self)
        popup.exec()
        self._refresh_tab_summary(effect_id)

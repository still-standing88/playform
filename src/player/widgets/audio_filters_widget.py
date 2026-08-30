import os

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
                                QPushButton, QComboBox, QListWidget, QListWidgetItem,
                                QMenu, QMessageBox, QInputDialog, QDialog)
from PySide6.QtCore import Qt

from gui_controls.player_key_event_filter import KeyEventFilter
from gui_controls.param_widgets import make_param_widget, read_param_widget, connect_param_widget_changed
from gui_controls.effect_dialogs import EffectSelectionDialog, EffectEditDialog
from media_core.av_play.mpv_effects_catalog import MPV_EFFECTS, get_mpv_effect
from media_core.av_play import mpv_effect_presets
from utilities.functions import get_ir_dir

EFFECT_ID_ROLE = Qt.ItemDataRole.UserRole


def _categories_for(entries):
    seen = []
    for entry in entries:
        if entry.category not in seen:
            seen.append(entry.category)
    return seen


class AudioFiltersWidget(QWidget):
    """Vertical, full-width list of added effects (one row per effect) --
    not ListTabCtrl's horizontal tab strip this replaced. That strip lays
    every tab out in a single unbroken row with no wrapping, so as effects
    were added (especially ones with long labels, e.g. "Noise Reduction
    (FFT)") later items got pushed off past the narrow accordion panel's
    width, reachable only via a cramped horizontal scrollbar -- and since
    the strip fully rebuilds on every add/remove, a given effect's position
    in it kept shifting around too. A plain top-to-bottom QListWidget (the
    same pattern FavoritesWidget/PlaylistListCtrl already use elsewhere in
    this app) scrolls vertically instead, which this narrow panel is
    already well suited for, and doesn't have either problem. This only
    works because parameter editing lives in a separate dialog (see
    gui_controls.effect_dialogs.EffectEditDialog) rather than a per-tab
    inline form -- there's no separate "content area below the strip" to
    manage anymore, just checkable rows, edited via click or the context
    menu.
    """

    def __init__(self, parent=None, player=None):
        super().__init__(parent)
        self.player = player
        self._building = False
        self._key_event_filter = KeyEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        add_row = QHBoxLayout()
        add_row.addStretch()
        self.add_effect_button = QPushButton(_("Add Effect..."), self)
        self.add_effect_button.setToolTip(_("Add an audio effect"))
        self.add_effect_button.clicked.connect(self._add_effect)
        add_row.addWidget(self.add_effect_button)
        layout.addLayout(add_row)
        self.effects_list = QListWidget(self)
        self.effects_list.setAlternatingRowColors(True)
        self.effects_list.setAccessibleName(_("Added audio effects"))
        self.effects_list.setToolTip(_("Double-click an effect to edit its parameters"))
        # Wrap long labels/summaries within the available width instead of
        # extending the row past it -- an unwrapped long line (e.g. "Noise
        # Reduction (FFT)" plus a multi-param summary) would otherwise force
        # a horizontal scrollbar, the exact problem this vertical list
        # replaced ListTabCtrl's horizontal tab strip to get away from.
        self.effects_list.setWordWrap(True)
        self.effects_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.effects_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        layout.addWidget(self.effects_list)
        self.effects_list.itemChanged.connect(self._on_item_changed)
        self.effects_list.itemClicked.connect(self._on_item_clicked)
        self.effects_list.itemActivated.connect(self._on_item_clicked)
        self.effects_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.effects_list.customContextMenuRequested.connect(self._show_context_menu)
        self._key_event_filter.install_on_widgets([self.effects_list, self.add_effect_button])

    def set_player(self, player):
        self.player = player
        self._populate()

    def set_media_available(self, available: bool):
        self.setEnabled(available)

    def _populate(self, select_effect_id: str = None):
        if not self.player:
            return
        self._building = True
        try:
            self.effects_list.clear()
            select_row = 0
            for effect_id in self.player.get_audio_filter_names():
                self._add_row_for(effect_id)
                if effect_id == select_effect_id:
                    select_row = self.effects_list.count() - 1
            if self.effects_list.count():
                self.effects_list.setCurrentRow(select_row)
        finally:
            self._building = False

    def _add_row_for(self, effect_id: str):
        effect = get_mpv_effect(effect_id)
        if effect is None:
            return
        spec = self.player.get_audio_filter_param_spec(effect_id)
        values = spec[1] if spec else {}
        enabled = self.player.is_audio_filter_enabled(effect_id)

        item = QListWidgetItem(self._row_text(effect.label, effect_id, values))
        item.setData(EFFECT_ID_ROLE, effect_id)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
        self.effects_list.addItem(item)

    @staticmethod
    def _row_text(effect_label: str, effect_id: str, values: dict) -> str:
        summary = AudioFiltersWidget._summarize(effect_id, values)
        return f"{effect_label}\n{summary}" if summary else effect_label

    @staticmethod
    def _summarize(effect_id: str, values: dict) -> str:
        if effect_id == "convolution_reverb":
            path = values.get("impulse_response_path") or ""
            return _("IR file: {name}").format(name=os.path.basename(path)) if path else _("No IR file selected")
        if not values:
            return ""
        parts = [f"{key}={value}" for key, value in list(values.items())[:3]]
        return ", ".join(parts)

    def _find_item(self, effect_id: str):
        for row in range(self.effects_list.count()):
            item = self.effects_list.item(row)
            if item.data(EFFECT_ID_ROLE) == effect_id:
                return item
        return None

    def _refresh_row(self, effect_id: str):
        item = self._find_item(effect_id)
        if item is None or not self.player:
            return
        effect = get_mpv_effect(effect_id)
        spec = self.player.get_audio_filter_param_spec(effect_id)
        values = spec[1] if spec else {}
        self._building = True
        try:
            item.setText(self._row_text(effect.label, effect_id, values))
        finally:
            self._building = False

    def _on_item_changed(self, item):
        if self._building or not self.player:
            return
        effect_id = item.data(EFFECT_ID_ROLE)
        if effect_id:
            enabled = item.checkState() == Qt.CheckState.Checked
            self.player.set_audio_filter_enabled(effect_id, enabled)

    def _on_item_clicked(self, item):
        effect_id = item.data(EFFECT_ID_ROLE)
        if effect_id and item.checkState() == Qt.CheckState.Checked:
            self._open_edit_popup(effect_id)

    def _show_context_menu(self, position):
        item = self.effects_list.itemAt(position)
        menu = QMenu(self)
        add_action = menu.addAction(_("Add Effect..."))
        edit_action = menu.addAction(_("Edit Parameters..."))
        edit_action.setEnabled(item is not None)
        delete_action = menu.addAction(_("Delete"))
        delete_action.setEnabled(item is not None)
        menu.addSeparator()
        clear_action = menu.addAction(_("Clear All"))
        clear_action.setEnabled(self.effects_list.count() > 0)

        chosen = menu.exec(self.effects_list.mapToGlobal(position))
        if chosen is None:
            return
        if chosen is add_action:
            self._add_effect()
        elif chosen is edit_action and item is not None:
            effect_id = item.data(EFFECT_ID_ROLE)
            if effect_id:
                self._open_edit_popup(effect_id)
        elif chosen is delete_action and item is not None:
            effect_id = item.data(EFFECT_ID_ROLE)
            if effect_id:
                self._delete_effect(effect_id)
        elif chosen is clear_action:
            self._clear_all()

    def _add_effect(self):
        if not self.player:
            return
        existing = set(self.player.get_audio_filter_names())
        addable = set(self.player.get_addable_audio_filter_ids())
        available = [effect for effect in MPV_EFFECTS
                     if effect.id not in existing and effect.id in addable]
        if not available:
            QMessageBox.information(
                self, _("Add Effect"), _("All available effects have already been added.")
            )
            return

        dialog = EffectSelectionDialog(
            entries=available,
            categories_fn=lambda: _categories_for(available),
            get_entry_fn=get_mpv_effect,
            parent=self,
            title=_("Add Effect"),
            list_title=_("Available Effects"),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        effect_id, values = dialog.result_effect()
        if not effect_id:
            return
        self.player.add_audio_filter(effect_id, values, enabled=True)
        # Jump straight to the effect just added and scroll it into view --
        # otherwise _populate()'s default (row 0) can leave you looking at
        # an unrelated row while the one you just added is off-screen.
        self._populate(select_effect_id=effect_id)

    def _delete_effect(self, effect_id: str):
        if not self.player:
            return
        self.player.remove_audio_filter(effect_id)
        self._populate()

    def _clear_all(self):
        if not self.player or not self.effects_list.count():
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
        effect = get_mpv_effect(effect_id)
        if effect is None:
            return
        spec = self.player.get_audio_filter_param_spec(effect_id)
        values = spec[1] if spec else {}
        original = dict(values)

        def _apply_live(key, value):
            self.player.set_audio_filter_parameter(effect_id, key, value, persist=False)

        dialog = EffectEditDialog(
            effect, values, parent=self,
            preset_backend=mpv_effect_presets,
            default_file_dir=get_ir_dir(),
            on_param_changed=_apply_live,
        )
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        # Every edit was already pushed to the live filter as it was made, so
        # OK only needs to persist the chain -- while Cancel has to actively
        # put the pre-dialog values back, since "not saved" no longer implies
        # "never applied".
        final_values = dialog.current_values() if accepted else original
        for key, value in final_values.items():
            self.player.set_audio_filter_parameter(effect_id, key, value, persist=False)
        if accepted:
            self.player.persist_audio_effects_chain()
        self._refresh_row(effect_id)

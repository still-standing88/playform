from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton
from PySide6.QtCore import Qt

from media_core.ffmpeg.effects_catalog import get_effect
from tools.ffmpeg.batch_converter.effect_picker_dialog import EffectPickerDialog

EFFECT_ID_ROLE = Qt.ItemDataRole.UserRole
EFFECT_VALUES_ROLE = Qt.ItemDataRole.UserRole + 1


class ProcessingTab(QWidget):
    """Shows only the effects actually applied to this conversion, in application order.

    Browsing the catalog and configuring parameters both happen in `EffectPickerDialog`,
    opened via the Add Edit/Add Filter buttons (or Edit Selected, to reconfigure an
    already-applied entry) — this list is the resulting chain, not a catalog browser.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.applied_list = QListWidget(self)
        self.applied_list.setAccessibleName(_("Applied edits and filters"))
        self.applied_list.setAccessibleDescription(
            _("Effects that will be applied to this conversion, in order. Use Add Edit or "
              "Add Filter to add more; select an entry to edit or remove it.")
        )
        self.applied_list.itemSelectionChanged.connect(self._update_button_state)
        self.applied_list.itemDoubleClicked.connect(lambda _item: self._on_edit_selected())
        layout.addWidget(self.applied_list)

        button_row = QHBoxLayout()
        self.add_edit_button = QPushButton(_("Add Edit..."), self)
        self.add_filter_button = QPushButton(_("Add Filter..."), self)
        self.edit_selected_button = QPushButton(_("Edit Selected..."), self)
        self.remove_button = QPushButton(_("Remove Selected"), self)
        self.add_edit_button.clicked.connect(lambda: self._open_picker("edits"))
        self.add_filter_button.clicked.connect(lambda: self._open_picker("filters"))
        self.edit_selected_button.clicked.connect(self._on_edit_selected)
        self.remove_button.clicked.connect(self._on_remove_selected)
        button_row.addWidget(self.add_edit_button)
        button_row.addWidget(self.add_filter_button)
        button_row.addStretch()
        button_row.addWidget(self.edit_selected_button)
        button_row.addWidget(self.remove_button)
        layout.addLayout(button_row)

        self._update_button_state()

    def _update_button_state(self):
        has_selection = self.applied_list.currentItem() is not None
        self.edit_selected_button.setEnabled(has_selection)
        self.remove_button.setEnabled(has_selection)

    def _make_item(self, effect_id: str, values: dict) -> QListWidgetItem:
        item = QListWidgetItem(get_effect(effect_id).label)
        item.setData(EFFECT_ID_ROLE, effect_id)
        item.setData(EFFECT_VALUES_ROLE, values)
        return item

    def _open_picker(self, branch: str):
        dialog = EffectPickerDialog(branch, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            effect_id, values = dialog.result_effect()
            if effect_id:
                self.applied_list.addItem(self._make_item(effect_id, values))
                self._update_button_state()

    def _on_edit_selected(self):
        item = self.applied_list.currentItem()
        if item is None:
            return

        effect_id = item.data(EFFECT_ID_ROLE)
        values = item.data(EFFECT_VALUES_ROLE)
        branch = get_effect(effect_id).branch
        dialog = EffectPickerDialog(branch, self, initial_effect_id=effect_id, initial_values=values)
        if dialog.exec() == dialog.DialogCode.Accepted:
            new_effect_id, new_values = dialog.result_effect()
            if new_effect_id:
                item.setText(get_effect(new_effect_id).label)
                item.setData(EFFECT_ID_ROLE, new_effect_id)
                item.setData(EFFECT_VALUES_ROLE, new_values)

    def _on_remove_selected(self):
        for item in self.applied_list.selectedItems():
            self.applied_list.takeItem(self.applied_list.row(item))
        self._update_button_state()

    def clear_all(self):
        self.applied_list.clear()
        self._update_button_state()

    def applied_effects(self) -> list:
        return [
            (self.applied_list.item(i).data(EFFECT_ID_ROLE), self.applied_list.item(i).data(EFFECT_VALUES_ROLE))
            for i in range(self.applied_list.count())
        ]

    def load_applied_effects(self, entries: list):
        self.clear_all()
        for effect_id, values in entries:
            self.applied_list.addItem(self._make_item(effect_id, values))
        self._update_button_state()

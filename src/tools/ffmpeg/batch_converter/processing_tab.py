from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from media_core.ffmpeg.effects_catalog import EFFECTS, effects_for_branch, categories_for_branch, get_effect
from tools.ffmpeg.batch_converter.effect_dialog import EffectParameterDialog

EFFECT_ID_ROLE = Qt.ItemDataRole.UserRole
EFFECT_VALUES_ROLE = Qt.ItemDataRole.UserRole + 1

_BRANCH_LABELS = {"edits": "Edits", "filters": "Filters"}


class ProcessingTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._leaf_items: dict = {}
        self._build_ui()
        self._populate_tree()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(1)
        self.tree.setHeaderLabels([_("Edits & Filters")])
        self.tree.itemSelectionChanged.connect(self._update_button_state)
        layout.addWidget(self.tree)

        button_row = QHBoxLayout()
        self.add_edit_button = QPushButton(_("Add Effect..."), self)
        self.remove_button = QPushButton(_("Remove Effect"), self)
        self.add_edit_button.clicked.connect(self._on_add_or_edit)
        self.remove_button.clicked.connect(self._on_remove)
        button_row.addWidget(self.add_edit_button)
        button_row.addWidget(self.remove_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        self._update_button_state()

    def _populate_tree(self):
        for branch in ("edits", "filters"):
            branch_item = QTreeWidgetItem([_(_BRANCH_LABELS[branch])])
            self.tree.addTopLevelItem(branch_item)
            branch_item.setExpanded(True)

            for category in categories_for_branch(branch):
                category_item = QTreeWidgetItem([_(category)])
                branch_item.addChild(category_item)

                for effect in effects_for_branch(branch):
                    if effect.category != category:
                        continue
                    leaf = QTreeWidgetItem([effect.label])
                    leaf.setData(0, EFFECT_ID_ROLE, effect.id)
                    category_item.addChild(leaf)
                    self._leaf_items[effect.id] = leaf

    def _update_button_state(self):
        item = self._selected_leaf()
        if item is None:
            self.add_edit_button.setEnabled(False)
            self.add_edit_button.setText(_("Add Effect..."))
            self.remove_button.setEnabled(False)
            return

        self.add_edit_button.setEnabled(True)
        applied = item.data(0, EFFECT_VALUES_ROLE) is not None
        self.add_edit_button.setText(_("Edit Effect...") if applied else _("Add Effect..."))
        self.remove_button.setEnabled(applied)

    def _selected_leaf(self):
        items = self.tree.selectedItems()
        if not items:
            return None
        item = items[0]
        return item if item.data(0, EFFECT_ID_ROLE) else None

    def _mark_applied(self, item: QTreeWidgetItem, applied: bool):
        font = QFont(item.font(0))
        font.setBold(applied)
        item.setFont(0, font)
        effect_id = item.data(0, EFFECT_ID_ROLE)
        label = get_effect(effect_id).label
        item.setText(0, f"✓ {label}" if applied else label)

    def _on_add_or_edit(self):
        item = self._selected_leaf()
        if item is None:
            return

        effect = get_effect(item.data(0, EFFECT_ID_ROLE))
        current_values = item.data(0, EFFECT_VALUES_ROLE)
        dialog = EffectParameterDialog(effect, current_values, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            item.setData(0, EFFECT_VALUES_ROLE, dialog.values())
            self._mark_applied(item, True)
            self._update_button_state()

    def _on_remove(self):
        item = self._selected_leaf()
        if item is None:
            return
        item.setData(0, EFFECT_VALUES_ROLE, None)
        self._mark_applied(item, False)
        self._update_button_state()

    def clear_all(self):
        for item in self._leaf_items.values():
            item.setData(0, EFFECT_VALUES_ROLE, None)
            self._mark_applied(item, False)
        self._update_button_state()

    def applied_effects(self) -> list:
        result = []
        for effect in EFFECTS:
            item = self._leaf_items.get(effect.id)
            if item is None:
                continue
            values = item.data(0, EFFECT_VALUES_ROLE)
            if values is not None:
                result.append((effect.id, values))
        return result

    def load_applied_effects(self, entries: list):
        self.clear_all()
        for effect_id, values in entries:
            item = self._leaf_items.get(effect_id)
            if item is None:
                continue
            item.setData(0, EFFECT_VALUES_ROLE, values)
            self._mark_applied(item, True)
        self._update_button_state()

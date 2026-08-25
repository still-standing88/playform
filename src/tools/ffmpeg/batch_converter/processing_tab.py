from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QDialog, QMenu
from PySide6.QtCore import Qt

from media_core.ffmpeg.effects_catalog import get_effect
from tools.ffmpeg.batch_converter.effect_picker_dialog import EffectPickerDialog
from gui_controls.effect_dialogs import EffectEditDialog

EFFECT_ID_ROLE = Qt.ItemDataRole.UserRole
EFFECT_VALUES_ROLE = Qt.ItemDataRole.UserRole + 1


class ProcessingTab(QWidget):
    """Shows only the effects actually applied to this conversion, in application order.

    Browsing the catalog and configuring parameters both happen in `EffectPickerDialog`,
    opened via the Add Edit/Add Filter buttons; editing and removing entries happens in
    the list's context menu (or double-click / Delete) -- this list is the resulting
    chain, not a catalog browser.
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
              "Add Filter to add more; open the context menu on an entry to edit, remove, "
              "reorder it, or press Delete to remove it.")
        )
        self.applied_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.applied_list.customContextMenuRequested.connect(self._show_context_menu)
        self.applied_list.itemDoubleClicked.connect(lambda _item: self._on_edit_selected())
        layout.addWidget(self.applied_list)

        button_row = QHBoxLayout()
        self.add_edit_button = QPushButton(_("Add Edit..."), self)
        self.add_filter_button = QPushButton(_("Add Filter..."), self)
        self.add_edit_button.clicked.connect(lambda: self._open_picker("edits"))
        self.add_filter_button.clicked.connect(lambda: self._open_picker("filters"))
        button_row.addWidget(self.add_edit_button)
        button_row.addWidget(self.add_filter_button)
        button_row.addStretch()
        layout.addLayout(button_row)

    def _show_context_menu(self, position):
        menu = QMenu(self)
        has_selection = self.applied_list.currentItem() is not None

        edit_action = menu.addAction(_("Edit..."))
        edit_action.setEnabled(has_selection)
        edit_action.triggered.connect(self._on_edit_selected)

        remove_action = menu.addAction(_("Remove"))
        remove_action.setEnabled(has_selection)
        remove_action.triggered.connect(self._on_remove_selected)

        move_up_action = menu.addAction(_("Move Up"))
        move_up_action.setEnabled(self._can_move(-1))
        move_up_action.triggered.connect(lambda: self._move_selected(-1))

        move_down_action = menu.addAction(_("Move Down"))
        move_down_action.setEnabled(self._can_move(1))
        move_down_action.triggered.connect(lambda: self._move_selected(1))

        menu.addSeparator()
        clear_action = menu.addAction(_("Clear All"))
        clear_action.setEnabled(self.applied_list.count() > 0)
        clear_action.triggered.connect(self.clear_all)

        menu.exec(self.applied_list.mapToGlobal(position))

    def _can_move(self, direction: int) -> bool:
        row = self.applied_list.currentRow()
        return 0 <= row < self.applied_list.count() and 0 <= row + direction < self.applied_list.count()

    def _move_selected(self, direction: int):
        row = self.applied_list.currentRow()
        if not self._can_move(direction):
            return
        item = self.applied_list.takeItem(row)
        self.applied_list.insertItem(row + direction, item)
        self.applied_list.setCurrentItem(item)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self._on_remove_selected()
            return
        super().keyPressEvent(event)

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

    def _on_edit_selected(self):
        item = self.applied_list.currentItem()
        if item is None:
            return

        effect_id = item.data(EFFECT_ID_ROLE)
        values = item.data(EFFECT_VALUES_ROLE)
        effect = get_effect(effect_id)
        dialog = EffectEditDialog(effect, values, parent=self, title=_("Edit {effect}").format(effect=effect.label))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item.setData(EFFECT_VALUES_ROLE, dialog.current_values())

    def _on_remove_selected(self):
        for item in self.applied_list.selectedItems():
            self.applied_list.takeItem(self.applied_list.row(item))

    def clear_all(self):
        self.applied_list.clear()

    def applied_effects(self) -> list:
        return [
            (self.applied_list.item(i).data(EFFECT_ID_ROLE), self.applied_list.item(i).data(EFFECT_VALUES_ROLE))
            for i in range(self.applied_list.count())
        ]

    def load_applied_effects(self, entries: list):
        self.clear_all()
        for effect_id, values in entries:
            self.applied_list.addItem(self._make_item(effect_id, values))

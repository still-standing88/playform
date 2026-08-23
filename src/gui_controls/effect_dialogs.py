from PySide6.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QFormLayout, QWidget,
                                QLabel, QTreeView, QPushButton, QComboBox, QInputDialog,
                                QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem

from gui_controls.param_widgets import make_param_widget, read_param_widget

EFFECT_ID_ROLE = Qt.ItemDataRole.UserRole


class EffectSelectionDialog(QDialog):
    """Effect chooser dialog: ONLY a categorized treeview plus OK/Cancel.
    Parameter configuration deliberately lives in EffectEditDialog instead,
    so picking and editing are two separate steps."""

    def __init__(self, entries: list, categories_fn, get_entry_fn, parent=None,
                 title: str = "", list_title: str = ""):
        super().__init__(parent)
        self._entries = entries
        self._get_entry_fn = get_entry_fn
        self._selected_id = None

        self.setWindowTitle(title or _("Add Effect"))
        self.setMinimumSize(360, 420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(_(list_title or _("Available Effects")), self))

        self.catalog_model = QStandardItemModel(self)
        self.catalog_tree = QTreeView(self)
        self.catalog_tree.setModel(self.catalog_model)
        self.catalog_tree.setHeaderHidden(True)
        self.catalog_tree.setAccessibleName(_(list_title or _("Available Effects")))
        self.catalog_tree.doubleClicked.connect(self.accept)
        self._populate_catalog(categories_fn)
        layout.addWidget(self.catalog_tree)

        buttons = QHBoxLayout()
        buttons.addStretch()
        ok_button = QPushButton(_("OK"), self)
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton(_("Cancel"), self)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        self.catalog_tree.selectionModel().currentChanged.connect(self._on_selection_changed)
        self._select_first_available()

    def _populate_catalog(self, categories_fn):
        seen_ids = set()
        for category in categories_fn():
            category_item = QStandardItem(category)
            category_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            for entry in self._entries:
                if entry.category != category or entry.id in seen_ids:
                    continue
                seen_ids.add(entry.id)
                leaf = QStandardItem(entry.label)
                leaf.setData(entry.id, EFFECT_ID_ROLE)
                category_item.appendRow(leaf)
            if category_item.rowCount():
                self.catalog_model.appendRow(category_item)

    def _select_first_available(self):
        for i in range(self.catalog_model.rowCount()):
            category_item = self.catalog_model.item(i)
            if category_item.rowCount() > 0:
                self.catalog_tree.setCurrentIndex(category_item.child(0).index())
                return

    def _on_selection_changed(self, current, _previous):
        entry_id = current.data(EFFECT_ID_ROLE) if current.isValid() else None
        self._selected_id = entry_id

    def selected_effect_id(self):
        return self._selected_id

    def result_effect(self):
        if not self._selected_id:
            return None, {}
        entry = self._get_entry_fn(self._selected_id)
        values = {param.key: param.default for param in entry.params}
        return self._selected_id, values


class EffectEditDialog(QDialog):
    """Parameter editor for one fixed effect: preset row (combo + New/Delete)
    on top, adaptive parameter form below. There is deliberately no way to
    change which effect is being edited here -- selection happens in
    EffectSelectionDialog.

    `preset_backend` is an object exposing list_presets(effect_id),
    load_preset(effect_id, name), save_preset(effect_id, name, values) and
    delete_preset(effect_id, name); pass None to hide the preset row."""

    def __init__(self, effect, values: dict, parent=None, title: str = "",
                 preset_backend=None, default_file_dir: str = ""):
        super().__init__(parent)
        self._effect = effect
        self._preset_backend = preset_backend
        self._param_inputs: dict = {}
        self._building = False
        self._default_file_dir = default_file_dir

        self.setWindowTitle(title or _("Edit {effect}").format(effect=effect.label))
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        if self._preset_backend is not None:
            preset_row = QHBoxLayout()
            preset_row.addWidget(QLabel(_("Preset"), self))
            self.preset_combo = QComboBox(self)
            preset_row.addWidget(self.preset_combo, 1)
            self.new_preset_button = QPushButton(_("New..."), self)
            self.delete_preset_button = QPushButton(_("Delete"), self)
            preset_row.addWidget(self.new_preset_button)
            preset_row.addWidget(self.delete_preset_button)
            layout.addLayout(preset_row)
            self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
            self.new_preset_button.clicked.connect(self._on_new_preset)
            self.delete_preset_button.clicked.connect(self._on_delete_preset)
        else:
            self.preset_combo = None

        self.param_form_container = QWidget(self)
        self.param_form = QFormLayout(self.param_form_container)
        layout.addWidget(self.param_form_container)

        buttons = QHBoxLayout()
        buttons.addStretch()
        ok_button = QPushButton(_("OK"), self)
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton(_("Cancel"), self)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        self._build_param_form(values)
        if self._preset_backend is not None:
            self._reload_presets()

    def _build_param_form(self, values: dict):
        while self.param_form.rowCount():
            self.param_form.removeRow(0)
        self._param_inputs.clear()

        if not self._effect.params:
            self.param_form.addRow(QLabel(_("This effect has no configurable parameters.")))
            return

        self._building = True
        try:
            for param in self._effect.params:
                current_value = values.get(param.key, param.default)
                widget = make_param_widget(
                    self, param.kind, param.choices, param.value_range, current_value, param.suffix,
                    default_dir=self._default_file_dir,
                )
                self._param_inputs[param.key] = widget
                self.param_form.addRow(param.label, widget)
        finally:
            self._building = False

    def _reload_presets(self, select: str = None):
        self.preset_combo.blockSignals(True)
        try:
            self.preset_combo.clear()
            self.preset_combo.addItem(_("Custom"), None)
            for name in self._preset_backend.list_presets(self._effect.id):
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
            values = self._preset_backend.load_preset(self._effect.id, name)
        except OSError:
            return
        self._build_param_form(values)

    def _on_new_preset(self):
        name, ok = QInputDialog.getText(self, _("New Preset"), _("Preset name:"))
        name = name.strip()
        if not ok or not name:
            return
        self._preset_backend.save_preset(self._effect.id, name, self.current_values())
        self._reload_presets(select=name)

    def _on_delete_preset(self):
        name = self.preset_combo.currentData()
        if not name:
            return
        if QMessageBox.question(
            self, _("Delete Preset"), _("Delete preset \"{name}\"?").format(name=name),
        ) != QMessageBox.StandardButton.Yes:
            return
        self._preset_backend.delete_preset(self._effect.id, name)
        self._reload_presets()

    def current_values(self) -> dict:
        return {key: read_param_widget(widget) for key, widget in self._param_inputs.items()}

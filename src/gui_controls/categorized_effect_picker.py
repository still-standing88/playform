from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QFormLayout, QWidget, QLabel,
    QTreeWidget, QTreeWidgetItem, QPushButton
)
from PySide6.QtCore import Qt

from gui_controls.param_widgets import make_param_widget, read_param_widget

EFFECT_ID_ROLE = Qt.ItemDataRole.UserRole


class CategorizedEffectPickerDialog(QDialog):
    """Pick an entry from a categorized catalog and configure its parameters
    in one adaptive dialog: the parameter form on the right rebuilds to
    match whichever entry is currently selected on the left, so choosing
    and configuring happen in a single step.

    Generalized over any catalog whose entries expose `id`, `label`,
    `category`, and `params` (each param exposing `key`, `label`, `kind`,
    `default`, `value_range`, `choices`, `suffix`) -- both
    `media_core.ffmpeg.effects_catalog.EffectDefinition` (Batch Converter)
    and `media_core.av_play.mpv_effects_catalog.MPVEffectDefinition` (live
    player) satisfy this shape, so both tools share this one dialog.

    `show_tree=False` collapses the dialog into a params-only editor for a
    single, already-known entry (used for the live player's "Edit
    Parameters..." popup, where the effect is already fixed and browsing
    categories again would just be noise).
    """

    def __init__(self, entries: list, categories_fn, get_entry_fn, parent=None,
                 initial_id: str = None, initial_values: dict = None,
                 title: str = "", list_title: str = "", show_tree: bool = True,
                 default_file_dir: str = ""):
        super().__init__(parent)
        self._entries = entries
        self._categories_fn = categories_fn
        self._get_entry_fn = get_entry_fn
        self._initial_id = initial_id
        self._initial_values = dict(initial_values or {})
        self._param_inputs: dict = {}
        self._current_entry = None
        self._default_file_dir = default_file_dir

        self.setWindowTitle(title or _("Add Effect"))
        self.setMinimumSize(600, 420)
        self._build_ui(list_title or _("Available Effects"), show_tree)

        if initial_id:
            self._select_entry(initial_id)
        elif show_tree:
            self._select_first_available()

    def _build_ui(self, list_title: str, show_tree: bool):
        layout = QHBoxLayout(self)

        if show_tree:
            left_widget = QWidget(self)
            left_layout = QVBoxLayout(left_widget)
            left_layout.addWidget(QLabel(_(list_title), self))
            self.catalog_tree = QTreeWidget(self)
            self.catalog_tree.setHeaderHidden(True)
            self.catalog_tree.setAccessibleName(_(list_title))
            self.catalog_tree.setAccessibleDescription(
                _("Select an effect to configure its parameters on the right, then choose OK to add it.")
            )
            self._populate_catalog()
            self.catalog_tree.currentItemChanged.connect(self._on_selection_changed)
            left_layout.addWidget(self.catalog_tree)
            layout.addWidget(left_widget, stretch=1)
        else:
            self.catalog_tree = None

        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        self.effect_title_label = QLabel(self)
        title_font = self.effect_title_label.font()
        title_font.setBold(True)
        self.effect_title_label.setFont(title_font)
        right_layout.addWidget(self.effect_title_label)

        self.param_form_container = QWidget(self)
        self.param_form = QFormLayout(self.param_form_container)
        right_layout.addWidget(self.param_form_container)
        right_layout.addStretch()

        button_row = QHBoxLayout()
        self.ok_button = QPushButton(_("OK"), self)
        self.ok_button.setEnabled(False)
        self.cancel_button = QPushButton(_("Cancel"), self)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        button_row.addStretch()
        button_row.addWidget(self.ok_button)
        button_row.addWidget(self.cancel_button)
        right_layout.addLayout(button_row)

        layout.addWidget(right_widget, stretch=1)

    def _populate_catalog(self):
        for category in self._categories_fn():
            category_item = QTreeWidgetItem([_(category)])
            category_item.setFlags(category_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.catalog_tree.addTopLevelItem(category_item)
            category_item.setExpanded(True)

            for entry in self._entries:
                if entry.category != category:
                    continue
                leaf = QTreeWidgetItem([entry.label])
                leaf.setData(0, EFFECT_ID_ROLE, entry.id)
                category_item.addChild(leaf)

    def _select_entry(self, entry_id: str):
        if self.catalog_tree is None:
            self._current_entry = self._get_entry_fn(entry_id)
            if self._current_entry:
                self.ok_button.setEnabled(True)
                self.effect_title_label.setText(self._current_entry.label)
                self._rebuild_param_form()
            return

        for i in range(self.catalog_tree.topLevelItemCount()):
            category_item = self.catalog_tree.topLevelItem(i)
            for j in range(category_item.childCount()):
                child = category_item.child(j)
                if child.data(0, EFFECT_ID_ROLE) == entry_id:
                    self.catalog_tree.setCurrentItem(child)
                    return

    def _select_first_available(self):
        for i in range(self.catalog_tree.topLevelItemCount()):
            category_item = self.catalog_tree.topLevelItem(i)
            if category_item.childCount() > 0:
                self.catalog_tree.setCurrentItem(category_item.child(0))
                return

    def _on_selection_changed(self, current, _previous):
        entry_id = current.data(0, EFFECT_ID_ROLE) if current else None
        if not entry_id:
            self._current_entry = None
            self.ok_button.setEnabled(False)
            self.effect_title_label.setText("")
            self._clear_param_form()
            return

        self._current_entry = self._get_entry_fn(entry_id)
        self.ok_button.setEnabled(True)
        self.effect_title_label.setText(self._current_entry.label)
        self._rebuild_param_form()

    def _clear_param_form(self):
        while self.param_form.rowCount():
            self.param_form.removeRow(0)
        self._param_inputs.clear()

    def _rebuild_param_form(self):
        self._clear_param_form()

        if not self._current_entry.params:
            self.param_form.addRow(QLabel(_("This effect has no configurable parameters.")))
            return

        values = self._initial_values if self._current_entry.id == self._initial_id else {}
        for param in self._current_entry.params:
            current_value = values.get(param.key, param.default)
            widget = make_param_widget(
                self, param.kind, param.choices, param.value_range, current_value, param.suffix,
                default_dir=self._default_file_dir,
            )
            self._param_inputs[param.key] = widget
            self.param_form.addRow(param.label, widget)

    def result_effect(self):
        if not self._current_entry:
            return None, {}
        values = {key: read_param_widget(widget) for key, widget in self._param_inputs.items()}
        return self._current_entry.id, values

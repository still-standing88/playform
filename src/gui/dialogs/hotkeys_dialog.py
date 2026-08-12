from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLineEdit, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QKeySequence
from app_config import key_config


class HotkeyCaptureEdit(QLineEdit):
    """Captures a single key combination and finalizes it on key-release,
    instead of QKeySequenceEdit's press-then-Enter-to-accept model.
    QKeySequenceEdit records Return as part of the chord itself -- pressing
    Q then Enter to "confirm" actually got recorded as the two-key chord
    "Q, Return" rather than accepting "Q". Release IS accept here: holding
    modifiers doesn't finalize anything by itself, but releasing the first
    non-modifier key immediately commits the combo captured up to that
    point, so there's no separate confirm keystroke to be ambiguous about.
    Escape cancels without committing.
    """

    sequenceCaptured = Signal(str)
    cancelled = Signal()

    _MODIFIER_KEYS = {
        Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt,
        Qt.Key.Key_Meta, Qt.Key.Key_AltGr,
    }

    def __init__(self, initial_sequence="", parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._captured_key = None
        self._captured_modifiers = Qt.KeyboardModifier.NoModifier
        self._finalized = False
        if initial_sequence:
            self.setText(initial_sequence)

    def keyPressEvent(self, event):
        if self._finalized:
            return
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.cancelled.emit()
            return
        if key in self._MODIFIER_KEYS or key == Qt.Key.Key_unknown:
            self.setText(self._preview_text(event.modifiers(), None))
            return
        self._captured_key = key
        self._captured_modifiers = event.modifiers()
        self.setText(self._preview_text(event.modifiers(), key))

    def keyReleaseEvent(self, event):
        key = event.key()
        if key in self._MODIFIER_KEYS:
            return
        if self._captured_key is None or self._finalized:
            return
        self._finalized = True
        text = self._preview_text(self._captured_modifiers, self._captured_key)
        self.setText(text)
        self.sequenceCaptured.emit(text)

    @staticmethod
    def _preview_text(modifiers, key):
        # PySide6's Qt.KeyboardModifier flag object doesn't convert via
        # int() directly in every binding version -- .value is the
        # reliable way to get the underlying integer to OR with the key.
        seq_int = int(getattr(modifiers, "value", modifiers))
        if key is not None:
            seq_int |= key
        if seq_int == 0:
            return ""
        return QKeySequence(seq_int).toString(QKeySequence.SequenceFormat.PortableText) or ""


class HotkeysDialog(QDialog):
    def __init__(self, parent=None, reset_callback=None):
        super().__init__(parent)
        self.reset_callback = reset_callback
        self.current_editor = None
        self.current_editor_item = None
        self.setWindowTitle(_("Hotkeys Configuration"))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(700, 500)
        self.setMinimumSize(600, 400)
        self.setup_ui()
        self.populate_tree()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels([_("Action"), _("Shortcut")])
        self.tree.setAlternatingRowColors(True)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.keyPressEvent = self.tree_key_press_event
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.tree.header().setSectionsMovable(False)
        self.tree.header().setSectionsClickable(False)
        layout.addWidget(self.tree)

        button_layout = QHBoxLayout()
        self.reset_button = QPushButton(_("Reset to Default"))
        self.reset_button.clicked.connect(self.reset_to_default)
        self.apply_button = QPushButton(_("Apply"))
        self.apply_button.clicked.connect(self.apply_changes)
        self.cancel_button = QPushButton(_("Cancel"))
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button = QPushButton(_("OK"))
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)

    def tree_key_press_event(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            current_item = self.tree.currentItem()
            if current_item and current_item.parent() is not None:
                self.start_editing(current_item, 1)
                return
        QTreeWidget.keyPressEvent(self.tree, event)

    def _set_action_item_text(self, item, action, category, shortcut):
        # Column 0's accessible Name is the action text (e.g. "Play/Pause")
        # -- its description can safely restate the shortcut since it isn't
        # already saying it. Column 1's accessible Name IS the shortcut
        # text itself, so its description must NOT restate the shortcut too
        # -- doing so is exactly what produced the reported artifact
        # ("Q, Return  Play/Pause in Explorer, current shortcut: Q, Return
        # level 1": Name + Description both carrying the shortcut).
        shortcut_display = shortcut if shortcut else _("none")
        item.setText(1, shortcut)
        item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole,
                     _("{action} in {category}, current shortcut: {shortcut}").format(
                         action=action, category=category, shortcut=shortcut_display))
        item.setData(1, Qt.ItemDataRole.AccessibleDescriptionRole,
                     _("Shortcut for {action} in {category}").format(action=action, category=category))

    def populate_tree(self):
        self.tree.clear()
        for category_name in key_config.key_dict.keys():
            category_item = QTreeWidgetItem(self.tree, [category_name, ""])
            category_item.setFlags(category_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            category_item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, f"Category: {category_name}")
            if category_name in key_config.key_config:
                for action, shortcut in key_config.key_config[category_name].items():
                    action_item = QTreeWidgetItem(category_item, [action, shortcut])
                    action_item.setData(0, Qt.ItemDataRole.UserRole, category_name)
                    self._set_action_item_text(action_item, action, category_name, shortcut)
                    action_item.setFlags(action_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tree.addTopLevelItem(category_item)
            category_item.setExpanded(False)
        self.tree.header().setSectionsMovable(False)
        self.tree.header().setSectionsClickable(False)

    @Slot(object, int)
    def on_item_clicked(self, item, column):
        if item.parent() is not None and column == 1:
            self.start_editing(item, column)

    @Slot(object, int)
    def on_item_double_clicked(self, item, column):
        if item.parent() is not None and column == 1:
            self.start_editing(item, column)

    def start_editing(self, item, column):
        if column != 1 or item.parent() is None:
            return

        if self.current_editor is not None:
            self.finish_editing()

        existing_text = item.text(1)
        editor = HotkeyCaptureEdit(existing_text)
        editor_tooltip = _("Shortcut editor. Press the desired key combination; releasing it accepts the shortcut. Press Escape to cancel.")
        editor.setAccessibleDescription(editor_tooltip)
        editor.setToolTip(editor_tooltip)
        editor.sequenceCaptured.connect(self.finish_editing)
        editor.cancelled.connect(self.cancel_editing)

        self.current_editor = editor
        self.current_editor_item = item
        self.tree.setItemWidget(item, 1, editor)
        editor.setFocus()

    def finish_editing(self, new_seq=None):
        if self.current_editor is None or self.current_editor_item is None:
            return

        if new_seq is None:
            new_seq = self.current_editor.text()
        item = self.current_editor_item
        parent = item.parent()

        if new_seq and parent is not None:
            category = parent.text(0)
            action_text = item.text(0)
            key_config.key_config[category][action_text] = new_seq
            self._set_action_item_text(item, action_text, category, new_seq)

        self._teardown_editor(item)

    def cancel_editing(self):
        if self.current_editor is None or self.current_editor_item is None:
            return
        self._teardown_editor(self.current_editor_item)

    def _teardown_editor(self, item):
        try:
            self.tree.setItemWidget(item, 1, None)
        except Exception:
            pass

        if self.current_editor is not None:
            self.current_editor.deleteLater()
        self.current_editor = None
        self.current_editor_item = None

    @Slot()
    def reset_to_default(self):
        reply = QMessageBox.question(
            self,
            _("Reset to Default"),
            _("Are you sure you want to reset all hotkeys to default?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            key_config.keysToDefault()
            self.populate_tree()

    @Slot()
    def apply_changes(self):
        key_config.saveConfig()
        key_config.apply_global_hotkeys()
        if self.reset_callback:
            self.reset_callback()

    def accept(self):
        if self.current_editor:
            self.finish_editing()
        self.apply_changes()
        super().accept()

    def reject(self):
        if self.current_editor:
            self.cancel_editing()
        super().reject()

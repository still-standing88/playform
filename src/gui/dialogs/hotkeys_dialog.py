from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QTreeWidget,
    QTreeWidgetItem, QPushButton, QLineEdit, QMessageBox, QHeaderView, QMenu
)
from PySide6.QtCore import Qt, QTimer, Slot, Signal
from PySide6.QtGui import QKeySequence

from app_config import key_config
from app_constance.key_names import key_name


_WIN_MODIFIER_TOKENS = {"win", "windows", "super", "cmd"}


def canonical_shortcut_text(modifiers, key=None):
    """Spell a chord the way ShortcutManager reports a live press: Ctrl, Alt,
    Shift, Win in that order, then the key's own name. QKeySequence
    .toString() cannot be used for this -- it renders a Win chord as an
    empty string, and spells Escape/Delete/Page Up as Esc/Del/PgUp, none of
    which a stored hotkey would ever match."""
    parts = []
    flags = int(getattr(modifiers, "value", modifiers) or 0)
    for flag, name in (
        (Qt.KeyboardModifier.ControlModifier.value, "Ctrl"),
        (Qt.KeyboardModifier.AltModifier.value, "Alt"),
        (Qt.KeyboardModifier.ShiftModifier.value, "Shift"),
        (Qt.KeyboardModifier.MetaModifier.value, "Win"),
    ):
        if flags & flag:
            parts.append(name)

    if key is not None:
        name = key_name(key)
        if not name:
            return ""
        parts.append(name)

    return "+".join(parts)


def normalize_shortcut_text(text):
    """Canonical text for a typed shortcut, "" for an empty field (which
    unbinds the key), or None when Qt cannot read it as a single chord."""
    text = text.strip()
    if not text:
        return ""

    parts = []
    for part in text.split("+"):
        # Qt knows the Windows modifier only as "Meta"; everywhere else --
        # default keys, the keyboard library, ShortcutManager -- it is "Win".
        token = part.strip().casefold()
        parts.append("Meta" if token in _WIN_MODIFIER_TOKENS else part)

    sequence = QKeySequence.fromString("+".join(parts), QKeySequence.SequenceFormat.NativeText)
    if sequence.count() != 1:
        return None

    combination = sequence[0]
    key = combination.key()
    if int(key) == int(Qt.Key.Key_unknown):
        return None

    return canonical_shortcut_text(combination.keyboardModifiers(), key)


class ShortcutEdit(QLineEdit):
    """The editing panel's shortcut field. Normally editable, so a
    combination can just be typed; Capture key arms it to read the chord off
    the keyboard instead, accepting on key-release. Holding modifiers
    commits nothing by itself, and releasing the first real key commits the
    combo captured up to that point, so there is no separate confirm
    keystroke to be ambiguous about (which is what made QKeySequenceEdit
    record "Q then Return" as a two-key chord). Escape cancels a capture."""

    captured = Signal(str)
    captureCancelled = Signal()

    _MODIFIER_KEYS = {
        Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt,
        Qt.Key.Key_Meta, Qt.Key.Key_AltGr,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._armed = False
        self._captured_key = None
        self._captured_modifiers = Qt.KeyboardModifier.NoModifier
        self._context_action = ""
        self._context_category = ""

    def set_shortcut_context(self, action, category):
        self._context_action = action
        self._context_category = category
        self._refresh_accessible_text(self.text())

    def is_capture_armed(self):
        return self._armed

    def set_capture_armed(self, armed):
        armed = bool(armed)
        if armed == self._armed:
            return
        self._armed = armed
        self._captured_key = None
        self.setReadOnly(armed)
        self._refresh_accessible_text(self.text())

    def _refresh_accessible_text(self, sequence):
        shortcut_display = sequence if sequence else _("none")
        self.setAccessibleName(_("{action} in {category}").format(
            action=self._context_action, category=self._context_category))
        if self._armed:
            self.setAccessibleDescription(_(
                "Recording for {action}. Press the desired key combination; "
                "releasing it accepts. Escape cancels.").format(action=self._context_action))
        else:
            self.setAccessibleDescription(_(
                "current shortcut: {shortcut}. Type a combination such as Ctrl+Shift+P, "
                "or use Capture key to record one.").format(shortcut=shortcut_display))

    def keyPressEvent(self, event):
        if not self._armed:
            super().keyPressEvent(event)
            return

        # Accepted in both branches: an unhandled Return or Space would
        # otherwise reach the dialog and activate a button.
        event.accept()
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.captureCancelled.emit()
            return
        if key in self._MODIFIER_KEYS or key == Qt.Key.Key_unknown:
            text = canonical_shortcut_text(event.modifiers())
            self.setText(text)
            self._refresh_accessible_text(text)
            return
        self._captured_key = key
        self._captured_modifiers = event.modifiers()
        text = canonical_shortcut_text(event.modifiers(), key)
        self.setText(text)
        self._refresh_accessible_text(text)

    def keyReleaseEvent(self, event):
        if not self._armed:
            super().keyReleaseEvent(event)
            return
        if event.key() in self._MODIFIER_KEYS or self._captured_key is None:
            return
        text = canonical_shortcut_text(self._captured_modifiers, self._captured_key)
        self._captured_key = None
        self.setText(text)
        self.captured.emit(text)


class HotkeysTree(QTreeWidget):
    """QTreeWidget subclass so Enter-on-a-row opens the editor reliably --
    assigning tree.keyPressEvent on the instance never overrides Qt's C++
    virtual dispatch, so the old monkey-patch was dead code."""

    enter_pressed = Signal(object, int)
    toggle_requested = Signal(object)

    def keyPressEvent(self, event):
        current_item = self.currentItem()
        is_action_row = current_item is not None and current_item.parent() is not None
        # Qt only toggles the check state of the current cell's own column,
        # so Space on the Shortcut cell would do nothing without this.
        if event.key() == Qt.Key.Key_Space and is_action_row:
            self.toggle_requested.emit(current_item)
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and is_action_row:
            self.enter_pressed.emit(current_item, 1)
            return
        super().keyPressEvent(event)


class HotkeysDialog(QDialog):
    def __init__(self, parent=None, reset_callback=None):
        super().__init__(parent)
        self.reset_callback = reset_callback
        self._edit_item = None
        self._edit_category = ""
        self._edit_action = ""
        self._dirty = False
        self._closing = False
        self._committed_config = self._snapshot_config()
        self.setWindowTitle(_("Hotkeys Configuration"))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(700, 500)
        self.setMinimumSize(600, 400)
        self.setup_ui()
        self.populate_tree()
        key_config.suspend_global_hotkeys()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(_("Search hotkeys"))
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self.filter_hotkeys)
        layout.addWidget(self.search_edit)

        self.tree = HotkeysTree()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels([_("Action"), _("Shortcut")])
        self.tree.setAlternatingRowColors(True)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.itemChanged.connect(self.on_item_changed)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.currentItemChanged.connect(self.on_current_item_changed)
        self.tree.enter_pressed.connect(self.focus_editor)
        self.tree.toggle_requested.connect(self.toggle_item_enabled)
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        self.tree.header().setSectionsMovable(False)
        self.tree.header().setSectionsClickable(False)
        layout.addWidget(self.tree)

        # A real widget panel rather than a widget dropped into the Shortcut
        # cell: setItemWidget children are not in the tree's accessibility
        # tree at all, and this field and button have to be reachable with a
        # screen reader.
        self.edit_panel = QWidget()
        panel_layout = QVBoxLayout(self.edit_panel)
        panel_layout.setContentsMargins(0, 6, 0, 0)
        panel_layout.setSpacing(4)
        self.edit_label = QLabel()
        panel_layout.addWidget(self.edit_label)

        field_row = QHBoxLayout()
        self.edit_field = ShortcutEdit()
        self.edit_label.setBuddy(self.edit_field)
        self.edit_field.textEdited.connect(self.on_field_edited)
        self.edit_field.editingFinished.connect(self.commit_pending)
        self.edit_field.captured.connect(self.on_shortcut_captured)
        self.edit_field.captureCancelled.connect(self.on_capture_cancelled)
        field_row.addWidget(self.edit_field, 1)

        self.capture_button = QPushButton(_("Capture key"))
        self.capture_button.setCheckable(True)
        self.capture_button.setAccessibleDescription(_(
            "Record the next key combination you press instead of typing it."))
        self.capture_button.toggled.connect(self.on_capture_toggled)
        field_row.addWidget(self.capture_button)
        panel_layout.addLayout(field_row)

        self.edit_panel.setVisible(False)
        layout.addWidget(self.edit_panel)

        button_layout = QHBoxLayout()
        self.reset_button = QPushButton(_("Reset to Default"))
        self.reset_button.clicked.connect(self.reset_to_default)
        self.apply_button = QPushButton(_("Apply"))
        self.apply_button.clicked.connect(self.apply_changes)
        self.cancel_button = QPushButton(_("Cancel"))
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button = QPushButton(_("OK"))
        self.ok_button.clicked.connect(self.accept)
        for button in (self.reset_button, self.apply_button, self.cancel_button, self.ok_button):
            # Otherwise Return inside the shortcut field clicks whichever
            # button Qt made the default, closing the dialog mid-edit.
            button.setAutoDefault(False)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

    def _set_action_item_text(self, item, action, category, shortcut):
        # Both columns announce with the same Name and "{action} in
        # {category}, current shortcut: {seq}" description so every row
        # reads identically whichever cell has focus ("Play/Pause ...").
        # AccessibleTextRole overrides the announced Name: without it,
        # column 1's Name is its display text -- the bare shortcut -- and
        # after an edit rows led with "A" instead of the action name.
        shortcut_display = shortcut if shortcut else _("none")
        description = _("{action} in {category}, current shortcut: {shortcut}").format(
            action=action, category=category, shortcut=shortcut_display)
        item.setText(1, shortcut)
        item.setData(0, Qt.ItemDataRole.AccessibleTextRole, action)
        item.setData(1, Qt.ItemDataRole.AccessibleTextRole, action)
        item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, description)
        item.setData(1, Qt.ItemDataRole.AccessibleDescriptionRole, description)

    def _set_action_item_enabled(self, item, category, action):
        is_enabled = key_config.is_hotkey_enabled(category, action)
        # Must run even when the value already matches: a QTreeWidgetItem
        # reads Unchecked without a CheckStateRole set, and an item with no
        # role gets no checkbox drawn (nor exposed to screen readers).
        was_blocked = self.tree.blockSignals(True)
        item.setCheckState(
            0,
            Qt.CheckState.Checked if is_enabled else Qt.CheckState.Unchecked,
        )
        self.tree.blockSignals(was_blocked)

    def populate_tree(self):
        self.reset_panel()
        self.tree.blockSignals(True)
        self.tree.clear()
        for category_name in key_config.key_dict.keys():
            category_item = QTreeWidgetItem(self.tree, [category_name, ""])
            # Selectable so screen-reader/keyboard users can actually reach
            # and read category rows -- stripping ItemIsSelectable made
            # arrow-key navigation skip them entirely (unreadable).
            category_item.setFlags(category_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            category_item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole,
                                  _("Category: {category}").format(category=category_name))
            if category_name in key_config.key_config:
                for action, shortcut in key_config.key_config[category_name].items():
                    action_item = QTreeWidgetItem(category_item, [action, shortcut])
                    action_item.setData(0, Qt.ItemDataRole.UserRole, category_name)
                    self._set_action_item_text(action_item, action, category_name, shortcut)
                    action_item.setFlags(
                        (action_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        | Qt.ItemFlag.ItemIsUserCheckable
                    )
                    self._set_action_item_enabled(action_item, category_name, action)
            self.tree.addTopLevelItem(category_item)
            category_item.setExpanded(False)
        self.tree.header().setSectionsMovable(False)
        self.tree.header().setSectionsClickable(False)
        self.tree.blockSignals(False)
        self.filter_hotkeys(self.search_edit.text())

    @Slot(object, int)
    def on_item_changed(self, item, column):
        if column != 0 or item.parent() is None:
            return
        key_config.set_hotkey_enabled(
            item.parent().text(0),
            item.text(0),
            item.checkState(0) == Qt.CheckState.Checked,
        )

    @Slot(object, int)
    def on_item_clicked(self, item, column):
        if item.parent() is not None and column == 1:
            self.focus_editor(item, column)

    @Slot(object, int)
    def on_item_double_clicked(self, item, column):
        if item.parent() is not None and column == 1:
            self.focus_editor(item, column)

    @Slot(object)
    def toggle_item_enabled(self, item):
        item.setCheckState(
            0,
            Qt.CheckState.Unchecked
            if item.checkState(0) == Qt.CheckState.Checked
            else Qt.CheckState.Checked,
        )

    @Slot(object, object)
    def on_current_item_changed(self, current, previous):
        self.commit_pending()
        if current is not None and current.parent() is not None:
            self.load_panel(current)
        else:
            self.reset_panel()

    @Slot(object, int)
    def focus_editor(self, item, column=1):
        if item is None or item.parent() is None:
            return
        self.commit_pending()
        if self.tree.currentItem() is not item:
            self.tree.setCurrentItem(item)
        if self._edit_item is not item:
            self.load_panel(item)
        self.edit_field.setFocus()

    def load_panel(self, item):
        self.disarm_capture(restore_text=False)
        self._edit_item = item
        self._edit_category = item.parent().text(0)
        self._edit_action = item.text(0)
        self._dirty = False
        self.edit_field.setText(item.text(1))
        self.edit_field.set_shortcut_context(self._edit_action, self._edit_category)
        self.edit_label.setText(_("Editing: {action} in {category}").format(
            action=self._edit_action, category=self._edit_category))
        self.edit_panel.setVisible(True)

    def reset_panel(self):
        self.disarm_capture(restore_text=False)
        self._edit_item = None
        self._edit_category = ""
        self._edit_action = ""
        self._dirty = False
        self.edit_field.clear()
        self.edit_panel.setVisible(False)

    @Slot(str)
    def on_field_edited(self, text):
        self._dirty = True

    @Slot()
    def commit_pending(self):
        item = self._edit_item
        if item is None or not self._dirty or self._closing:
            return
        if self.edit_field.is_capture_armed():
            return

        text = self.edit_field.text()
        action = self._edit_action
        self._dirty = False
        normalized = normalize_shortcut_text(text)
        if normalized is None:
            self.edit_field.setText(item.text(1))
            self.edit_field.set_shortcut_context(action, self._edit_category)
            # Deferred: running a modal warning straight out of the field's
            # focus-out would nest an event loop inside that event.
            QTimer.singleShot(0, lambda: self.warn_invalid(text, action))
            return

        self.edit_field.setText(normalized)
        self.apply_edit(item, normalized)

    def warn_invalid(self, text, action):
        if self._closing:
            return
        QMessageBox.warning(
            self,
            _("Invalid shortcut"),
            _("{text} is not a valid key combination for {action}. Enter something like "
              "Ctrl+Shift+P, or use Capture key.").format(text=text, action=action),
        )

    def apply_edit(self, item, sequence):
        category = item.parent().text(0)
        action = item.text(0)
        key_config.set_hotkey_sequence(category, action, sequence)
        self._set_action_item_text(item, action, category, sequence)
        self.edit_field.set_shortcut_context(action, category)

    @Slot(bool)
    def on_capture_toggled(self, armed):
        if armed:
            self.edit_field.set_capture_armed(True)
            self.edit_field.setFocus()
        else:
            self.disarm_capture(restore_text=True)

    @Slot(str)
    def on_shortcut_captured(self, sequence):
        item = self._edit_item
        self.disarm_capture(restore_text=False)
        if item is None:
            return
        self.edit_field.setText(sequence)
        self._dirty = False
        self.apply_edit(item, sequence)

    @Slot()
    def on_capture_cancelled(self):
        self.disarm_capture(restore_text=True)

    def disarm_capture(self, restore_text=True):
        self.edit_field.set_capture_armed(False)
        was_blocked = self.capture_button.blockSignals(True)
        self.capture_button.setChecked(False)
        self.capture_button.blockSignals(was_blocked)
        if restore_text:
            self.edit_field.setText(self._edit_item.text(1) if self._edit_item is not None else "")
            self.edit_field.set_shortcut_context(self._edit_action, self._edit_category)

    @Slot(object)
    def filter_hotkeys(self, query):
        query = query.strip().casefold()
        for category_index in range(self.tree.topLevelItemCount()):
            category_item = self.tree.topLevelItem(category_index)
            has_match = False
            for action_index in range(category_item.childCount()):
                action_item = category_item.child(action_index)
                matches = not query or query in action_item.text(0).casefold()
                action_item.setHidden(not matches)
                has_match = has_match or matches
            category_item.setHidden(not has_match)
            category_item.setExpanded(bool(query) and has_match)
        if self._edit_item is not None and self._edit_item.isHidden():
            self.commit_pending()
            self.reset_panel()

    @Slot(object)
    def open_context_menu(self, position):
        item = self.tree.itemAt(position)
        if item is None or item.parent() is None:
            return
        self.tree.setCurrentItem(item)
        category = item.parent().text(0)
        action = item.text(0)
        is_enabled = key_config.is_hotkey_enabled(category, action)

        menu = QMenu(self)
        toggle_action = menu.addAction(_("Disable") if is_enabled else _("Enable"))
        unbind_action = menu.addAction(_("Unbind shortcut"))
        reset_action = menu.addAction(_("Reset hotkey"))
        selected_action = menu.exec(self.tree.viewport().mapToGlobal(position))

        if selected_action == toggle_action:
            key_config.set_hotkey_enabled(category, action, not is_enabled)
            self._set_action_item_enabled(item, category, action)
        elif selected_action == unbind_action:
            key_config.set_hotkey_sequence(category, action, "")
            self._set_action_item_text(item, action, category, "")
        elif selected_action == reset_action:
            key_config.reset_hotkey(category, action)
            self._set_action_item_text(
                item,
                action,
                category,
                key_config.get_hotkey_sequence(category, action),
            )
            self._set_action_item_enabled(item, category, action)

        if self._edit_item is item:
            self.load_panel(item)

    @staticmethod
    def _snapshot_config():
        return {section: dict(key_config.key_config.items(section))
                for section in key_config.key_config.sections()}

    def _restore_committed_config(self):
        cfg = key_config.key_config
        for section in cfg.sections():
            cfg.remove_section(section)
        for section, options in self._committed_config.items():
            cfg[section] = dict(options)

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
        self._committed_config = self._snapshot_config()
        if self.reset_callback:
            self.reset_callback()

    def accept(self):
        self.commit_pending()
        self.apply_changes()
        super().accept()

    def done(self, result):
        # Covers accept, reject and the window's own close button. Apply runs
        # while the hooks are still suspended, so the new Global sequences
        # only take effect here.
        key_config.resume_global_hotkeys()
        super().done(result)

    def reject(self):
        # Set before the dialog tears down so a pending invalid-input warning
        # does not pop over the window the user just decided to leave.
        self._closing = True
        self._restore_committed_config()
        super().reject()

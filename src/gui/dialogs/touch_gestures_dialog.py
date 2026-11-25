from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from app_config.touch_config import touch_config
from app_constance.touch_gestures import ACTION_LABELS, GESTURES, SETTING_RANGES, default_settings
from gui_controls.touch_gesture_controller import TouchGestureController


class PracticeSurface(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(240, 180)
        self.setAccessibleName(_("Touch gesture practice area"))
        self.setAccessibleDescription(_("Use touchscreen gestures here. Playback is not changed."))

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(QPen(self.palette().color(QPalette.ColorRole.Mid)))
        for x in (self.width() // 3, self.width() * 2 // 3):
            painter.drawLine(x, 12, x, self.height() - 12)
        painter.setPen(self.palette().color(QPalette.ColorRole.Text))
        for i, text in enumerate((_("Left"), _("Centre"), _("Right"))):
            painter.drawText(i * self.width() // 3, 0, self.width() // 3, self.height(), Qt.AlignmentFlag.AlignCenter, text)


class TouchGesturesDialog(QDialog):
    applied = Signal()

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.config = config or touch_config
        self._draft = self.config.snapshot()
        self._loading = False
        self.setWindowTitle(_("Touch Gestures Configuration"))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(720, 580)
        self.setMinimumSize(480, 420)
        self._setup_ui()
        self._load_draft()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        self.enabled_check = QCheckBox(_("Enable touchscreen gestures on the video area"))
        self.enabled_check.setMinimumHeight(32)
        self.enabled_check.toggled.connect(lambda value: self._set_option("enabled", value))
        layout.addWidget(self.enabled_check)

        preset_row = QHBoxLayout()
        preset_label = QLabel(_("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumHeight(32)
        for text, key in ((_("Custom"), "custom"), (_("Video (default)"), "video"), (_("Audiobooks / Podcasts"), "audio")):
            self.preset_combo.addItem(text, key)
        preset_label.setBuddy(self.preset_combo)
        self.preset_combo.activated.connect(self._select_preset)
        preset_row.addWidget(preset_label)
        preset_row.addWidget(self.preset_combo, 1)
        layout.addLayout(preset_row)

        tabs = QTabWidget()
        layout.addWidget(tabs, 1)
        mappings = QWidget()
        mappings_layout = QVBoxLayout(mappings)
        self.search_edit = QLineEdit()
        self.search_edit.setMinimumHeight(32)
        self.search_edit.setPlaceholderText(_("Search gestures or actions"))
        self.search_edit.setAccessibleName(_("Search gestures or actions"))
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter)
        mappings_layout.addWidget(self.search_edit)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([_("Gesture"), _("Action")])
        self.tree.setAccessibleName(_("Touch gesture mappings"))
        self.tree.setAlternatingRowColors(True)
        self.tree.setStyleSheet("QTreeView::item { padding-top: 4px; padding-bottom: 4px; }")
        self.tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tree.currentItemChanged.connect(self._select_gesture)
        self.tree.itemActivated.connect(lambda item, column: self.action_combo.setFocus())
        mappings_layout.addWidget(self.tree, 1)
        self.rows = {}
        categories = {}
        for key, (category, label, actions) in GESTURES.items():
            if category not in categories:
                categories[category] = QTreeWidgetItem(self.tree, [_(category)])
                categories[category].setExpanded(True)
            row = QTreeWidgetItem(categories[category], [_(label), ""])
            row.setData(0, Qt.ItemDataRole.UserRole, key)
            self.rows[key] = row
        self.edit_label = QLabel(_("Action for selected gesture:"))
        self.action_combo = QComboBox()
        self.action_combo.setMinimumHeight(32)
        self.action_combo.setAccessibleName(_("Action for selected gesture"))
        self.edit_label.setBuddy(self.action_combo)
        self.action_combo.currentIndexChanged.connect(self._change_binding)
        mappings_layout.addWidget(self.edit_label)
        mappings_layout.addWidget(self.action_combo)
        tabs.addTab(mappings, _("Mappings"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        behavior = QWidget()
        form = QFormLayout(behavior)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.fullscreen_check = QCheckBox(_("Only in fullscreen"))
        self.fullscreen_check.toggled.connect(lambda value: self._set_option("fullscreen_only", value))
        self.feedback_check = QCheckBox(_("Show gesture feedback on video"))
        self.feedback_check.toggled.connect(lambda value: self._set_option("feedback", value))
        form.addRow(self.fullscreen_check)
        form.addRow(self.feedback_check)
        self.option_fields = {}
        for key, text, suffix in (
            ("seek_backward_seconds", "Backward skip", " s"),
            ("seek_forward_seconds", "Forward skip", " s"),
            ("scrub_seconds", "Seek distance across full width", " s"),
            ("sensitivity", "Swipe and zoom sensitivity", "x"),
            ("volume_limit", "Maximum gesture volume", "%"),
            ("hold_ms", "Long press duration", " ms"),
            ("double_tap_ms", "Double tap interval", " ms"),
            ("drag_threshold", "Movement before a swipe", " px"),
            ("hold_speed", "Temporary playback speed", "x"),
        ):
            field = QDoubleSpinBox() if key in ("sensitivity", "hold_speed") else QSpinBox()
            field.setRange(*SETTING_RANGES[key])
            field.setMinimumHeight(32)
            if isinstance(field, QDoubleSpinBox):
                field.setDecimals(2)
                field.setSingleStep(0.25)
            field.setSuffix(suffix)
            field.setAccessibleName(_(text))
            field.valueChanged.connect(lambda value, name=key: self._set_option(name, value))
            label = QLabel(_(text))
            label.setBuddy(field)
            form.addRow(label, field)
            self.option_fields[key] = field
        help_label = QLabel(_("During horizontal seeking, move your finger vertically to seek more precisely. Brightness changes the video, not the display hardware."))
        help_label.setWordWrap(True)
        form.addRow(help_label)
        scroll.setWidget(behavior)
        tabs.addTab(scroll, _("Behavior"))

        practice = QWidget()
        practice_layout = QVBoxLayout(practice)
        explanation = QLabel(_("Try your gestures in this area using a touchscreen. Your draft settings are used, and playback is not changed."))
        explanation.setWordWrap(True)
        practice_layout.addWidget(explanation)
        self.practice_surface = PracticeSurface()
        practice_layout.addWidget(self.practice_surface, 1)
        self.practice_result = QLabel(_("Waiting for a gesture..."))
        self.practice_result.setWordWrap(True)
        self.practice_result.setAccessibleName(_("Recognized gesture"))
        practice_layout.addWidget(self.practice_result)
        self.practice_controller = TouchGestureController(self.practice_surface, self._draft)
        self.practice_controller.triggered.connect(lambda key, point: self._practice_result(key))
        self.practice_controller.started.connect(self._practice_result)
        self.practice_controller.finished.connect(lambda key, cancelled: self.practice_result.setText(_("Gesture cancelled")) if cancelled else None)
        tabs.addTab(practice, _("Practice"))

        buttons = QHBoxLayout()
        reset = QPushButton(_("Reset to Default"))
        reset.clicked.connect(self.reset_defaults)
        self.apply_button = QPushButton(_("Apply"))
        self.apply_button.clicked.connect(self.apply_changes)
        ok = QPushButton(_("OK"))
        ok.clicked.connect(self.accept)
        cancel = QPushButton(_("Cancel"))
        cancel.clicked.connect(self.reject)
        for button in (reset, self.apply_button, ok, cancel):
            button.setAutoDefault(False)
            button.setMinimumHeight(36)
        buttons.addWidget(reset)
        buttons.addStretch()
        buttons.addWidget(self.apply_button)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def _load_draft(self):
        self._loading = True
        self.enabled_check.setChecked(self._draft["enabled"])
        self.fullscreen_check.setChecked(self._draft["fullscreen_only"])
        self.feedback_check.setChecked(self._draft["feedback"])
        for key, field in self.option_fields.items():
            field.setValue(self._draft[key])
        for key in self.rows:
            self._refresh_row(key)
        self._loading = False
        if self.tree.currentItem() is None:
            self.tree.setCurrentItem(self.rows["tap"])
        else:
            self._select_gesture(self.tree.currentItem(), None)
        self.practice_controller.set_settings(self._draft)
        self._filter(self.search_edit.text())

    def _refresh_row(self, key):
        row = self.rows[key]
        label = _(GESTURES[key][1])
        action = _(ACTION_LABELS[self._draft["bindings"][key]])
        row.setText(1, action)
        for column in (0, 1):
            row.setData(column, Qt.ItemDataRole.AccessibleTextRole, label)
            row.setData(column, Qt.ItemDataRole.AccessibleDescriptionRole,
                        _("{gesture}, action: {action}").format(gesture=label, action=action))

    def _select_gesture(self, current, previous):
        self.action_combo.blockSignals(True)
        self.action_combo.clear()
        key = current.data(0, Qt.ItemDataRole.UserRole) if current else None
        self.action_combo.setEnabled(key in GESTURES)
        if key in GESTURES:
            self.edit_label.setText(_("Action for {gesture}:").format(gesture=_(GESTURES[key][1])))
            for action in GESTURES[key][2]:
                self.action_combo.addItem(_(ACTION_LABELS[action]), action)
            self.action_combo.setCurrentIndex(self.action_combo.findData(self._draft["bindings"][key]))
        self.action_combo.blockSignals(False)

    def _change_binding(self, index):
        current = self.tree.currentItem()
        key = current.data(0, Qt.ItemDataRole.UserRole) if current else None
        if self._loading or key not in GESTURES or index < 0:
            return
        self._draft["bindings"][key] = self.action_combo.currentData()
        self.preset_combo.setCurrentIndex(0)
        self._refresh_row(key)
        self.practice_controller.set_settings(self._draft)
        self._filter(self.search_edit.text())

    def _set_option(self, key, value):
        if self._loading:
            return
        self._draft[key] = value
        self.preset_combo.setCurrentIndex(0)
        self.practice_controller.set_settings(self._draft)

    def _select_preset(self, index):
        preset = self.preset_combo.itemData(index)
        if preset != "custom":
            self._draft = default_settings(preset)
            self._load_draft()

    def reset_defaults(self):
        self._draft = default_settings()
        self.preset_combo.setCurrentIndex(self.preset_combo.findData("video"))
        self._load_draft()

    def _filter(self, text):
        text = text.casefold().strip()
        for row in self.rows.values():
            row.setHidden(bool(text) and text not in (row.text(0) + " " + row.text(1)).casefold())
        for index in range(self.tree.topLevelItemCount()):
            category = self.tree.topLevelItem(index)
            category.setHidden(all(category.child(i).isHidden() for i in range(category.childCount())))

    def _practice_result(self, key):
        self.practice_result.setText(_("{gesture}: {action}").format(
            gesture=_(GESTURES[key][1]), action=_(ACTION_LABELS[self._draft["bindings"][key]])))

    def apply_changes(self):
        if not self.config.save(self._draft):
            QMessageBox.warning(self, _("Could not save gestures"), _("Touch gesture settings could not be saved. Your changes are still available in this dialog."))
            return False
        self.applied.emit()
        return True

    def accept(self):
        if self.apply_changes():
            super().accept()

    def done(self, result):
        self.practice_controller.cancel()
        super().done(result)

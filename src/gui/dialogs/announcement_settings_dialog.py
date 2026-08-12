from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel
)
from PySide6.QtCore import Qt

from utilities.announcement_categories import AnnouncementCategory, category_label
from utilities.announcement_settings import get_enabled_map, set_enabled_map


class AnnouncementSettingsDialog(QDialog):
    """Preferences -> Accessibility -> Announcements: one checkable row per
    AnnouncementCategory (the granularity every signal_manager.announce()
    call site is actually tagged at -- see utilities/announcement_categories.py).
    Unchecking a category stops it from being spoken (see
    main_window._on_categorized_message); the status bar still always shows
    the text regardless."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Announcements"))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(420, 420)
        self._enabled_map = get_enabled_map()
        self.setup_ui()
        self.populate_tree()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(_(
            "Choose which kinds of events are announced by speech. The "
            "status bar always shows the text either way -- this only "
            "controls what gets spoken aloud."
        ))
        info.setWordWrap(True)
        layout.addWidget(info)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(1)
        self.tree.setHeaderLabels([_("Category")])
        self.tree.header().setSectionResizeMode(0, self.tree.header().ResizeMode.Stretch)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree)

        button_layout = QHBoxLayout()
        self.select_all_btn = QPushButton(_("Enable All"))
        self.select_all_btn.clicked.connect(lambda: self._set_all(True))
        self.select_none_btn = QPushButton(_("Disable All"))
        self.select_none_btn.clicked.connect(lambda: self._set_all(False))
        button_layout.addWidget(self.select_all_btn)
        button_layout.addWidget(self.select_none_btn)
        button_layout.addStretch()

        self.close_btn = QPushButton(_("Close"))
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)

    def populate_tree(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        for category in AnnouncementCategory:
            enabled = self._enabled_map.get(category.value, True)
            item = QTreeWidgetItem(self.tree, [category_label(category)])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
            item.setData(0, Qt.ItemDataRole.UserRole, category.value)
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole,
                         _("Announce {category} events by speech").format(category=category_label(category)))
            self.tree.addTopLevelItem(item)
        self.tree.blockSignals(False)

    def _on_item_changed(self, item, column):
        category_value = item.data(0, Qt.ItemDataRole.UserRole)
        if not category_value:
            return
        self._enabled_map[category_value] = item.checkState(0) == Qt.CheckState.Checked
        set_enabled_map(self._enabled_map)

    def _set_all(self, enabled: bool):
        for category in AnnouncementCategory:
            self._enabled_map[category.value] = enabled
        set_enabled_map(self._enabled_map)
        self.populate_tree()

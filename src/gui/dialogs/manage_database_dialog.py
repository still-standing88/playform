from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QGroupBox, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QKeyEvent

from app_constance.styles import TITLE_LABEL_STYLE
import app_db


class ManageDatabaseDialog(QDialog):
    """Lists cataloged folders (with file counts / last-scanned times
    already tracked by app_db.media_db but never surfaced anywhere before
    this), and exposes per-folder rescan/remove plus the whole-database
    Clear & Rebuild that used to live in the Database prefs tab - a
    destructive, folder-scoped action doesn't belong behind a checkbox page.
    """

    dialog_hidden = Signal()
    dialog_closed = Signal()

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._main_window = main_window

        self.setWindowTitle(_("Manage Database"))
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(560, 420)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        self.ui()
        self.reload()

    def ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title_bar = QHBoxLayout()
        title_label = QLabel(_("Manage Database"))
        title_label.setStyleSheet(TITLE_LABEL_STYLE)
        title_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        title_bar.addWidget(title_label)
        title_bar.addStretch()

        minimize_btn = QPushButton(_("Minimize"))
        minimize_btn.setFixedSize(75, 25)
        minimize_btn.setToolTip(_("Hide to status bar"))
        minimize_btn.clicked.connect(self._on_minimize)
        title_bar.addWidget(minimize_btn)

        close_btn = QPushButton(_("Close"))
        close_btn.setFixedSize(60, 25)
        close_btn.clicked.connect(self._on_close_requested)
        title_bar.addWidget(close_btn)

        layout.addLayout(title_bar)

        self.folders_tree = QTreeWidget()
        self.folders_tree.setColumnCount(3)
        self.folders_tree.setHeaderLabels([_("Folder"), _("Files"), _("Last Scanned")])
        self.folders_tree.setRootIsDecorated(False)
        self.folders_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.folders_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.folders_tree.header().setSectionsMovable(False)
        self.folders_tree.header().setSectionsClickable(False)
        self.folders_tree.setAccessibleName(_("Cataloged folders list"))
        self.folders_tree.setAccessibleDescription(
            _("List of folders added to the media database, with file count and last scan time.")
        )
        self.folders_tree.itemSelectionChanged.connect(self._update_button_states)
        layout.addWidget(self.folders_tree)

        folder_buttons = QHBoxLayout()
        self.add_button = QPushButton(_("Add Folder..."))
        self.add_button.clicked.connect(self._on_add_clicked)
        folder_buttons.addWidget(self.add_button)

        self.rescan_button = QPushButton(_("Rescan Selected"))
        self.rescan_button.clicked.connect(self._on_rescan_clicked)
        folder_buttons.addWidget(self.rescan_button)

        self.remove_button = QPushButton(_("Remove Selected..."))
        self.remove_button.clicked.connect(self._on_remove_clicked)
        folder_buttons.addWidget(self.remove_button)

        folder_buttons.addStretch()
        layout.addLayout(folder_buttons)

        stats_group = QGroupBox(_("Index Statistics"))
        stats_layout = QFormLayout(stats_group)
        self.total_files_label = QLabel("-")
        self.errors_label = QLabel("-")
        stats_layout.addRow(_("Total indexed files:"), self.total_files_label)
        stats_layout.addRow(_("Files with errors:"), self.errors_label)
        layout.addWidget(stats_group)

        rebuild_row = QHBoxLayout()
        rebuild_row.addStretch()
        self.rebuild_button = QPushButton(_("Clear && Rebuild Catalog..."))
        self.rebuild_button.clicked.connect(self._on_rebuild_clicked)
        rebuild_row.addWidget(self.rebuild_button)
        layout.addLayout(rebuild_row)

        self._update_button_states()

    def _update_button_states(self):
        has_selection = bool(self.folders_tree.selectedItems())
        self.rescan_button.setEnabled(has_selection)
        self.remove_button.setEnabled(has_selection)

    @staticmethod
    def _format_timestamp(value) -> str:
        if not value:
            return _("Never")
        try:
            return datetime.fromtimestamp(float(value)).strftime("%Y-%m-%d %H:%M")
        except (TypeError, ValueError, OSError):
            return _("Unknown")

    def reload(self):
        """Refreshes the folder list and index stats from the database.
        Safe to call whether or not the dialog is currently visible - e.g.
        from the catalog worker's folder_finished signal while this dialog
        is minimized."""
        selected_paths = set(self._selected_paths())
        self.folders_tree.clear()
        for info in app_db.media_db.get_catalog_root_details():
            item = QTreeWidgetItem(self.folders_tree)
            last_scanned = self._format_timestamp(info["date_last_scanned"])
            item.setText(0, info["path"])
            item.setData(0, Qt.ItemDataRole.UserRole, info["path"])
            item.setText(1, str(info["file_count"]))
            item.setText(2, last_scanned)
            desc = _("Folder: {path}. Files: {count}. Last scanned: {scanned}.").format(
                path=info["path"], count=info["file_count"], scanned=last_scanned
            )
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc)
            self.folders_tree.addTopLevelItem(item)
            if info["path"] in selected_paths:
                item.setSelected(True)
        self._update_button_states()
        self._reload_stats()

    def _reload_stats(self):
        try:
            stats = app_db.media_db.get_index_stats()
        except Exception:
            return
        self.total_files_label.setText(str(stats.get("total_files", 0)))
        self.errors_label.setText(str(stats.get("files_with_errors", 0)))

    def _selected_paths(self):
        return [item.data(0, Qt.ItemDataRole.UserRole) for item in self.folders_tree.selectedItems()]

    @Slot()
    def _on_add_clicked(self):
        path = QFileDialog.getExistingDirectory(self, _("Select Folder to Catalog"))
        if not path:
            return
        self._main_window.catalog_folder(path)

    @Slot()
    def _on_rescan_clicked(self):
        for path in self._selected_paths():
            self._main_window.catalog_folder(path)

    @Slot()
    def _on_remove_clicked(self):
        paths = self._selected_paths()
        if not paths:
            return
        reply = QMessageBox.question(
            self,
            _("Remove from Database"),
            _("Remove {count} folder(s) from the database? Their indexed "
              "entries are deleted from the search index; nothing is "
              "touched on disk.").format(count=len(paths)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for path in paths:
            app_db.media_db.remove_catalog_root_and_index(path)
        self.reload()

    @Slot()
    def _on_rebuild_clicked(self):
        reply = QMessageBox.question(
            self,
            _("Clear & Rebuild Catalog"),
            _("This clears the entire media database and re-scans every "
              "previously cataloged folder. Continue?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._main_window.rebuild_catalog()

    @Slot()
    def show_dialog(self):
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.reload()
        self.show()
        self.raise_()
        self.activateWindow()

    @Slot()
    def _on_minimize(self):
        self.hide()
        self.dialog_hidden.emit()

    @Slot()
    def _on_close_requested(self):
        self.close()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.dialog_closed.emit()
        event.accept()

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
                               QLabel, QCheckBox, QMenu, QMessageBox, QComboBox, QTreeView,
                               QHeaderView, QSplitter, QScrollArea, QApplication)
from PySide6.QtCore import Qt, QTimer, Signal, QSortFilterProxyModel
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem
from downloader.downloader import Downloader, DownloadStatus

STATUS_FILTER_ROLE = Qt.ItemDataRole.UserRole + 1
SOURCE_FILTER_ROLE = Qt.ItemDataRole.UserRole + 2

STATUS_LABELS = {
    DownloadStatus.QUEUED: lambda: _("Queued"),
    DownloadStatus.DOWNLOADING: lambda: _("Downloading"),
    DownloadStatus.PAUSED: lambda: _("Paused"),
    DownloadStatus.COMPLETED: lambda: _("Completed"),
    DownloadStatus.FAILED: lambda: _("Failed"),
    DownloadStatus.CANCELLED: lambda: _("Cancelled"),
}


def status_text(status):
    label = STATUS_LABELS.get(status)
    return label() if label else str(status)


def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


class DownloadFilterProxyModel(QSortFilterProxyModel):
    """Backs the secondary read-only QTreeView -- filters by status or by
    "podcast queue" (metadata.source_kind == "podcast") without touching
    the primary QTreeWidget's own row set."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter_kind = "all"

    def set_filter_kind(self, kind):
        self._filter_kind = kind
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if self._filter_kind == "all":
            return True
        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        if self._filter_kind == "podcast":
            return model.data(index, SOURCE_FILTER_ROLE) == "podcast"
        return model.data(index, STATUS_FILTER_ROLE) == self._filter_kind


class DownloaderWidget(QWidget):
    closed = Signal()

    def __init__(self, downloader=None, destination="./temp"):
        super().__init__()

        if downloader is None:
            self.downloader = Downloader(destination=destination)
        else:
            self.downloader = downloader

        self.current_item = None
        self.tree_rows = {}    # DownloadItem -> QTreeWidgetItem
        self.filter_rows = {}  # DownloadItem -> (name_item, size_item, status_item)

        self.setup_ui()
        self.connect_signals()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_list)
        self.update_timer.start(1000)
        self.refresh_list()

    def setup_ui(self):
        self.setWindowTitle(_("Download Manager"))
        self.setMinimumSize(700, 450)

        main_layout = QVBoxLayout()

        top_splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel(_("Downloads:")))
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels([_("Filename"), _("Size"), _("Status")])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.currentItemChanged.connect(self.on_selection_changed)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.setAccessibleName(_("Downloads list"))
        self.tree.setAccessibleDescription(_("List of current, queued, paused, and finished downloads"))
        left_layout.addWidget(self.tree)

        top_splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.info_label = QLabel(_("No download selected"))
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.info_label.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.info_label.setMinimumHeight(100)
        self.info_label.setAccessibleName(_("Selected download information"))
        self.info_label.setAccessibleDescription(self.info_label.text())

        # A checkbox, not a push button, ties directly to whether the
        # detail panel below is shown -- per spec, "a label that displays
        # info and is togglable on or off with a checkbox".
        self.more_info_check = QCheckBox(_("Show more info"))
        self.more_info_check.setEnabled(False)
        self.more_info_check.toggled.connect(self.toggle_more_info)

        self.more_info_scroll = QScrollArea()
        self.more_info_scroll.setWidgetResizable(True)
        self.more_info_scroll.setVisible(False)

        self.more_info_content = QLabel()
        self.more_info_content.setWordWrap(True)
        self.more_info_content.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.more_info_content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.more_info_content.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.more_info_content.setAccessibleName(_("Additional download details"))

        self.more_info_scroll.setWidget(self.more_info_content)

        right_layout.addWidget(QLabel(_("Download Info:")))
        right_layout.addWidget(self.info_label)
        right_layout.addWidget(self.more_info_check)
        right_layout.addWidget(self.more_info_scroll, 1)

        top_splitter.addWidget(right_widget)
        top_splitter.setStretchFactor(0, 2)
        top_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(top_splitter, 2)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(_("Filter:")))
        self.filter_combo = QComboBox()
        self.filter_combo.addItem(_("All"), "all")
        self.filter_combo.addItem(_("Queued"), DownloadStatus.QUEUED.value)
        self.filter_combo.addItem(_("Downloading"), DownloadStatus.DOWNLOADING.value)
        self.filter_combo.addItem(_("Paused"), DownloadStatus.PAUSED.value)
        self.filter_combo.addItem(_("Completed"), DownloadStatus.COMPLETED.value)
        self.filter_combo.addItem(_("Failed"), DownloadStatus.FAILED.value)
        self.filter_combo.addItem(_("Podcast Queue"), "podcast")
        self.filter_combo.setAccessibleName(_("Download filter"))
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self.filter_combo)
        filter_row.addStretch()
        main_layout.addLayout(filter_row)

        self.filter_model = QStandardItemModel(0, 3, self)
        self.filter_model.setHorizontalHeaderLabels([_("Filename"), _("Size"), _("Status")])
        self.filter_proxy = DownloadFilterProxyModel(self)
        self.filter_proxy.setSourceModel(self.filter_model)

        self.filter_view = QTreeView()
        self.filter_view.setModel(self.filter_proxy)
        self.filter_view.setRootIsDecorated(False)
        self.filter_view.setAlternatingRowColors(True)
        self.filter_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.filter_view.setAccessibleName(_("Filtered downloads view"))
        self.filter_view.setAccessibleDescription(_("Downloads filtered by status or podcast queue"))
        main_layout.addWidget(self.filter_view, 1)

        self.setLayout(main_layout)

    def connect_signals(self):
        self.downloader.download_started.connect(self.on_download_started)
        self.downloader.download_finished.connect(self.on_download_finished)
        self.downloader.queue_changed.connect(self.refresh_list)

    def add_download(self, url, destination=None, filename=None):
        return self.downloader.add_download(url, destination, filename)

    def on_download_started(self, download_item):
        self.refresh_list()

    def on_download_finished(self, download_item, success):
        self.refresh_list()

    def _on_filter_changed(self, index):
        self.filter_proxy.set_filter_kind(self.filter_combo.itemData(index))

    def _all_items(self):
        buckets = self.downloader.get_all_downloads()
        items = []
        for key in ('active', 'paused', 'queue', 'completed', 'failed'):
            items.extend(buckets.get(key, []))
        return items

    def refresh_list(self):
        items = self._all_items()
        seen = set(items)

        for item in items:
            self._update_tree_row(item)
            self._update_filter_row(item)

        for item in list(self.tree_rows.keys()):
            if item not in seen:
                self._remove_tree_row(item)
        for item in list(self.filter_rows.keys()):
            if item not in seen:
                self._remove_filter_row(item)

        if self.current_item is not None and self.current_item in seen:
            self.update_info_display()
            if self.more_info_check.isChecked():
                self.update_more_info_display()

    def _size_text(self, item):
        if item.total_size:
            return f"{format_size(item.downloaded_size)} / {format_size(item.total_size)}"
        return format_size(item.downloaded_size)

    def _update_tree_row(self, item):
        size_text = self._size_text(item)
        status = status_text(item.status)
        row = self.tree_rows.get(item)
        if row is None:
            row = QTreeWidgetItem([item.filename, size_text, status])
            row.setData(0, Qt.ItemDataRole.UserRole, item)
            self.tree.addTopLevelItem(row)
            self.tree_rows[item] = row
        else:
            if row.text(0) != item.filename:
                row.setText(0, item.filename)
            if row.text(1) != size_text:
                row.setText(1, size_text)
            if row.text(2) != status:
                row.setText(2, status)
        desc = _("{filename}, {size}, {status}").format(filename=item.filename, size=size_text, status=status)
        row.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc)

    def _remove_tree_row(self, item):
        row = self.tree_rows.pop(item, None)
        if row is None:
            return
        index = self.tree.indexOfTopLevelItem(row)
        if index >= 0:
            self.tree.takeTopLevelItem(index)
        if self.current_item is item:
            self.current_item = None

    def _update_filter_row(self, item):
        size_text = self._size_text(item)
        status = status_text(item.status)
        source_kind = item.metadata.get("source_kind", "")
        row_items = self.filter_rows.get(item)
        if row_items is None:
            name_item = QStandardItem(item.filename)
            size_item = QStandardItem(size_text)
            status_item = QStandardItem(status)
            for cell in (name_item, size_item, status_item):
                cell.setEditable(False)
            self.filter_model.appendRow([name_item, size_item, status_item])
            self.filter_rows[item] = (name_item, size_item, status_item)
        else:
            name_item, size_item, status_item = row_items
            if name_item.text() != item.filename:
                name_item.setText(item.filename)
            if size_item.text() != size_text:
                size_item.setText(size_text)
            if status_item.text() != status:
                status_item.setText(status)
        name_item = self.filter_rows[item][0]
        name_item.setData(item.status.value, STATUS_FILTER_ROLE)
        name_item.setData(source_kind, SOURCE_FILTER_ROLE)

    def _remove_filter_row(self, item):
        row_items = self.filter_rows.pop(item, None)
        if row_items is None:
            return
        self.filter_model.removeRow(row_items[0].row())

    def on_selection_changed(self, current, previous):
        item = current.data(0, Qt.ItemDataRole.UserRole) if current else None
        self.current_item = item
        if item is None:
            self.info_label.setText(_("No download selected"))
            self.info_label.setAccessibleDescription(self.info_label.text())
            self.more_info_check.setEnabled(False)
            self.more_info_check.setChecked(False)
            self.more_info_scroll.setVisible(False)
            return

        self.update_info_display()
        self.more_info_check.setEnabled(True)
        if self.more_info_check.isChecked():
            self.update_more_info_display()

    def on_item_double_clicked(self, item, column):
        download_item = item.data(0, Qt.ItemDataRole.UserRole)
        if not download_item:
            return
        if download_item.status == DownloadStatus.DOWNLOADING:
            self.downloader.pause_download(download_item)
        elif download_item.status == DownloadStatus.PAUSED:
            self.downloader.resume_download(download_item)

    def update_info_display(self):
        if not self.current_item:
            return

        info = self.current_item.get_info()
        status_label = status_text(self.current_item.status)

        text = f"<b>{_('Filename')}:</b> {info['filename']}<br>"
        text += f"<b>{_('Status')}:</b> {status_label}<br>"
        text += f"<b>{_("Progress")}:</b> {format_size(info['downloaded_size'])} / "
        text += f"{format_size(info['total_size'])}<br>"
        text += f"<b>{_("Speed")}:</b> {format_size(info['speed'])}/s"
        if info.get('metadata', {}).get('source_kind'):
            text += f"<br><b>{_('Source')}:</b> {info['metadata']['source_kind']}"

        if info['error']:
            text += f"<br><b style='color: red;'>{_("Error")}:</b> {info['error']}"

        self.info_label.setText(text)

        # Plain-text mirror of the HTML above - a screen reader reading
        # accessibleDescription verbatim shouldn't hear literal "<b>" tags.
        plain = (
            f"{_('Filename')}: {info['filename']}. "
            f"{_('Status')}: {status_label}. "
            f"{_('Progress')}: {format_size(info['downloaded_size'])} / "
            f"{format_size(info['total_size'])}. "
            f"{_('Speed')}: {format_size(info['speed'])}/s."
        )
        if info['error']:
            plain += f" {_('Error')}: {info['error']}"
        self.info_label.setAccessibleDescription(plain)

    def update_more_info_display(self):
        if not self.current_item:
            return

        info = self.current_item.get_info()

        text = f"<b>{_("URL")}:</b><br>{info['url']}<br><br>"
        text += f"<b>{_("Destination")}:</b><br>{info['destination']}<br><br>"
        text += f"<b>{_("Full Path")}:</b><br>{info['filepath']}<br><br>"
        text += f"<b>{_("Retry Count")}:</b> {info['retry_count']}<br>"

        if info['error']:
            text += f"<br><b>{_("Error Details")}:</b><br>{info['error']}"

        plain = (
            f"{_('URL')}: {info['url']}. "
            f"{_('Destination')}: {info['destination']}. "
            f"{_('Full Path')}: {info['filepath']}. "
            f"{_('Retry Count')}: {info['retry_count']}."
        )
        if info['error']:
            plain += f" {_('Error Details')}: {info['error']}"
        self.more_info_content.setAccessibleDescription(plain)

        self.more_info_content.setText(text)

    def toggle_more_info(self, checked):
        self.more_info_scroll.setVisible(checked)
        if checked:
            self.update_more_info_display()

    def show_context_menu(self, position):
        current = self.tree.currentItem()
        if not current:
            return

        download_item = current.data(0, Qt.ItemDataRole.UserRole)
        if not download_item:
            return

        menu = QMenu(self)

        copy_url_action = QAction(_("Copy URL"), self)
        copy_url_action.triggered.connect(lambda: self.copy_to_clipboard(download_item.url))
        menu.addAction(copy_url_action)

        copy_dest_action = QAction(_("Copy Destination"), self)
        copy_dest_action.triggered.connect(lambda: self.copy_to_clipboard(str(download_item.filepath)))
        menu.addAction(copy_dest_action)

        menu.addSeparator()

        if download_item.status == DownloadStatus.DOWNLOADING:
            pause_action = QAction(_("Pause Download"), self)
            pause_action.triggered.connect(lambda: self.downloader.pause_download(download_item))
            menu.addAction(pause_action)

            cancel_action = QAction(_("Cancel Download"), self)
            cancel_action.triggered.connect(lambda: self.downloader.cancel_download(download_item))
            menu.addAction(cancel_action)
        elif download_item.status in (DownloadStatus.PAUSED, DownloadStatus.QUEUED):
            if download_item.status == DownloadStatus.PAUSED:
                resume_action = QAction(_("Resume Download"), self)
                resume_action.triggered.connect(lambda: self.downloader.resume_download(download_item))
                menu.addAction(resume_action)

            cancel_action = QAction(_("Cancel Download"), self)
            cancel_action.triggered.connect(lambda: self.downloader.cancel_download(download_item))
            menu.addAction(cancel_action)

        if download_item.status == DownloadStatus.FAILED:
            retry_action = QAction(_("Retry Download"), self)
            retry_action.triggered.connect(lambda: self.downloader.retry_download(download_item))
            menu.addAction(retry_action)

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def copy_to_clipboard(self, text):
        QApplication.clipboard().setText(text)

    def close_with_confirmation(self) -> bool:
        """Returns True if it's OK for the caller (DownloaderDialog) to
        proceed with closing, False if the user cancelled."""
        active_downloads = self.downloader.get_all_downloads()['active']

        if active_downloads:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(_("Downloads in Progress"))
            msg_box.setText(
                _("{count} download(s) are still in progress.").format(count=len(active_downloads))
            )
            msg_box.setInformativeText(_("What would you like to do?"))

            abort_btn = msg_box.addButton(_("Abort Downloads"), QMessageBox.ButtonRole.DestructiveRole)
            cancel_btn = msg_box.addButton(_("Cancel"), QMessageBox.ButtonRole.RejectRole)
            msg_box.setDefaultButton(cancel_btn)
            msg_box.exec()

            if msg_box.clickedButton() == abort_btn:
                for item in active_downloads.copy():
                    self.downloader.cancel_download(item)
                return True
            return False

        return True

    def closeEvent(self, event):
        self.update_timer.stop()
        self.closed.emit()
        event.accept()

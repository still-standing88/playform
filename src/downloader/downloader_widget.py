from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
                               QLabel, QCheckBox, QMenu, QMessageBox, QTreeView,
                               QHeaderView, QSplitter, QScrollArea, QApplication)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QStandardItemModel, QStandardItem
from downloader.downloader import Downloader, DownloadStatus

CATEGORY_ROLE = Qt.ItemDataRole.UserRole + 1

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


class DownloaderWidget(QWidget):
    closed = Signal()

    def __init__(self, downloader=None, destination="./temp"):
        super().__init__()

        if downloader is None:
            self.downloader = Downloader(destination=destination)
        else:
            self.downloader = downloader

        self.current_item = None
        self.category_filter = "all"
        self.tree_rows = {}    # DownloadItem -> QTreeWidgetItem

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

        category_widget = QWidget()
        category_layout = QVBoxLayout(category_widget)
        category_layout.setContentsMargins(0, 0, 0, 0)

        category_layout.addWidget(QLabel(_("Categories:")))
        self.category_model = QStandardItemModel(self)
        self._populate_category_model()

        self.category_tree = QTreeView()
        self.category_tree.setModel(self.category_model)
        self.category_tree.setHeaderHidden(True)
        self.category_tree.setRootIsDecorated(False)
        self.category_tree.setAlternatingRowColors(True)
        self.category_tree.setAccessibleName(_("Download categories"))
        self.category_tree.setAccessibleDescription(_("Filter the downloads list by status or source"))
        self.category_tree.selectionModel().currentChanged.connect(self.on_category_changed)
        category_layout.addWidget(self.category_tree)

        top_splitter.addWidget(category_widget)

        middle_widget = QWidget()
        middle_layout = QVBoxLayout(middle_widget)
        middle_layout.setContentsMargins(0, 0, 0, 0)

        middle_layout.addWidget(QLabel(_("Downloads:")))
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
        middle_layout.addWidget(self.tree)

        top_splitter.addWidget(middle_widget)

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
        top_splitter.setStretchFactor(0, 0)
        top_splitter.setStretchFactor(1, 2)
        top_splitter.setStretchFactor(2, 1)
        top_splitter.setSizes([160, 500, 300])

        main_layout.addWidget(top_splitter, 1)

        self.setLayout(main_layout)

        self.category_tree.setCurrentIndex(self.category_model.index(0, 0))

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

    def _populate_category_model(self):
        self.category_model.clear()
        root = self.category_model.invisibleRootItem()
        categories = [
            (_("All"), "all"),
            (_("Queued"), DownloadStatus.QUEUED.value),
            (_("Downloading"), DownloadStatus.DOWNLOADING.value),
            (_("Paused"), DownloadStatus.PAUSED.value),
            (_("Completed"), DownloadStatus.COMPLETED.value),
            (_("Failed"), DownloadStatus.FAILED.value),
            (_("Podcast Queue"), "podcast"),
        ]
        for label, kind in categories:
            entry = QStandardItem(label)
            entry.setEditable(False)
            entry.setData(kind, CATEGORY_ROLE)
            root.appendRow(entry)

    def on_category_changed(self, current, previous):
        if not current.isValid():
            return
        self.category_filter = self.category_model.itemFromIndex(current).data(CATEGORY_ROLE)
        self._apply_category_filter()

    def _item_matches_category(self, download_item):
        if self.category_filter == "all":
            return True
        if self.category_filter == "podcast":
            return download_item.metadata.get("source_kind") == "podcast"
        return download_item.status.value == self.category_filter

    def _apply_category_filter(self):
        for download_item, row in self.tree_rows.items():
            row.setHidden(not self._item_matches_category(download_item))

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

        for item in list(self.tree_rows.keys()):
            if item not in seen:
                self._remove_tree_row(item)

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
        row.setHidden(not self._item_matches_category(item))

    def _remove_tree_row(self, item):
        row = self.tree_rows.pop(item, None)
        if row is None:
            return
        index = self.tree.indexOfTopLevelItem(row)
        if index >= 0:
            self.tree.takeTopLevelItem(index)
        if self.current_item is item:
            self.current_item = None

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

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                               QListWidgetItem, QLabel, QPushButton, QMenu,
                               QMessageBox, QProgressBar, QFrame, QScrollArea)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QClipboard
from downloader.downloader import Downloader, DownloadStatus
from pathlib import Path


class DownloadListItem(QWidget):
    def __init__(self, download_item):
        super().__init__()
        self.download_item = download_item
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        self.filename_label = QLabel(download_item.filename)
        self.filename_label.setStyleSheet("font-weight: bold;")
        
        self.status_label = QLabel(download_item.status.value)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        
        info_layout = QHBoxLayout()
        self.size_label = QLabel("0 B / 0 B")
        self.speed_label = QLabel("0 B/s")
        info_layout.addWidget(self.size_label)
        info_layout.addStretch()
        info_layout.addWidget(self.speed_label)
        
        layout.addWidget(self.filename_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addLayout(info_layout)
        
        self.setLayout(layout)
        
        download_item.progress_changed.connect(self.update_progress)
        download_item.status_changed.connect(self.update_status)
        download_item.speed_changed.connect(self.update_speed)
    
    def update_progress(self, downloaded, total):
        if total > 0:
            percentage = int((downloaded / total) * 100)
            self.progress_bar.setValue(percentage)
        
        self.size_label.setText(f"{self.format_size(downloaded)} / {self.format_size(total)}")
    
    def update_status(self, status):
        self.status_label.setText(status.value)
        
        if status == DownloadStatus.COMPLETED:
            self.progress_bar.setValue(100)
            self.status_label.setStyleSheet("color: green;")
        elif status == DownloadStatus.FAILED:
            self.status_label.setStyleSheet("color: red;")
        elif status == DownloadStatus.CANCELLED:
            self.status_label.setStyleSheet("color: orange;")
        elif status == DownloadStatus.DOWNLOADING:
            self.status_label.setStyleSheet("color: blue;")
        else:
            self.status_label.setStyleSheet("")
    
    def update_speed(self, speed):
        self.speed_label.setText(f"{self.format_size(speed)}/s")
    
    @staticmethod
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
        self.list_items = {}
        
        self.setup_ui()
        self.connect_signals()
        
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_list)
        self.update_timer.start(1000)
    
    def setup_ui(self):
        self.setWindowTitle("Download Manager")
        self.setMinimumSize(600, 400)
        
        main_layout = QHBoxLayout()
        
        left_layout = QVBoxLayout()
        
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.currentItemChanged.connect(self.on_selection_changed)
        
        left_layout.addWidget(QLabel("Downloads:"))
        left_layout.addWidget(self.list_widget)
        
        button_layout = QHBoxLayout()
        
        self.minimize_btn = QPushButton("Minimize")
        self.minimize_btn.clicked.connect(self.showMinimized)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close_with_confirmation)
        
        button_layout.addWidget(self.minimize_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        left_layout.addLayout(button_layout)
        
        right_layout = QVBoxLayout()
        
        self.info_label = QLabel("No download selected")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignTop)
        self.info_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.info_label.setFocusPolicy(Qt.TabFocus)
        self.info_label.setMinimumHeight(100)
        
        self.more_info_btn = QPushButton("More Info")
        self.more_info_btn.setCheckable(True)
        self.more_info_btn.clicked.connect(self.toggle_more_info)
        self.more_info_btn.setEnabled(False)
        
        self.more_info_scroll = QScrollArea()
        self.more_info_scroll.setWidgetResizable(True)
        self.more_info_scroll.setVisible(False)
        
        self.more_info_content = QLabel()
        self.more_info_content.setWordWrap(True)
        self.more_info_content.setAlignment(Qt.AlignTop)
        self.more_info_content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.more_info_content.setFocusPolicy(Qt.TabFocus)
        
        self.more_info_scroll.setWidget(self.more_info_content)
        
        right_layout.addWidget(QLabel("Download Info:"))
        right_layout.addWidget(self.info_label)
        right_layout.addWidget(self.more_info_btn)
        right_layout.addWidget(self.more_info_scroll, 1)
        
        main_layout.addLayout(left_layout, 2)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        main_layout.addLayout(right_layout, 1)
        
        self.setLayout(main_layout)
    
    def connect_signals(self):
        self.downloader.download_started.connect(self.on_download_started)
        self.downloader.download_finished.connect(self.on_download_finished)
        self.downloader.queue_changed.connect(self.refresh_list)
    
    def add_download(self, url, destination=None, filename=None):
        return self.downloader.add_download(url, destination, filename)
    
    def on_download_started(self, download_item):
        self.add_item_to_list(download_item)
    
    def on_download_finished(self, download_item, success):
        if download_item in self.list_items:
            list_widget_item = self.list_items[download_item]
            widget = self.list_widget.itemWidget(list_widget_item)
            if widget:
                widget.update_status(download_item.status)
    
    def add_item_to_list(self, download_item):
        if download_item in self.list_items:
            return
        
        list_item = QListWidgetItem()
        widget = DownloadListItem(download_item)
        
        list_item.setSizeHint(widget.sizeHint())
        self.list_widget.addItem(list_item)
        self.list_widget.setItemWidget(list_item, widget)
        
        self.list_items[download_item] = list_item
    
    def refresh_list(self):
        all_downloads = self.downloader.get_all_downloads()
        
        for item in all_downloads['active']:
            self.add_item_to_list(item)
        
        for item in all_downloads['queue']:
            self.add_item_to_list(item)
        
        for item in all_downloads['completed']:
            self.add_item_to_list(item)
        
        for item in all_downloads['failed']:
            self.add_item_to_list(item)
    
    def on_selection_changed(self, current, previous):
        if not current:
            self.current_item = None
            self.info_label.setText("No download selected")
            self.more_info_btn.setEnabled(False)
            self.more_info_btn.setChecked(False)
            self.more_info_scroll.setVisible(False)
            return
        
        for download_item, list_item in self.list_items.items():
            if list_item == current:
                self.current_item = download_item
                self.update_info_display()
                self.more_info_btn.setEnabled(True)
                if self.more_info_btn.isChecked():
                    self.update_more_info_display()
                break
    
    def update_info_display(self):
        if not self.current_item:
            return
        
        info = self.current_item.get_info()
        
        text = f"<b>Filename:</b> {info['filename']}<br>"
        text += f"<b>Status:</b> {info['status']}<br>"
        text += f"<b>Progress:</b> {DownloadListItem.format_size(info['downloaded_size'])} / "
        text += f"{DownloadListItem.format_size(info['total_size'])}<br>"
        text += f"<b>Speed:</b> {DownloadListItem.format_size(info['speed'])}/s"
        
        if info['error']:
            text += f"<br><b style='color: red;'>Error:</b> {info['error']}"
        
        self.info_label.setText(text)
    
    def update_more_info_display(self):
        if not self.current_item:
            return
        
        info = self.current_item.get_info()
        
        text = f"<b>URL:</b><br>{info['url']}<br><br>"
        text += f"<b>Destination:</b><br>{info['destination']}<br><br>"
        text += f"<b>Full Path:</b><br>{info['filepath']}<br><br>"
        text += f"<b>Retry Count:</b> {info['retry_count']}<br>"
        
        if info['error']:
            text += f"<br><b>Error Details:</b><br>{info['error']}"
        
        self.more_info_content.setText(text)
    
    def toggle_more_info(self):
        is_visible = self.more_info_btn.isChecked()
        self.more_info_scroll.setVisible(is_visible)
        if is_visible:
            self.update_more_info_display()
    
    def show_context_menu(self, position):
        current = self.list_widget.currentItem()
        if not current:
            return
        
        download_item = None
        for item, list_item in self.list_items.items():
            if list_item == current:
                download_item = item
                break
        
        if not download_item:
            return
        
        menu = QMenu(self)
        
        copy_url_action = QAction("Copy URL", self)
        copy_url_action.triggered.connect(lambda: self.copy_to_clipboard(download_item.url))
        
        copy_dest_action = QAction("Copy Destination", self)
        copy_dest_action.triggered.connect(lambda: self.copy_to_clipboard(str(download_item.filepath)))
        
        menu.addAction(copy_url_action)
        menu.addAction(copy_dest_action)
        
        if download_item.status == DownloadStatus.DOWNLOADING:
            cancel_action = QAction("Cancel Download", self)
            cancel_action.triggered.connect(lambda: self.downloader.cancel_download(download_item))
            menu.addAction(cancel_action)
        
        if download_item.status == DownloadStatus.FAILED:
            retry_action = QAction("Retry Download", self)
            retry_action.triggered.connect(lambda: self.downloader.retry_download(download_item))
            menu.addAction(retry_action)
        
        menu.exec(self.list_widget.mapToGlobal(position))
    
    def copy_to_clipboard(self, text):
        clipboard = QClipboard()
        clipboard.setText(text)
    
    def close_with_confirmation(self):
        active_downloads = self.downloader.get_all_downloads()['active']
        
        if active_downloads:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Downloads in Progress")
            msg_box.setText(f"{len(active_downloads)} download(s) are still in progress.")
            msg_box.setInformativeText("What would you like to do?")
            
            abort_btn = msg_box.addButton("Abort Downloads", QMessageBox.DestructiveRole)
            cancel_btn = msg_box.addButton("Cancel", QMessageBox.RejectRole)
            
            msg_box.setDefaultButton(cancel_btn)
            msg_box.exec()
            
            if msg_box.clickedButton() == abort_btn:
                for item in active_downloads.copy():
                    self.downloader.cancel_download(item)
                self.close()
            else:
                return
        else:
            self.close()
    
    def closeEvent(self, event):
        self.update_timer.stop()
        self.closed.emit()
        event.accept()

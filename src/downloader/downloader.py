from PySide6.QtCore import QObject, Signal, QUrl, QFile, QIODevice, QTimer
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from pathlib import Path
from datetime import datetime
from enum import Enum
import time


class DownloadStatus(Enum):
    QUEUED = "Queued"
    DOWNLOADING = "Downloading"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class DownloadItem(QObject):
    progress_changed = Signal(int, int)
    status_changed = Signal(object)
    speed_changed = Signal(float)
    error_occurred = Signal(str)
    finished = Signal(bool)
    
    def __init__(self, url, destination, filename=None):
        super().__init__()
        self.url = url
        self.destination = Path(destination)
        self.filename = filename or Path(QUrl(url).path()).name or "download"
        self.filepath = self.destination / self.filename
        
        self.status = DownloadStatus.QUEUED
        self.downloaded_size = 0
        self.total_size = 0
        self.download_speed = 0.0
        self.error_message = ""
        self.retry_count = 0
        self.max_retries = 3
        
        self._reply = None
        self._file = None
        self._start_time = None
        self._last_time = None
        self._last_downloaded = 0
        self._speed_samples = []
        self._redirect_count = 0
        self._max_redirects = 5
    
    def get_info(self):
        return {
            'url': self.url,
            'filename': self.filename,
            'destination': str(self.destination),
            'filepath': str(self.filepath),
            'status': self.status.value,
            'downloaded_size': self.downloaded_size,
            'total_size': self.total_size,
            'speed': self.download_speed,
            'error': self.error_message,
            'retry_count': self.retry_count
        }
    
    def set_status(self, status):
        if self.status != status:
            self.status = status
            self.status_changed.emit(status)
    
    def calculate_speed(self):
        current_time = time.time()
        if self._last_time is None:
            self._last_time = current_time
            self._last_downloaded = self.downloaded_size
            return
        
        time_diff = current_time - self._last_time
        if time_diff >= 0.5:
            bytes_diff = self.downloaded_size - self._last_downloaded
            speed = bytes_diff / time_diff if time_diff > 0 else 0
            
            self._speed_samples.append(speed)
            if len(self._speed_samples) > 5:
                self._speed_samples.pop(0)
            
            self.download_speed = sum(self._speed_samples) / len(self._speed_samples)
            self.speed_changed.emit(self.download_speed)
            
            self._last_time = current_time
            self._last_downloaded = self.downloaded_size


class Downloader(QObject):
    download_started = Signal(object)
    download_finished = Signal(object, bool)
    queue_changed = Signal()
    all_finished = Signal()
    
    def __init__(self, destination="./temp", max_concurrent=1):
        super().__init__()
        self.destination = Path(destination)
        self.destination.mkdir(parents=True, exist_ok=True)
        
        self.max_concurrent = max_concurrent
        self.queue = []
        self.active_downloads = []
        self.completed_downloads = []
        self.failed_downloads = []
        
        self._network_managers = []
        self._is_paused = False
        
        for _ in range(max_concurrent):
            manager = QNetworkAccessManager()
            self._network_managers.append(manager)
    
    def add_download(self, url, destination=None, filename=None, progress_callback=None, finished_callback=None):
        dest = Path(destination) if destination else self.destination
        item = DownloadItem(url, dest, filename)
        
        if progress_callback:
            item.progress_changed.connect(progress_callback)
        if finished_callback:
            item.finished.connect(finished_callback)
        
        self.queue.append(item)
        self.queue_changed.emit()

        if not self._is_paused:
            self._process_queue()

        return item

    def pause_queue(self):
        self._is_paused = True

    def resume_queue(self):
        self._is_paused = False
        self._process_queue()

    def cancel_download(self, item):
        if item in self.active_downloads:
            if item._reply:
                item._reply.abort()
            item.set_status(DownloadStatus.CANCELLED)
            self.active_downloads.remove(item)
            self.failed_downloads.append(item)
            self._process_queue()
        elif item in self.queue:
            item.set_status(DownloadStatus.CANCELLED)
            self.queue.remove(item)
            self.failed_downloads.append(item)
            self.queue_changed.emit()
    
    def retry_download(self, item):
        if item in self.failed_downloads:
            self.failed_downloads.remove(item)
            item.retry_count = 0
            item.error_message = ""
            item.set_status(DownloadStatus.QUEUED)
            self.queue.append(item)
            self.queue_changed.emit()
            if not self._is_paused:
                self._process_queue()
    
    def get_download_status(self, item):
        return item.get_info()
    
    def get_all_downloads(self):
        return {
            'queue': self.queue,
            'active': self.active_downloads,
            'completed': self.completed_downloads,
            'failed': self.failed_downloads
        }
    
    def _process_queue(self):
        if self._is_paused:
            return
        
        while len(self.active_downloads) < self.max_concurrent and self.queue:
            item = self.queue.pop(0)
            self._start_download(item)
            self.queue_changed.emit()
    
    def _start_download(self, item):
        manager_index = len(self.active_downloads) % len(self._network_managers)
        manager = self._network_managers[manager_index]
        
        item.destination.mkdir(parents=True, exist_ok=True)
        
        item._file = QFile(str(item.filepath))
        if not item._file.open(QIODevice.WriteOnly):
            item.error_message = f"{_("Cannot open file for writing")}: {item.filepath}"
            item.set_status(DownloadStatus.FAILED)
            item.error_occurred.emit(item.error_message)
            self.failed_downloads.append(item)
            self._process_queue()
            return
        
        request = QNetworkRequest(QUrl(item.url))
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.NoLessSafeRedirectPolicy)
        
        item._reply = manager.get(request)
        item._reply.downloadProgress.connect(lambda received, total: self._on_progress(item, received, total))
        item._reply.finished.connect(lambda: self._on_finished(item))
        item._reply.readyRead.connect(lambda: self._on_ready_read(item))
        item._reply.errorOccurred.connect(lambda error: self._on_error(item, error))
        
        item._start_time = time.time()
        item._last_time = time.time()
        item.set_status(DownloadStatus.DOWNLOADING)
        
        self.active_downloads.append(item)
        self.download_started.emit(item)

    def _on_progress(self, item, bytes_received, bytes_total):
        item.downloaded_size = bytes_received
        item.total_size = bytes_total
        item.calculate_speed()
        item.progress_changed.emit(bytes_received, bytes_total)
    
    def _on_ready_read(self, item):
        if item._file and item._reply:
            item._file.write(item._reply.readAll())
    
    def _on_error(self, item, error):
        if error == QNetworkReply.OperationCanceledError:
            return
        
        error_string = item._reply.errorString() if item._reply else _("Unknown error")
        item.error_message = f"{_("Network error")}: {error_string}"
        item.error_occurred.emit(item.error_message)
    
    def _on_finished(self, item):
        if item._file:
            item._file.close()
        
        if not item._reply:
            return
        
        redirect_url = item._reply.attribute(QNetworkRequest.RedirectionTargetAttribute)
        
        if redirect_url and item._redirect_count < item._max_redirects:
            item._redirect_count += 1
            if redirect_url.isRelative():
                redirect_url = item._reply.url().resolved(redirect_url)
            
            item.url = redirect_url.toString()
            item._reply.deleteLater()
            item._reply = None
            
            if item in self.active_downloads:
                self.active_downloads.remove(item)
            
            self._start_download(item)
            return
        
        if item._redirect_count >= item._max_redirects:
            item.error_message = _("Too many redirects")
            item.set_status(DownloadStatus.FAILED)
            item.finished.emit(False)
            
            if item in self.active_downloads:
                self.active_downloads.remove(item)
            self.failed_downloads.append(item)
            self.download_finished.emit(item, False)
            self._handle_retry(item)
            return
        
        error = item._reply.error()
        
        if error != QNetworkReply.NoError and error != QNetworkReply.OperationCanceledError:
            item.set_status(DownloadStatus.FAILED)
            item.finished.emit(False)
            
            if item in self.active_downloads:
                self.active_downloads.remove(item)
            self.failed_downloads.append(item)
            self.download_finished.emit(item, False)
            self._handle_retry(item)
        else:
            if item.status != DownloadStatus.CANCELLED:
                item.set_status(DownloadStatus.COMPLETED)
                item.finished.emit(True)
                
                if item in self.active_downloads:
                    self.active_downloads.remove(item)
                self.completed_downloads.append(item)
                self.download_finished.emit(item, True)
        
        item._reply.deleteLater()
        item._reply = None
        
        self._process_queue()
        
        if not self.active_downloads and not self.queue:
            self.all_finished.emit()
    
    def _handle_retry(self, item):
        if item.retry_count < item.max_retries:
            item.retry_count += 1
            item.error_message += f" ({_("Retry")} {item.retry_count}/{item.max_retries})"
            
            QTimer.singleShot(2000, lambda: self._retry_download_internal(item))
        else:
            item.error_message += _(" (Max retries reached)")
    
    def _retry_download_internal(self, item):
        if item in self.failed_downloads:
            self.failed_downloads.remove(item)
        item.set_status(DownloadStatus.QUEUED)
        item.downloaded_size = 0
        item._redirect_count = 0
        self.queue.insert(0, item)
        self.queue_changed.emit()
        self._process_queue()

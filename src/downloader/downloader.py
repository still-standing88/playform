import json
import logging
import os
import time
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QUrl, QFile, QIODevice, QTimer
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply, QNetworkProxy


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

    def __init__(self, url, destination, filename=None, metadata=None, item_id=None):
        super().__init__()
        self.id = item_id or uuid.uuid4().hex
        self.url = url
        self.destination = Path(destination)
        self.filename = filename or Path(QUrl(url).path()).name or "download"
        self.filepath = self.destination / self.filename
        # Arbitrary caller-supplied tags, e.g. {"source_kind": "podcast",
        # "podcast_feed_url": ..., "episode_title": ...} -- lets callers
        # (podcast episode downloads, yt-dlp binary fetches, ...) mark what
        # a queued item actually is without Downloader needing to know
        # about any of them specifically.
        self.metadata = metadata or {}

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
        # Range-resume bookkeeping -- see Downloader._start_download/_on_ready_read.
        self._resume_offset = 0
        self._resume_confirmed = True
        # Token-bucket state for speed limiting -- see Downloader._apply_speed_limit.
        self._throttle_bucket = 0.0
        self._throttle_last = 0.0

    def get_info(self):
        return {
            'id': self.id,
            'url': self.url,
            'filename': self.filename,
            'destination': str(self.destination),
            'filepath': str(self.filepath),
            'status': self.status.value,
            'downloaded_size': self.downloaded_size,
            'total_size': self.total_size,
            'speed': self.download_speed,
            'error': self.error_message,
            'retry_count': self.retry_count,
            'metadata': self.metadata,
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

    def __init__(self, destination="./temp", max_concurrent=1, persist=True):
        super().__init__()
        self.destination = Path(destination)
        self.destination.mkdir(parents=True, exist_ok=True)

        self.max_concurrent = max_concurrent
        self.queue = []
        self.active_downloads = []
        self.paused_downloads = []
        self.completed_downloads = []
        self.failed_downloads = []

        self._network_managers = []
        self._is_paused = False
        self._persist_enabled = persist
        self._speed_limit_kbps = 0
        self._retry_count = 3
        self._retry_delay_ms = 2000
        self._proxy = None

        for _ in range(max_concurrent):
            manager = QNetworkAccessManager()
            self._network_managers.append(manager)

        if self._persist_enabled:
            self.restore()

    def apply_settings(self, max_parallel=None, speed_limit_kbps=None,
                       retry_count=None, retry_delay_ms=None):
        """Live-apply download settings (from the Downloads prefs panel).
        Only max_parallel requires structural change; the rest take effect
        on the next transfer tick/retry."""
        if speed_limit_kbps is not None:
            self._speed_limit_kbps = max(0, int(speed_limit_kbps))
        if retry_count is not None:
            self._retry_count = max(0, int(retry_count))
        if retry_delay_ms is not None:
            self._retry_delay_ms = max(250, int(retry_delay_ms))
        if max_parallel is not None and int(max_parallel) != self.max_concurrent:
            self.max_concurrent = max(1, int(max_parallel))
            while len(self._network_managers) < self.max_concurrent:
                manager = QNetworkAccessManager()
                self._apply_proxy_to_manager(manager)
                self._network_managers.append(manager)

    def apply_proxy(self, enabled=False, proxy_type="http", host="", port=0,
                    user="", password=""):
        """Configure a QNetworkProxy for every managed network access
        manager. Passing enabled=False clears any previously set proxy."""
        from PySide6.QtNetwork import QNetworkProxy as _QP
        type_map = {
            "http": _QP.HttpProxy,
            "socks5": _QP.Socks5Proxy,
        }
        if not enabled or not host:
            proxy = _QP(_QP.DefaultProxy)
        else:
            proxy = _QP(type_map.get(proxy_type, _QP.HttpProxy), host, int(port))
            if user:
                proxy.setUser(user)
            if password:
                proxy.setPassword(password)
        self._proxy = proxy
        for manager in self._network_managers:
            manager.setProxy(proxy)

    def _apply_proxy_to_manager(self, manager):
        if self._proxy is not None:
            manager.setProxy(self._proxy)

    def add_download(self, url, destination=None, filename=None, progress_callback=None, finished_callback=None, metadata=None):
        dest = Path(destination) if destination else self.destination
        item = DownloadItem(url, dest, filename, metadata=metadata)
        self._dedupe_filename(item)

        if progress_callback:
            item.progress_changed.connect(progress_callback)
        if finished_callback:
            item.finished.connect(finished_callback)

        self.queue.append(item)
        self.queue_changed.emit()
        self._persist_item(item)

        if not self._is_paused:
            self._process_queue()

        return item

    def _dedupe_filename(self, item):
        """Avoid clobbering an existing file (or another queued item's
        target) by appending " (n)" before the extension."""
        candidate = item.filename
        base, ext = os.path.splitext(candidate)
        n = 1
        taken = {other.filename for other in
                 self.queue + self.active_downloads + self.paused_downloads}
        while (item.destination / candidate).exists() or candidate in taken:
            candidate = f"{base} ({n}){ext}"
            n += 1
        item.filename = candidate
        item.filepath = item.destination / candidate

    def pause_queue(self):
        self._is_paused = True

    def resume_queue(self):
        self._is_paused = False
        self._process_queue()

    def pause_download(self, item):
        """Gracefully stops an item without discarding its progress -- the
        partial file and downloaded_size are kept so resume_download() can
        continue it via an HTTP Range request instead of restarting from 0."""
        if item in self.active_downloads:
            item.set_status(DownloadStatus.PAUSED)
            self.active_downloads.remove(item)
            self.paused_downloads.append(item)
            if item._reply:
                item._reply.abort()
            self.queue_changed.emit()
            self._persist_item(item)
            self._process_queue()
        elif item in self.queue:
            item.set_status(DownloadStatus.PAUSED)
            self.queue.remove(item)
            self.paused_downloads.append(item)
            self.queue_changed.emit()
            self._persist_item(item)

    def resume_download(self, item):
        if item in self.paused_downloads:
            self.paused_downloads.remove(item)
            item.set_status(DownloadStatus.QUEUED)
            item.error_message = ""
            self.queue.insert(0, item)
            self.queue_changed.emit()
            self._persist_item(item)
            if not self._is_paused:
                self._process_queue()

    def cancel_download(self, item):
        if item in self.active_downloads:
            if item._reply:
                item._reply.abort()
            item.set_status(DownloadStatus.CANCELLED)
            self.active_downloads.remove(item)
            self.failed_downloads.append(item)
            self._remove_part_file(item)
            self._record_history(item)
            self._forget_item(item)
            self._process_queue()
        elif item in self.paused_downloads:
            item.set_status(DownloadStatus.CANCELLED)
            self.paused_downloads.remove(item)
            self.failed_downloads.append(item)
            self._remove_part_file(item)
            self._record_history(item)
            self._forget_item(item)
            self.queue_changed.emit()
        elif item in self.queue:
            item.set_status(DownloadStatus.CANCELLED)
            self.queue.remove(item)
            self.failed_downloads.append(item)
            self._remove_part_file(item)
            self._record_history(item)
            self._forget_item(item)
            self.queue_changed.emit()

    def _remove_part_file(self, item):
        part_path = item.filepath.with_name(item.filepath.name + ".part")
        try:
            if part_path.exists():
                part_path.unlink()
        except OSError:
            logging.exception("Downloader: failed to remove .part file for %r", getattr(item, "id", None))

    def retry_download(self, item):
        if item in self.failed_downloads:
            self.failed_downloads.remove(item)
            item.retry_count = 0
            item.error_message = ""
            item.set_status(DownloadStatus.QUEUED)
            self.queue.append(item)
            self.queue_changed.emit()
            self._persist_item(item)
            if not self._is_paused:
                self._process_queue()

    def get_download_status(self, item):
        return item.get_info()

    def get_all_downloads(self):
        return {
            'queue': self.queue,
            'active': self.active_downloads,
            'paused': self.paused_downloads,
            'completed': self.completed_downloads,
            'failed': self.failed_downloads
        }

    # ------------------------------------------------------------------
    # Persistence -- download_queue table in user.sqlite3 (see app_db.user_db).
    # Lets queued/paused downloads (including podcast episodes) survive an
    # app restart; the Downloader itself owns this, independent of whether
    # any GUI dialog is open, per "controllable from the background".
    # ------------------------------------------------------------------
    def _persist_item(self, item):
        if not self._persist_enabled:
            return
        try:
            from app_db import user_db
            user_db.save_download_queue_row({
                "id": item.id,
                "url": item.url,
                "destination": str(item.destination),
                "filename": item.filename,
                "status": item.status.value,
                "downloaded_size": item.downloaded_size,
                "total_size": item.total_size,
                "metadata": json.dumps(item.metadata),
                "added_at": getattr(item, "_added_at", None) or datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            })
        except Exception:
            logging.exception("Downloader: failed to persist item %r", getattr(item, "id", None))

    def _forget_item(self, item):
        if not self._persist_enabled:
            return
        try:
            from app_db import user_db
            user_db.delete_download_queue_row(item.id)
        except Exception:
            logging.exception("Downloader: failed to remove persisted item %r", getattr(item, "id", None))

    def restore(self):
        """Loads queued/downloading/paused rows back in as paused items --
        conservative on purpose: nothing auto-resumes network activity on
        its own, the user (or a caller) decides when to resume, matching
        "operates under user control"."""
        try:
            from app_db import user_db
            rows = user_db.load_download_queue_rows()
        except Exception:
            logging.exception("Downloader: failed to load persisted download queue")
            return

        for row in rows:
            try:
                status = row.get("status")
                if status not in (
                    DownloadStatus.QUEUED.value, DownloadStatus.DOWNLOADING.value, DownloadStatus.PAUSED.value,
                ):
                    continue
                metadata = {}
                if row.get("metadata"):
                    try:
                        metadata = json.loads(row["metadata"])
                    except Exception:
                        metadata = {}
                item = DownloadItem(row["url"], row["destination"], row["filename"], metadata=metadata, item_id=row["id"])
                item.downloaded_size = row.get("downloaded_size") or 0
                item.total_size = row.get("total_size") or 0
                item._added_at = row.get("added_at")
                item.status = DownloadStatus.PAUSED
                self.paused_downloads.append(item)
            except Exception:
                logging.exception("Downloader: failed to restore a persisted download row; skipping")

        if self.paused_downloads:
            self.queue_changed.emit()

        self._restore_history()

    def _restore_history(self):
        try:
            from app_db import user_db
            rows = user_db.load_download_history_rows()
        except Exception:
            logging.exception("Downloader: failed to load persisted download history")
            return
        for row in rows:
            try:
                status = row.get("status")
                if status not in (DownloadStatus.COMPLETED.value, DownloadStatus.FAILED.value):
                    continue
                metadata = {}
                if row.get("metadata"):
                    try:
                        metadata = json.loads(row["metadata"])
                    except Exception:
                        metadata = {}
                item = DownloadItem(row["url"], row["destination"], row["filename"], metadata=metadata, item_id=row["id"])
                item.downloaded_size = row.get("downloaded_size") or 0
                item.total_size = row.get("total_size") or 0
                item._added_at = row.get("added_at")
                item.status = DownloadStatus(status)
                bucket = self.completed_downloads if item.status == DownloadStatus.COMPLETED else self.failed_downloads
                bucket.append(item)
            except Exception:
                logging.exception("Downloader: failed to restore a persisted history row; skipping")

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

        # All bytes land in a .part sibling and are atomically renamed on
        # completion -- a crash mid-download then leaves only a .part file,
        # never a playable-looking but truncated final file.
        part_path = item.filepath.with_name(item.filepath.name + ".part")

        resume_offset = 0
        if item.downloaded_size > 0 and part_path.exists():
            on_disk_size = part_path.stat().st_size
            if on_disk_size == item.downloaded_size:
                resume_offset = item.downloaded_size
            else:
                # Bookkeeping and file disagree -- safest is a clean restart.
                item.downloaded_size = 0

        item._resume_offset = resume_offset
        item._resume_confirmed = resume_offset == 0
        item._throttle_bucket = 0.0
        item._throttle_last = time.monotonic()

        open_mode = QIODevice.WriteOnly | QIODevice.Append if resume_offset else QIODevice.WriteOnly
        item._file = QFile(str(part_path))
        if not item._file.open(open_mode):
            item.error_message = f"{_("Cannot open file for writing")}: {part_path}"
            item.set_status(DownloadStatus.FAILED)
            item.error_occurred.emit(item.error_message)
            self.failed_downloads.append(item)
            self._forget_item(item)
            self._process_queue()
            return

        request = QNetworkRequest(QUrl(item.url))
        request.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.NoLessSafeRedirectPolicy)
        if resume_offset:
            request.setRawHeader(b"Range", f"bytes={resume_offset}-".encode())

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
        self._persist_item(item)

    def _on_progress(self, item, bytes_received, bytes_total):
        offset = item._resume_offset if item._resume_confirmed else 0
        item.downloaded_size = offset + bytes_received
        if bytes_total > 0:
            item.total_size = offset + bytes_total
        item.calculate_speed()
        item.progress_changed.emit(item.downloaded_size, item.total_size)

    def _on_ready_read(self, item):
        if not item._reply or not item._file:
            return

        if not item._resume_confirmed:
            status = item._reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
            if status == 206:
                item._resume_confirmed = True
            elif status is not None:
                # Server ignored our Range request (e.g. plain 200) --
                # fall back to a full restart so we don't end up with
                # duplicate/corrupt data spliced into the file.
                item._resume_offset = 0
                item.downloaded_size = 0
                try:
                    item._file.close()
                    item._file.open(QIODevice.WriteOnly)
                except Exception:
                    logging.exception("Downloader: failed to truncate file for restarted download")
                item._resume_confirmed = True

        data = bytes(item._reply.readAll())
        item._file.write(data)
        self._apply_speed_limit(item, len(data))

    def _apply_speed_limit(self, item, byte_count):
        """Token-bucket pacing: if a speed limit is configured and this
        chunk arrived faster than the limit allows, sleep the difference.
        Called on the GUI thread -- deliberately bounded (never more than
        ~0.5s per tick) so the event loop isn't starved."""
        if self._speed_limit_kbps <= 0:
            return
        now = time.monotonic()
        elapsed = now - item._throttle_last if item._throttle_last else 0.0
        item._throttle_last = now
        item._throttle_bucket += elapsed * self._speed_limit_kbps * 1024
        item._throttle_bucket = min(item._throttle_bucket, self._speed_limit_kbps * 1024)
        item._throttle_bucket -= byte_count
        if item._throttle_bucket < 0:
            delay = min(-item._throttle_bucket / (self._speed_limit_kbps * 1024), 0.5)
            time.sleep(delay)
            item._throttle_last = time.monotonic()
            item._throttle_bucket = 0.0

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

        if item.status == DownloadStatus.PAUSED:
            # Intentional pause (abort()) -- all bookkeeping already done
            # by pause_download(), just clean up the reply object.
            item._reply.deleteLater()
            item._reply = None
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
            self._forget_item(item)
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
            self._forget_item(item)
            self.download_finished.emit(item, False)
            self._handle_retry(item)
        else:
            if item.status not in (DownloadStatus.CANCELLED, DownloadStatus.PAUSED):
                # Completion validation: when the server told us the total
                # size, verify the on-disk .part actually matches before
                # promoting it -- a truncated-but-clean-close transfer
                # would otherwise count as COMPLETED.
                part_path = item.filepath.with_name(item.filepath.name + ".part")
                expected = item.total_size or (item._resume_offset if not item._resume_confirmed else 0)
                on_disk = part_path.stat().st_size if part_path.exists() else 0
                if item.total_size and on_disk != item.total_size:
                    item.error_message = (
                        _("Size mismatch") + f": {on_disk}/{item.total_size}"
                    )
                    item.set_status(DownloadStatus.FAILED)
                    item.finished.emit(False)
                    if item in self.active_downloads:
                        self.active_downloads.remove(item)
                    self.failed_downloads.append(item)
                    self._forget_item(item)
                    self.download_finished.emit(item, False)
                    self._handle_retry(item)
                else:
                    try:
                        if item.filepath.exists():
                            item.filepath.unlink()
                        if part_path.exists():
                            os.replace(str(part_path), str(item.filepath))
                    except OSError as e:
                        item.error_message = _("Rename failed") + f": {e}"
                        item.set_status(DownloadStatus.FAILED)
                        item.finished.emit(False)
                        if item in self.active_downloads:
                            self.active_downloads.remove(item)
                        self.failed_downloads.append(item)
                        self._forget_item(item)
                        self.download_finished.emit(item, False)
                    else:
                        item.downloaded_size = on_disk
                        item.set_status(DownloadStatus.COMPLETED)
                        item.finished.emit(True)

                        if item in self.active_downloads:
                            self.active_downloads.remove(item)
                        self.completed_downloads.append(item)
                        self._record_history(item)
                        self._forget_item(item)
                        self.download_finished.emit(item, True)

        item._reply.deleteLater()
        item._reply = None

        self._process_queue()

        if not self.active_downloads and not self.queue:
            self.all_finished.emit()

    def _handle_retry(self, item):
        max_retries = self._retry_count if self._persist_enabled else item.max_retries
        if item.retry_count < max_retries:
            item.retry_count += 1
            item.error_message += f" ({_("Retry")} {item.retry_count}/{max_retries})"

            # Exponential backoff from the configured base delay; retries
            # resume from downloaded_size (Range request) instead of
            # restarting from zero, so progress is kept.
            delay = self._retry_delay_ms * (2 ** (item.retry_count - 1))
            QTimer.singleShot(delay, lambda: self._retry_download_internal(item))
        else:
            item.error_message += _(" (Max retries reached)")
            self._record_history(item)

    def _record_history(self, item):
        """Persist a terminal-state row (completed/failed) to the
        download_history table so history survives restarts."""
        if not self._persist_enabled:
            return
        try:
            from app_db import user_db
            user_db.save_download_history_row({
                "id": item.id,
                "url": item.url,
                "destination": str(item.destination),
                "filename": item.filename,
                "status": item.status.value,
                "downloaded_size": item.downloaded_size,
                "total_size": item.total_size,
                "metadata": json.dumps(item.metadata),
                "added_at": getattr(item, "_added_at", None) or datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            })
        except Exception:
            logging.exception("Downloader: failed to record history for %r", getattr(item, "id", None))

    def _forget_history(self, item):
        if not self._persist_enabled:
            return
        try:
            from app_db import user_db
            user_db.delete_download_history_row(item.id)
        except Exception:
            logging.exception("Downloader: failed to remove history for %r", getattr(item, "id", None))

    def _retry_download_internal(self, item):
        if item in self.failed_downloads:
            self.failed_downloads.remove(item)
        item.set_status(DownloadStatus.QUEUED)
        item._redirect_count = 0
        self.queue.insert(0, item)
        self.queue_changed.emit()
        self._persist_item(item)
        self._process_queue()

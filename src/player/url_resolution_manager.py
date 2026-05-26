import logging
import threading
from dataclasses import dataclass, field
from queue import Empty, Queue
from typing import Dict, Optional

from PySide6.QtCore import QObject, Signal

from .url import resolve_media_url


logger = logging.getLogger(__name__)


@dataclass
class PendingResolution:
    event: threading.Event = field(default_factory=threading.Event)
    resolved_url: Optional[str] = None
    error: Optional[str] = None


class UrlResolutionManager(QObject):
    resolved = Signal(str, str)
    failed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue: Queue[Optional[str]] = Queue()
        self._lock = threading.RLock()
        self._cache: Dict[str, str] = {}
        self._pending: Dict[str, PendingResolution] = {}
        self._running = True
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def get_cached(self, url: str) -> Optional[str]:
        with self._lock:
            return self._cache.get(url)

    def request(self, url: str):
        if not url:
            return
        with self._lock:
            if url in self._cache:
                cached = self._cache[url]
            else:
                cached = None
                if url not in self._pending:
                    self._pending[url] = PendingResolution()
                    self._queue.put(url)
        if cached:
            self.resolved.emit(url, cached)

    def resolve_blocking(self, url: str, timeout: Optional[float] = None) -> str:
        if not url:
            raise ValueError("URL is empty")

        with self._lock:
            cached = self._cache.get(url)
            if cached:
                return cached
            pending = self._pending.get(url)
            if pending is None:
                pending = PendingResolution()
                self._pending[url] = pending
                self._queue.put(url)

        if not pending.event.wait(timeout):
            raise TimeoutError(f"Timed out resolving URL: {url}")

        if pending.error:
            raise RuntimeError(pending.error)

        if pending.resolved_url:
            return pending.resolved_url

        raise RuntimeError(f"URL resolution did not produce a result for: {url}")

    def stop(self):
        self._running = False
        self._queue.put(None)
        if self._worker.is_alive():
            self._worker.join(timeout=1.0)

    def _run(self):
        while self._running:
            try:
                url = self._queue.get(timeout=0.2)
            except Empty:
                continue

            if url is None:
                continue

            try:
                resolved_url = resolve_media_url(url)
                with self._lock:
                    pending = self._pending.pop(url, None)
                    self._cache[url] = resolved_url
                if pending is not None:
                    pending.resolved_url = resolved_url
                    pending.event.set()
                self.resolved.emit(url, resolved_url)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to resolve URL {url}: {error_msg}")
                with self._lock:
                    pending = self._pending.pop(url, None)
                if pending is not None:
                    pending.error = error_msg
                    pending.event.set()
                self.failed.emit(url, error_msg)

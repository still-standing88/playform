from __future__ import annotations

import logging
import os
import queue
import threading
from typing import List, Optional, Set

import av_play
from PySide6.QtCore import QObject, Signal, QThread

from .url import (
    is_url_supported,
    resolve_webpage_url,
    run_ytdlp_flat_playlist,
    has_playlist_param,
    is_playlist,
)
from .utilities import ensure_ytdlp_available


logger = logging.getLogger(__name__)


class LazyPlaylistSignals(QObject):
    extraction_started = Signal()
    extraction_complete = Signal(object)
    extraction_failed = Signal(str)


class _UrlExtractThread(QThread):
    result_ready = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, player: LazyPlaylistPlayer) -> None:
        super().__init__(None)
        self._player = player
        self._url: str = ""

    def set_url(self, url: str):
        self._url = url

    def run(self):
        try:
            result = self._player._fetch_webpage_playlist(self._url)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))


class LazyPlaylistSignals(QObject):
    extraction_started = Signal()
    extraction_complete = Signal(object)
    extraction_failed = Signal(str)


class LazyPlaylistPlayer(av_play.VLCVideoPlayer):
    def __init__(self) -> None:
        super().__init__()
        self.signals = LazyPlaylistSignals()

        self._webpage_urls: List[str] = []
        self._resolved: dict[int, str] = {}
        self._resolving: Set[int] = set()
        self._resolve_lock = threading.RLock()
        self._preload_window: int = 3

        self._preload_queue: queue.Queue[int] = queue.Queue()
        self._preload_stop_event = threading.Event()
        self._preload_thread: Optional[threading.Thread] = None

        self._extract_worker: Optional[_UrlExtractThread] = None
        self._pending_url: Optional[str] = None

    def init(self, *args, **kw):
        av_play.VLCVideoPlayer.init(self, *args, **kw)
        self._preload_stop_event.clear()
        if self._preload_thread is None or not self._preload_thread.is_alive():
            self._preload_thread = threading.Thread(
                target=self._preload_worker, daemon=True, name="LazyPlaylistPreload"
            )
            self._preload_thread.start()

    def release(self):
        self._preload_stop_event.set()
        try:
            self._preload_queue.put_nowait(-1)
        except Exception:
            pass
        if self._preload_thread and self._preload_thread.is_alive():
            self._preload_thread.join(timeout=1.0)
        if self._extract_worker and self._extract_worker.isRunning():
            self._extract_worker.quit()
            self._extract_worker.wait(2000)
        av_play.VLCVideoPlayer.release(self)

    def load_playlist(
        self,
        playlist: av_play.Playlist,
        auto_play: bool = False,
        start_index: int = 0,
    ):
        if playlist is None or len(playlist) == 0:
            return

        self._reset_resolution_state(len(playlist))

        for idx, entry in enumerate(playlist.entries):
            location = entry.location or ""
            self._webpage_urls.append(location)
            if location and av_play.is_path(location):
                with self._resolve_lock:
                    self._resolved[idx] = location

        target_index = max(0, min(start_index, len(playlist) - 1))
        if not self._ensure_resolved_blocking(target_index):
            raise RuntimeError(
                f"Failed to resolve playlist entry at index {target_index}"
            )

        av_play.VLCVideoPlayer.load_playlist(
            self, playlist, auto_play=auto_play, start_index=target_index
        )

        self._schedule_preload_ahead(target_index)

    def load_url(self, url: str):
        if not ensure_ytdlp_available(None, show_message=False):
            self.signals.extraction_failed.emit("yt-dlp is not available.")
            return

        if self._extract_worker and self._extract_worker.isRunning():
            self._pending_url = url
            return

        self._pending_url = None
        self.signals.extraction_started.emit()
        self._start_extraction(url)

    def _start_extraction(self, url: str):
        if self._extract_worker is None:
            self._extract_worker = _UrlExtractThread(self)
            self._extract_worker.result_ready.connect(self._on_extraction_done)
            self._extract_worker.error_occurred.connect(self._on_extraction_error)
        self._extract_worker.set_url(url)
        self._extract_worker.start()

    def _on_extraction_done(self, playlist_info: dict):
        try:
            playlist = av_play.Playlist(
                title=playlist_info.get("title") or "Extracted Playlist"
            )
            for entry in playlist_info.get("entries", []):
                playlist.add_entry(
                    av_play.PlaylistEntry(
                        location=entry["location"],
                        title=entry.get("title"),
                    )
                )
            self.load_playlist(playlist, auto_play=False, start_index=0)
            self._play_playlist_track()
            self.signals.extraction_complete.emit(playlist)
        except Exception as e:
            logger.error(f"Failed to build playlist from extraction: {e}")
            self.signals.extraction_failed.emit(str(e))
        finally:
            self._drain_extraction()

    def _on_extraction_error(self, error_msg: str):
        logger.error(f"URL extraction failed: {error_msg}")
        self.signals.extraction_failed.emit(error_msg)
        self._drain_extraction()

    def _drain_extraction(self):
        pending = self._pending_url
        self._pending_url = None
        if pending:
            self.signals.extraction_started.emit()
            self._start_extraction(pending)

    def get_webpage_url(self, index: int) -> Optional[str]:
        if 0 <= index < len(self._webpage_urls):
            return self._webpage_urls[index]
        return None

    def get_streaming_url(self, index: int) -> Optional[str]:
        with self._resolve_lock:
            return self._resolved.get(index)

    def is_loaded(self, index: int) -> bool:
        with self._resolve_lock:
            return index in self._resolved

    def get_loaded_indices(self) -> List[int]:
        with self._resolve_lock:
            return sorted(self._resolved.keys())

    def refresh(self, index: int) -> bool:
        with self._resolve_lock:
            self._resolved.pop(index, None)
            self._resolving.discard(index)
        return self._ensure_resolved_blocking(index)

    def refresh_all(self):
        with self._resolve_lock:
            indices = list(self._resolved.keys())
        for idx in indices:
            self.refresh(idx)

    def set_playlist_shuffle_mode(self, mode: av_play.AVPlaylistShuffleMode):
        av_play.VLCVideoPlayer.set_playlist_shuffle_mode(self, mode)
        if self._current_playlist is not None and len(self._current_playlist) > 0:
            self._schedule_preload_ahead(self._current_playlist_index)

    def _play_playlist_track(self):
        if self._current_playlist is None:
            return

        idx = self._current_playlist_index
        if 0 <= idx < len(self._current_playlist):
            if self._ensure_resolved_blocking(idx):
                with self._resolve_lock:
                    streaming = self._resolved.get(idx)
                if streaming:
                    self._current_playlist.entries[idx].location = streaming

        av_play.VLCVideoPlayer._play_playlist_track(self)
        self._schedule_preload_ahead(self._current_playlist_index)

    def _ensure_resolved_blocking(self, index: int) -> bool:
        with self._resolve_lock:
            if index in self._resolved:
                return True

        webpage = self._webpage_urls[index] if 0 <= index < len(self._webpage_urls) else None
        if not webpage:
            return False

        try:
            if av_play.is_path(webpage):
                resolved = webpage
            elif is_url_supported(webpage):
                try:
                    resolved = resolve_webpage_url(webpage)
                except Exception as e:
                    logger.warning(f"Extraction failed for supported URL, passing directly: {e}")
                    resolved = webpage
            else:
                resolved = webpage
            with self._resolve_lock:
                self._resolved[index] = resolved
                self._resolving.discard(index)
            return True
        except Exception as e:
            logger.error(f"Resolution failed for index {index}: {e}")
            with self._resolve_lock:
                self._resolving.discard(index)
            return False

    def _schedule_preload_ahead(self, current_index: int):
        if self._current_playlist is None:
            return
        total = len(self._current_playlist)
        if total == 0:
            return

        order = self._resolve_playback_order(current_index)
        for idx in order[1:self._preload_window + 1]:
            with self._resolve_lock:
                if idx in self._resolved or idx in self._resolving:
                    continue
                self._resolving.add(idx)
            try:
                self._preload_queue.put_nowait(idx)
            except Exception:
                with self._resolve_lock:
                    self._resolving.discard(idx)
                break

    def _resolve_playback_order(self, current_index: int) -> List[int]:
        total = len(self._current_playlist) if self._current_playlist else 0
        if total == 0:
            return []

        shuffle_mode = self.get_playlist_shuffle_mode()
        repeat_mode = self.get_playlist_repeat_mode()

        if shuffle_mode == av_play.AVPlaylistShuffleMode.SHUFFLE:
            shuffle_order = list(getattr(self, "_shuffle_order", []))
            if not shuffle_order:
                shuffle_order = list(range(total))
            if current_index not in shuffle_order:
                return shuffle_order
            pos = shuffle_order.index(current_index)
            return shuffle_order[pos:] + shuffle_order[:pos]

        if repeat_mode == av_play.AVPlaylistRepeatMode.REPEAT_ALL:
            return list(range(current_index, total)) + list(range(0, current_index))
        return list(range(current_index, total))

    def _preload_worker(self):
        while not self._preload_stop_event.is_set():
            try:
                index = self._preload_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if index < 0 or self._preload_stop_event.is_set():
                break
            try:
                self._ensure_resolved_blocking(index)
            except Exception as e:
                logger.warning(f"Preload failed for index {index}: {e}")

    def _reset_resolution_state(self, total_entries: int):
        with self._resolve_lock:
            self._webpage_urls = []
            self._resolved = {}
            self._resolving = set()
        while True:
            try:
                self._preload_queue.get_nowait()
            except queue.Empty:
                break

    def _fetch_webpage_playlist(self, url: str) -> dict:
        if not is_playlist(url) and not has_playlist_param(url):
            return {"title": "Extracted URL", "entries": [{"location": url}]}

        flat_entries = run_ytdlp_flat_playlist(url)
        entries = []
        title = "Extracted Playlist"
        for info in flat_entries:
            webpage = info.get("webpage_url") or info.get("original_url") or info.get("url")
            if not webpage:
                continue
            title = info.get("playlist_title") or info.get("playlist") or title
            entries.append({"location": webpage, "title": info.get("title")})
        if not entries:
            raise ValueError("No playable entries found in playlist")
        return {"title": title, "entries": entries}

from __future__ import annotations

import logging
import os
import queue
import threading
from typing import List, Optional, Set

import media_core.av_play as av_play
from media_core.av_play.mpv_audio_filter import MPVEqualizerFilter, MPVAudioFilter
from media_core.av_play.mpv_effects_catalog import MPV_EFFECTS, get_mpv_effect
from media_core.av_play.mpv_equalizer_presets import EQUALIZER_PRESETS
from PySide6.QtCore import QObject, Signal, QThread

from app_config import prefs

from ..util.url import (
    is_url_supported,
    resolve_webpage_url,
    run_ytdlp_flat_playlist,
    run_ytdlp,
    has_playlist_param,
    is_playlist,
)
from ..util.utilities import ensure_ytdlp_available


logger = logging.getLogger(__name__)

# Derived from the mpv_effects_catalog (the one source of truth for the
# "Add Effect" picker dialog too) and keyed by catalog id -- NOT the filter
# class's own AVFilter "handle" (its stable, untranslated display label,
# still used internally for af-chain ordering, see _rebuild_filter_chain).
# The Equalizer has its own dedicated accordion section/UI already, so
# it's intentionally excluded here.
AUDIO_FILTER_CLASSES = {
    effect.id: effect.filter_class for effect in MPV_EFFECTS if effect.id != "equalizer"
}


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


class LazyPlaylistPlayer(av_play.VideoPlayer):
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

        self._equalizer_filter: Optional[MPVEqualizerFilter] = None
        self._equalizer_filter_id: Optional[int] = None

        # Objects are kept around even while disabled so re-enabling an
        # effect restores whatever parameters were last set on it.
        # _added_effect_order tracks which catalog ids the user has
        # explicitly added (and their display order), independent of the
        # actual af-chain playback order _rebuild_filter_chain computes.
        # The whole chain (added effects, enabled state, param values) is
        # persisted to app_config.prefs -- see add_audio_filter et al.
        self._audio_filter_objects: dict[str, MPVAudioFilter] = {}
        self._audio_filter_ids: dict[str, int] = {}
        self._added_effect_order: List[str] = []

    def get_equalizer_presets(self) -> List[str]:
        return [name for name, _bands in EQUALIZER_PRESETS]

    def get_equalizer_bands(self) -> List[float]:
        return list(MPVEqualizerFilter.BAND_FREQUENCIES)

    def get_preset_amps(self, preset: int) -> List[float]:
        if 0 <= preset < len(EQUALIZER_PRESETS):
            return list(EQUALIZER_PRESETS[preset][1])
        return [0.0] * len(MPVEqualizerFilter.BAND_FREQUENCIES)

    def set_equalizer(self, band_amps: List[float], preamp: float = 0.0, preset: Optional[int] = None,
                       persist: bool = True) -> None:
        if preset is not None and 0 <= preset < len(EQUALIZER_PRESETS):
            band_amps = list(EQUALIZER_PRESETS[preset][1])

        instance = self.primary_instance
        if instance is not None:
            if self._equalizer_filter_id is not None:
                try:
                    instance.remove_filter(self._equalizer_filter_id)
                except Exception:
                    pass
            self._equalizer_filter = MPVEqualizerFilter(band_amps=band_amps, preamp=preamp)
            self._equalizer_filter_id = instance.apply_filter(self._equalizer_filter)

        if persist:
            prefs.prefs["equalizer_enabled"] = True
            prefs.prefs["equalizer_preamp"] = preamp
            prefs.prefs["equalizer_bands"] = list(band_amps)
            prefs.prefs["equalizer_preset"] = preset if preset is not None else -1
            prefs.save()

    def disable_equalizer(self, persist: bool = True) -> None:
        instance = self.primary_instance
        if instance is not None and self._equalizer_filter_id is not None:
            try:
                instance.remove_filter(self._equalizer_filter_id)
            except Exception:
                pass
        self._equalizer_filter_id = None
        self._equalizer_filter = None

        if persist:
            prefs.prefs["equalizer_enabled"] = False
            prefs.save()

    def get_audio_filter_names(self) -> List[str]:
        """Currently *added* effect ids, in add order -- not the full
        catalog (see media_core.av_play.mpv_effects_catalog.MPV_EFFECTS
        for that; the "Add Effect" picker browses the catalog directly)."""
        return list(self._added_effect_order)

    def _get_audio_filter_object(self, name: str) -> Optional[MPVAudioFilter]:
        if name not in self._audio_filter_objects:
            filter_cls = AUDIO_FILTER_CLASSES.get(name)
            if filter_cls is None:
                return None
            self._audio_filter_objects[name] = filter_cls()
        return self._audio_filter_objects[name]

    def get_audio_filter_param_spec(self, name: str):
        """Returns (params_by_mpv_name: dict[str, (type, (min, max, step, default))], current_values: dict) or None."""
        filter_obj = self._get_audio_filter_object(name)
        if filter_obj is None:
            return None
        return dict(filter_obj.info.get("mpv_param_map", {})), dict(filter_obj.get_parameters())

    def is_audio_filter_enabled(self, name: str) -> bool:
        return name in self._audio_filter_ids

    def add_audio_filter(self, effect_id: str, values: Optional[dict] = None,
                          enabled: bool = True, persist: bool = True) -> bool:
        """Add effect_id to the active chain (one instance per effect id --
        adding an already-added id just updates it instead of duplicating)."""
        filter_obj = self._get_audio_filter_object(effect_id)
        if filter_obj is None:
            return False

        for param_name, value in (values or {}).items():
            filter_obj.set_parameter(param_name, value)

        if effect_id not in self._added_effect_order:
            self._added_effect_order.append(effect_id)

        self.set_audio_filter_enabled(effect_id, enabled, persist=False)

        if persist:
            self._persist_audio_effects_chain()
        return True

    def remove_audio_filter(self, effect_id: str, persist: bool = True) -> None:
        if effect_id not in self._added_effect_order:
            return
        self.set_audio_filter_enabled(effect_id, False, persist=False)
        self._added_effect_order.remove(effect_id)
        self._audio_filter_objects.pop(effect_id, None)

        if persist:
            self._persist_audio_effects_chain()

    def clear_audio_filters(self, persist: bool = True) -> None:
        for effect_id in list(self._added_effect_order):
            self.remove_audio_filter(effect_id, persist=False)

        if persist:
            self._persist_audio_effects_chain()

    def set_audio_filter_enabled(self, name: str, enabled: bool, persist: bool = True) -> None:
        filter_obj = self._get_audio_filter_object(name)
        if filter_obj is None:
            return
        instance = self.primary_instance
        if enabled:
            if name not in self._audio_filter_ids and instance is not None:
                self._audio_filter_ids[name] = instance.apply_filter(filter_obj)
        else:
            filter_id = self._audio_filter_ids.pop(name, None)
            if filter_id is not None and instance is not None:
                try:
                    instance.remove_filter(filter_id)
                except Exception:
                    pass

        if persist:
            self._persist_audio_effects_chain()

    def set_audio_filter_parameter(self, name: str, param_name: str, value, persist: bool = True) -> None:
        filter_obj = self._audio_filter_objects.get(name)
        if filter_obj is None:
            return
        filter_id = self._audio_filter_ids.get(name)
        instance = self.primary_instance
        if filter_id is not None and instance is not None:
            instance.set_parameter(filter_id, param_name, value)
        else:
            filter_obj.set_parameter(param_name, value)

        if persist:
            self._persist_audio_effects_chain()

    def _persist_audio_effects_chain(self) -> None:
        chain = []
        for effect_id in self._added_effect_order:
            filter_obj = self._audio_filter_objects.get(effect_id)
            if filter_obj is None:
                continue
            chain.append({
                "id": effect_id,
                "enabled": self.is_audio_filter_enabled(effect_id),
                "values": dict(filter_obj.get_parameters()),
            })
        prefs.prefs["audio_effects_chain"] = chain
        prefs.save()

    def _apply_saved_audio_effects(self) -> None:
        for entry in prefs.prefs.get("audio_effects_chain") or []:
            effect_id = entry.get("id")
            if not effect_id or effect_id not in AUDIO_FILTER_CLASSES:
                continue
            self.add_audio_filter(
                effect_id,
                values=entry.get("values") or {},
                enabled=bool(entry.get("enabled", True)),
                persist=False,
            )

    def _apply_saved_equalizer(self) -> None:
        if not prefs.prefs.get("equalizer_enabled"):
            return
        bands = prefs.prefs.get("equalizer_bands") or []
        if not bands:
            return
        preset = prefs.prefs.get("equalizer_preset", -1)
        self.set_equalizer(
            bands,
            preamp=prefs.prefs.get("equalizer_preamp", 0.0),
            preset=preset if preset is not None and preset >= 0 else None,
            persist=False,
        )

    def init(self, *args, **kw):
        super().init(*args, **kw)
        self._preload_stop_event.clear()
        if self._preload_thread is None or not self._preload_thread.is_alive():
            self._preload_thread = threading.Thread(
                target=self._preload_worker, daemon=True, name="LazyPlaylistPreload"
            )
            self._preload_thread.start()
        self._apply_saved_equalizer()
        self._apply_saved_audio_effects()

    def release(self):
        # release() is reachable from GUI event handlers on the Qt main
        # thread (closeEvent, player re-init). Signal both workers to stop
        # but don't join/wait here -- up to 1s for the preload thread and up
        # to 2s for the (possibly network-bound) extraction thread would
        # freeze the whole event loop. _preload_thread is a daemon thread,
        # so leaving it to exit on its own is safe; _extract_worker may log
        # a benign "QThread destroyed while running" warning if it's still
        # finishing when GC'd, which is an acceptable tradeoff against
        # blocking the GUI thread.
        self._preload_stop_event.set()
        try:
            self._preload_queue.put_nowait(-1)
        except Exception:
            pass
        if self._extract_worker and self._extract_worker.isRunning():
            self._extract_worker.quit()
        super().release()

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

        super().load_playlist(
            playlist, auto_play=auto_play, start_index=target_index
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
            self.load_playlist(playlist, auto_play=True, start_index=0)
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
        super().set_playlist_shuffle_mode(mode)
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

        super()._play_playlist_track()
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
            try:
                info = run_ytdlp(url, as_playlist=False)
                if isinstance(info, list):
                    info = info[0]
                title = info.get("title") or info.get("webpage_url") or url
                return {"title": title, "entries": [{"location": url, "title": title}]}
            except Exception:
                return {"title": url, "entries": [{"location": url, "title": url}]}

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

import logging
import os
from typing import Optional

import av_play
from PySide6.QtCore import QThread, Signal

from app_config import prefs
from utilities.chapter_probe import get_chapters
from ..util.url import fetch_full_info, is_url_supported

logger = logging.getLogger(__name__)

_CHAPTER_CAPABLE_EXTENSIONS = {"mp4", "m4v", "mkv", "m4b"}


class _YtdlpInfoFetchThread(QThread):
    result_ready = Signal(str, dict)
    error_occurred = Signal(str, str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self):
        try:
            info = fetch_full_info(self._url)
            self.result_ready.emit(self._url, info)
        except Exception as e:
            self.error_occurred.emit(self._url, str(e))


def best_subtitle_format(formats: list) -> Optional[dict]:
    for fmt in formats:
        if fmt.get("ext") in ("vtt", "srt"):
            return fmt
    return formats[0] if formats else None


def best_subtitle_format_url(formats: list) -> Optional[str]:
    fmt = best_subtitle_format(formats)
    return fmt.get("url") if fmt else None


def _pick_ytdlp_subtitle_track(info: dict, preferred_lang: str):
    preferred_primary = preferred_lang.split("-")[0].lower()
    for source_key in ("subtitles", "automatic_captions"):
        tracks = info.get(source_key) or {}
        if not tracks:
            continue
        lang = None
        if preferred_lang in tracks:
            lang = preferred_lang
        else:
            for key in tracks:
                if key.split("-")[0].lower() == preferred_primary:
                    lang = key
                    break
        if not lang:
            lang = next(iter(tracks), None)
        if not lang:
            continue
        url = best_subtitle_format_url(tracks[lang])
        if url:
            return url, lang, tracks
    return None, None, None


class _YtdlpSubtitleFetchThread(QThread):
    finished_ok = Signal(str, bool)

    def __init__(self, subtitle_manager, source: str, subtitle_url: str, language: str, parent=None):
        super().__init__(parent)
        self._subtitle_manager = subtitle_manager
        self._source = source
        self._subtitle_url = subtitle_url
        self._language = language

    def run(self):
        ok = self._subtitle_manager.load_from_ytdlp_track(self._subtitle_url, self._language)
        self.finished_ok.emit(self._source, ok)


class TrackMetadataLoader:
    """Loads subtitles/chapters for the current track, including yt-dlp
    metadata/subtitle fetching over background threads. Extracted out of
    PlayerWidget's _load_subtitles_for_current_track and friends. widget is
    the owning PlayerWidget instance."""

    def __init__(self, widget):
        self._widget = widget
        self._current_ytdlp_source: Optional[str] = None
        self._ytdlp_subtitle_tracks = {}
        self._ytdlp_metadata_thread: Optional[_YtdlpInfoFetchThread] = None
        self._ytdlp_subtitle_thread: Optional[_YtdlpSubtitleFetchThread] = None

    def load_subtitles_for_current_track(self):
        widget = self._widget
        widget.subtitles_widget.clear_subtitles()
        widget._last_subtitle_text = None
        widget.filters_widget.reset_filters()

        source = widget.player_controls._source_url
        if source and is_url_supported(source):
            widget.chapters_widget.clear_chapters()
            self._fetch_ytdlp_metadata(source)
            return

        self._current_ytdlp_source = None
        self._ytdlp_subtitle_tracks = {}
        widget.subtitles_widget.set_available_languages([])
        instance = widget.player.primary_instance
        if instance and av_play.is_path(instance.file_path):
            if widget.subtitle_manager.load_for_video(instance.file_path):

                widget.subtitles_widget.load_all_subtitles(widget.subtitle_manager)
        self.load_chapters_for_current_track()

    def _fetch_ytdlp_metadata(self, source: str):
        self._current_ytdlp_source = source
        if self._ytdlp_metadata_thread and self._ytdlp_metadata_thread.isRunning():
            self._ytdlp_metadata_thread.quit()
            self._ytdlp_metadata_thread.wait(100)

        thread = _YtdlpInfoFetchThread(source, self._widget)
        thread.result_ready.connect(self._on_ytdlp_metadata_ready)
        thread.error_occurred.connect(self._on_ytdlp_metadata_error)
        self._ytdlp_metadata_thread = thread
        thread.start()

    def _on_ytdlp_metadata_ready(self, source: str, info: dict):
        if source != self._current_ytdlp_source:
            return  # stale result for a track we've since navigated away from

        widget = self._widget
        widget._info_dialogs.cache_youtube_info(source, info)

        chapters = [
            {
                "start": chapter.get("start_time", 0.0),
                "end": chapter.get("end_time", 0.0),
                "title": chapter.get("title", ""),
            }
            for chapter in info.get("chapters") or []
        ]
        if chapters:
            widget.chapters_widget.load_chapters(chapters)

        subtitle_url, lang, tracks = _pick_ytdlp_subtitle_track(info, prefs.prefs.get("subtitle-language", "en-US"))
        self._ytdlp_subtitle_tracks = tracks or {}
        widget.subtitles_widget.set_available_languages(list(self._ytdlp_subtitle_tracks.keys()), lang)
        if subtitle_url:
            self._fetch_ytdlp_subtitles(source, subtitle_url, lang)

    def on_subtitle_language_selected(self, language: str):
        if language not in self._ytdlp_subtitle_tracks:
            return
        url = best_subtitle_format_url(self._ytdlp_subtitle_tracks[language])
        if url and self._current_ytdlp_source:
            self._fetch_ytdlp_subtitles(self._current_ytdlp_source, url, language)

    def _fetch_ytdlp_subtitles(self, source: str, subtitle_url: str, language: str):
        if self._ytdlp_subtitle_thread and self._ytdlp_subtitle_thread.isRunning():
            self._ytdlp_subtitle_thread.quit()
            self._ytdlp_subtitle_thread.wait(100)

        thread = _YtdlpSubtitleFetchThread(self._widget.subtitle_manager, source, subtitle_url, language, self._widget)
        thread.finished_ok.connect(self._on_ytdlp_subtitles_ready)
        self._ytdlp_subtitle_thread = thread
        thread.start()

    def _on_ytdlp_subtitles_ready(self, source: str, ok: bool):
        if source != self._current_ytdlp_source:
            return  # stale result for a track we've since navigated away from
        if ok:
            self._widget.subtitles_widget.load_all_subtitles(self._widget.subtitle_manager)

    def _on_ytdlp_metadata_error(self, source: str, error_msg: str):
        if source != self._current_ytdlp_source:
            return
        logger.warning(f"yt-dlp metadata fetch failed for {source}: {error_msg}")

    def load_chapters_for_current_track(self):
        widget = self._widget
        widget.chapters_widget.clear_chapters()
        instance = widget.player.primary_instance
        if not instance or not av_play.is_path(instance.file_path):
            return

        ext = os.path.splitext(instance.file_path)[1].lower().lstrip(".")
        if ext not in _CHAPTER_CAPABLE_EXTENSIONS:
            return

        try:
            chapters = get_chapters(instance.file_path)
        except Exception:
            return

        if chapters:
            widget.chapters_widget.load_chapters(chapters)

    def on_chapter_activated(self, start_seconds: float):
        instance = self._widget.player.primary_instance
        if instance:
            try:
                instance.set_position(start_seconds)
            except av_play.AVError:
                pass

    def cleanup(self):
        if self._ytdlp_metadata_thread and self._ytdlp_metadata_thread.isRunning():
            self._ytdlp_metadata_thread.quit()
            self._ytdlp_metadata_thread.wait(2000)

        if self._ytdlp_subtitle_thread and self._ytdlp_subtitle_thread.isRunning():
            self._ytdlp_subtitle_thread.quit()
            self._ytdlp_subtitle_thread.wait(2000)

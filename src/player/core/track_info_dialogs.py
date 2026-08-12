from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox

from utilities import signal_manager
from utilities.announcement_categories import AnnouncementCategory
from utilities.chapter_probe import get_media_metadata
from utilities.functions import is_youtube_url, is_local_file
from ..util.url import is_url_supported
from ..util.utilities import ensure_ffprobe_available
from .track_metadata_loader import _YtdlpInfoFetchThread, best_subtitle_format


def _announce(text):
    signal_manager.announce(text, AnnouncementCategory.PLAYBACK)


class _SubtitleFileDownloadThread(QThread):
    finished_ok = Signal(str)  # save_path
    error_occurred = Signal(str)

    def __init__(self, url: str, save_path: str, parent=None):
        super().__init__(parent)
        self._url = url
        self._save_path = save_path

    def run(self):
        try:
            import httpx
            response = httpx.get(self._url, timeout=15.0)
            response.raise_for_status()
            with open(self._save_path, "wb") as f:
                f.write(response.content)
            self.finished_ok.emit(self._save_path)
        except Exception as e:
            self.error_occurred.emit(str(e))


class TrackInfoDialogs:
    """YouTube info/comments/media-metadata dialogs and subtitle-file
    download, extracted out of PlayerWidget. widget is the owning
    PlayerWidget instance."""

    def __init__(self, widget):
        self._widget = widget
        self._youtube_info_cache = {}
        self._subtitle_download_thread: 'QThread | None' = None
        self._metadata_dialog_thread: 'QThread | None' = None

    def cache_youtube_info(self, url: str, info: dict):
        self._youtube_info_cache[url] = info

    def show_youtube_info_dialog(self):
        widget = self._widget
        current_file = widget.player_controls._source_url or widget.player_controls._current_file
        if not current_file:
            return

        if not is_youtube_url(current_file):
            return

        from gui.dialogs.youtube_info_dialog import YouTubeInfoDialog

        cached = self._youtube_info_cache.get(current_file)
        dialog = YouTubeInfoDialog(current_file, parent=widget.window(), cached_info=cached)
        dialog.exec()

        if dialog.cached_info and current_file not in self._youtube_info_cache:
            self.cache_youtube_info(current_file, dialog.cached_info)

    def download_subtitle_file(self):
        widget = self._widget
        subtitle_tracks = widget._track_loader._ytdlp_subtitle_tracks
        if not subtitle_tracks:
            QMessageBox.information(
                widget, _("No Subtitles"), _("No subtitle track is available for this source.")
            )
            return

        current_lang = widget.subtitles_widget.language_combo.currentText()
        if not current_lang or current_lang not in subtitle_tracks:
            current_lang = next(iter(subtitle_tracks), None)
        if not current_lang:
            return

        fmt = best_subtitle_format(subtitle_tracks[current_lang])
        if not fmt or not fmt.get("url"):
            return

        extension = fmt.get("ext") or "srt"
        default_name = f"subtitles_{current_lang}.{extension}"
        save_path, _filter = QFileDialog.getSaveFileName(widget, _("Save Subtitle File"), default_name)
        if not save_path:
            return

        if self._subtitle_download_thread and self._subtitle_download_thread.isRunning():
            self._subtitle_download_thread.quit()
            self._subtitle_download_thread.wait(100)

        thread = _SubtitleFileDownloadThread(fmt["url"], save_path, widget)
        thread.finished_ok.connect(self._on_subtitle_download_finished)
        thread.error_occurred.connect(self._on_subtitle_download_error)
        self._subtitle_download_thread = thread
        _announce(_("Downloading subtitle..."))
        thread.start()

    def _on_subtitle_download_finished(self, save_path: str):
        _announce(_("Subtitle saved to {path}").format(path=save_path))

    def _on_subtitle_download_error(self, error_msg: str):
        QMessageBox.warning(self._widget, _("Download Failed"), error_msg)

    def view_youtube_comments(self):
        widget = self._widget
        current_file = widget.player_controls._source_url or widget.player_controls._current_file
        if not current_file or not is_youtube_url(current_file):
            return

        from gui.dialogs.youtube_comments_dialog import YouTubeCommentsDialog
        dialog = YouTubeCommentsDialog(current_file, parent=widget.window())
        dialog.exec()

    def view_media_metadata(self):
        widget = self._widget
        current_file = widget.player_controls._current_file
        source = widget.player_controls._source_url or current_file
        if not source:
            return

        from gui.dialogs.media_metadata_dialog import MediaMetadataDialog

        if current_file and is_local_file(current_file):
            if not ensure_ffprobe_available(widget):
                return
            try:
                metadata = get_media_metadata(current_file)
            except Exception as e:
                QMessageBox.warning(widget, _("Metadata Error"), str(e))
                return
            dialog = MediaMetadataDialog.from_local_metadata(current_file, metadata, parent=widget.window())
            dialog.exec()
        elif is_url_supported(source):
            info = self._youtube_info_cache.get(source)
            if info:
                dialog = MediaMetadataDialog.from_url_info(source, info, parent=widget.window())
                dialog.exec()
            else:
                self._fetch_metadata_for_dialog(source)

    def _fetch_metadata_for_dialog(self, source: str):
        if self._metadata_dialog_thread and self._metadata_dialog_thread.isRunning():
            self._metadata_dialog_thread.quit()
            self._metadata_dialog_thread.wait(100)

        thread = _YtdlpInfoFetchThread(source, self._widget)
        thread.result_ready.connect(self._on_metadata_dialog_info_ready)
        thread.error_occurred.connect(self._on_metadata_dialog_info_error)
        self._metadata_dialog_thread = thread
        _announce(_("Fetching media metadata..."))
        thread.start()

    def _on_metadata_dialog_info_ready(self, source: str, info: dict):
        self.cache_youtube_info(source, info)
        from gui.dialogs.media_metadata_dialog import MediaMetadataDialog
        dialog = MediaMetadataDialog.from_url_info(source, info, parent=self._widget.window())
        dialog.exec()

    def _on_metadata_dialog_info_error(self, source: str, error_msg: str):
        QMessageBox.warning(self._widget, _("Metadata Error"), error_msg)

    def cleanup(self):
        self._youtube_info_cache.clear()

        if self._subtitle_download_thread and self._subtitle_download_thread.isRunning():
            self._subtitle_download_thread.quit()
            self._subtitle_download_thread.wait(2000)

        if self._metadata_dialog_thread and self._metadata_dialog_thread.isRunning():
            self._metadata_dialog_thread.quit()
            self._metadata_dialog_thread.wait(2000)

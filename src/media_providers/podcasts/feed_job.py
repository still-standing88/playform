import logging

from PySide6.QtCore import QThread, Signal

from media_core.podcasts.feed_manager import FeedManager
from media_core.podcasts.feed_refresh_runner import FeedRefreshRunner

__all__ = ["FeedJob"]


class FeedJob(QThread):
    """Qt wrapper driving media_core.podcasts off the GUI thread -- same
    shape as tools/ffmpeg/batch_converter/job.py wrapping ConversionRunner.
    Every feedparser.parse() call (the actual blocking network I/O) happens
    on this thread's run(), never on the GUI thread.

    mode is one of "refresh_one", "refresh_all", "validate_and_add",
    "update_url". urls is a 1-tuple for every mode except "refresh_all"
    (where None means "all registered feeds") and "update_url" (a 2-tuple
    of (old_url, new_url)).
    """

    feed_started = Signal(str)
    feed_updated = Signal(str, object)
    feed_error = Signal(str, str)
    progress = Signal(int, int)
    finished_all = Signal(bool)

    def __init__(self, feed_manager: FeedManager, mode: str, urls=None):
        super().__init__()
        self._feed_manager = feed_manager
        self._mode = mode
        self._urls = urls
        self._runner = None

    def run(self):
        try:
            handler = getattr(self, f"_run_{self._mode}", None)
            if handler is None:
                logging.error("FeedJob: unknown mode %r", self._mode)
                self.finished_all.emit(False)
                return
            handler()
        except Exception:
            logging.exception("FeedJob: unhandled error in mode %r", self._mode)
            self.finished_all.emit(False)

    def _run_refresh_all(self):
        self._runner = FeedRefreshRunner(
            self._feed_manager, urls=self._urls, force=True,
            on_feed_started=self.feed_started.emit,
            on_feed_updated=self.feed_updated.emit,
            on_feed_error=self.feed_error.emit,
            on_progress=self.progress.emit,
        )
        completed = self._runner.run()
        self.finished_all.emit(completed)

    def _run_refresh_one(self):
        url = self._urls[0]
        self.feed_started.emit(url)
        try:
            data = self._feed_manager.refresh_feed(url, force=True)
            self.feed_updated.emit(url, data)
            self.finished_all.emit(True)
        except Exception as exc:
            logging.exception("FeedJob: refresh_one failed for %r", url)
            self.feed_error.emit(url, str(exc))
            self.finished_all.emit(False)

    def _validate_or_error(self, url):
        """Runs a force refresh and interprets feedparser's bozo flag the
        same way FeedWidget.validate_feed() used to. Returns (parsed_data,
        error_message_or_None)."""
        parsed = self._feed_manager.refresh_feed(url, force=True)
        if parsed and not parsed.get('bozo', 0):
            return parsed, None
        if parsed and parsed.get('bozo', 0):
            exception = parsed.get('bozo_exception')
            return None, str(exception) if exception else _("Invalid feed format")
        return None, _("Failed to parse feed")

    def _run_validate_and_add(self):
        url = self._urls[0]
        self.feed_started.emit(url)
        try:
            data, error = self._validate_or_error(url)
        except Exception as exc:
            logging.exception("FeedJob: validate_and_add failed for %r", url)
            data, error = None, str(exc)
        if error is not None:
            self._feed_manager.remove_feed(url)
            self.feed_error.emit(url, error)
            self.finished_all.emit(False)
            return
        self._feed_manager.add_feed(url)
        self.feed_updated.emit(url, data)
        self.finished_all.emit(True)

    def _run_update_url(self):
        old_url, new_url = self._urls
        self.feed_started.emit(new_url)
        try:
            data, error = self._validate_or_error(new_url)
        except Exception as exc:
            logging.exception("FeedJob: update_url failed for %r", new_url)
            data, error = None, str(exc)
        if error is not None:
            self._feed_manager.remove_feed(new_url)
            self.feed_error.emit(new_url, error)
            self.finished_all.emit(False)
            return
        self._feed_manager.update_feed_url(old_url, new_url)
        self.feed_updated.emit(new_url, data)
        self.finished_all.emit(True)

    def stop(self):
        if self._runner:
            self._runner.stop()

    def pause(self):
        if self._runner:
            self._runner.pause()

    def resume(self):
        if self._runner:
            self._runner.resume()

    def is_paused(self) -> bool:
        return bool(self._runner and self._runner.is_paused())

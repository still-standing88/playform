from __future__ import annotations

import logging
from typing import Callable, Iterable, Optional

from media_core.m4b_tools.runner import M4bToolsRunner
from media_core.podcasts.feed_manager import FeedManager


class FeedRefreshRunner(M4bToolsRunner):
    """Drives FeedManager.refresh_feed() over one or more feed URLs off the
    GUI thread, with pause/resume/stop between feeds (mirrors
    media_core.m4b_tools' runner shape, see M4bToolsRunner). All reporting
    goes through plain callbacks -- a Qt wrapper (feed_job.FeedJob) re-emits
    each one as a signal, same pattern as
    tools/ffmpeg/batch_converter/job.py wrapping ConversionRunner.
    """

    def __init__(
        self,
        feed_manager: FeedManager,
        urls: Optional[Iterable[str]] = None,
        force: bool = False,
        on_feed_started: Optional[Callable[[str], None]] = None,
        on_feed_updated: Optional[Callable[[str, object], None]] = None,
        on_feed_error: Optional[Callable[[str, str], None]] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ):
        super().__init__()
        self._feed_manager = feed_manager
        self._urls = list(urls) if urls is not None else None
        self._force = force
        self._on_feed_started = on_feed_started or (lambda url: None)
        self._on_feed_updated = on_feed_updated or (lambda url, data: None)
        self._on_feed_error = on_feed_error or (lambda url, message: None)
        self._on_progress = on_progress or (lambda done, total: None)

    def run(self) -> bool:
        urls = self._urls if self._urls is not None else self._feed_manager.get_feed_list()
        total = len(urls)
        for index, url in enumerate(urls):
            if not self._checkpoint():
                return False
            self._on_feed_started(url)
            try:
                data = self._feed_manager.refresh_feed(url, force=self._force)
                self._on_feed_updated(url, data)
            except Exception as exc:
                logging.exception("FeedRefreshRunner: failed to refresh %r", url)
                self._on_feed_error(url, str(exc))
            self._on_progress(index + 1, total)
        return self._is_running

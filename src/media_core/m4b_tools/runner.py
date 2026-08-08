from __future__ import annotations

import threading


class M4bToolsRunner:
    """Shared pause/resume/stop plumbing for m4b_tools' framework-agnostic job runners.

    Mirrors `media_core.ffmpeg.conversion_job.ConversionRunner`'s threading model so a Qt
    wrapper can drive any m4b_tools runner the same way it drives batch conversion jobs:
    call `run()` on a worker thread, and `pause()`/`resume()`/`stop()` from the UI thread.
    """

    def __init__(self):
        self._is_running = True
        self._resume_event = threading.Event()
        self._resume_event.set()

    def stop(self):
        self._is_running = False
        self._resume_event.set()

    def pause(self):
        self._resume_event.clear()

    def resume(self):
        self._resume_event.set()

    def is_paused(self) -> bool:
        return not self._resume_event.is_set()

    def _checkpoint(self) -> bool:
        """Block while paused. Returns False once `stop()` has been called."""
        self._resume_event.wait()
        return self._is_running

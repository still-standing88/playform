"""Run a blocking media_core.av_capture call (device enumeration, camera
format probing, device-presence checks - anything that spins up a real
ffmpeg/platform subprocess) off the GUI thread and deliver the result back
via a signal.

Every direct CaptureCapabilities call used to happen inline in whatever
widget needed it (TypeDevicePage.__init__, its Refresh button, the planned
disconnected-device check) - each one is a few hundred ms to a couple of
seconds of real subprocess time, which is a UI freeze on a click. This is
the one place that pattern is handled, so nothing in dialogs/ or views/
touches CaptureCapabilities synchronously.
"""
from __future__ import annotations

import threading
from typing import Callable

from PySide6.QtCore import QObject, Signal


class AsyncProbe(QObject):
    """One-shot per call - build a fresh instance (or call run() again) for
    each probe rather than trying to reuse/cancel an in-flight one; callers
    that can have overlapping requests (device-status checks retriggered by
    fast session switching) guard with their own request-token check on the
    result instead."""

    result_ready = Signal(object)
    failed = Signal(str)

    def run(self, fn: Callable[[], object]) -> None:
        def _worker():
            try:
                value = fn()
            except Exception as exc:  # subprocess/platform errors of any kind
                self.failed.emit(str(exc))
                return
            self.result_ready.emit(value)

        threading.Thread(target=_worker, daemon=True, name="av-capture-probe").start()

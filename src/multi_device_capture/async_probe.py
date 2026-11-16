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

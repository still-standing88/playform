"""Non-intrusive "is this saved source's device still here" check.

Runs on-demand (session selected, or an explicit Refresh) rather than on a
poll timer - one CaptureCapabilities.list_devices() call per distinct
MediaKind actually used by the sources being checked (not one call per
source), off the GUI thread via AsyncProbe. Overlapping checks (fast
session switching) are resolved by a monotonic token - only the latest
request's result is ever applied.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from media_core.av_capture.capabilities import CaptureCapabilities

from .async_probe import AsyncProbe
from .models import CaptureSource


class DeviceStatusChecker(QObject):
    checked = Signal(dict)   # {source_id: bool} - True if the source's device is currently present
    failed = Signal(str)

    def __init__(self, capabilities: CaptureCapabilities, parent=None):
        super().__init__(parent)
        self.capabilities = capabilities
        self._probe = AsyncProbe(self)
        self._probe.result_ready.connect(self._on_result)
        self._probe.failed.connect(self.failed)
        self._token = 0
        self._pending: dict[int, list[CaptureSource]] = {}

    def check(self, sources: list[CaptureSource]) -> None:
        self._token += 1
        token = self._token
        self._pending[token] = list(sources)
        kinds = {s.media_type for s in sources}
        capabilities = self.capabilities

        def _work(_kinds=kinds, _token=token):
            present_ids_by_kind = {}
            for kind in _kinds:
                present_ids_by_kind[kind] = {d.id for d in capabilities.list_devices(kind)}
            return _token, present_ids_by_kind

        self._probe.run(_work)

    def _on_result(self, result) -> None:
        token, present_ids_by_kind = result
        sources = self._pending.pop(token, None)
        if sources is None or token != self._token:
            return  # superseded by a newer check
        presence = {
            source.id: source.device_id in present_ids_by_kind.get(source.media_type, set())
            for source in sources
        }
        self.checked.emit(presence)

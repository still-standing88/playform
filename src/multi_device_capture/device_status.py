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

    def check(self, sources: list[CaptureSource]) -> None:
        self._token += 1
        token = self._token
        capabilities = self.capabilities

        def _work():
            devices = capabilities.inventory()
            return token, {
                source.id: capabilities.resolve_device(
                    devices.get(source.media_type, []),
                    source.device_id, source.device_name or source.settings.get("screen_name", ""),
                ) is not None
                for source in sources
            }

        self._probe.run(_work)

    def _on_result(self, result) -> None:
        token, presence = result
        if token == self._token:
            self.checked.emit(presence)

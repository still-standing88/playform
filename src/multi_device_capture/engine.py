import concurrent.futures
import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from media_core.av_capture.capabilities import CaptureCapabilities
from media_core.av_capture.session_runner import CaptureSessionRunner

from .models import CaptureSource, Session
from .settings import MultiDeviceCaptureSettings

logger = logging.getLogger(__name__)


class CaptureEngine(QObject):
    source_started = Signal(str, str)
    source_error = Signal(str, str)
    source_stopped = Signal(str, str)
    duration_changed = Signal(str, float)
    state_changed = Signal(str)

    def __init__(self, capabilities: CaptureCapabilities, settings: MultiDeviceCaptureSettings, parent=None):
        super().__init__(parent)
        self.capabilities = capabilities
        self.settings = settings
        self._runner = None
        self._active = False
        self._paused = False
        self._shutting_down = False
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="av-capture-ctl")
        self.state_changed.connect(self._maybe_notify_finished)

    def is_active(self) -> bool:
        return self._active

    def is_paused(self) -> bool:
        return self._paused

    def shutdown(self) -> None:
        self._shutting_down = True
        if self._active:
            self.stop_and_wait()
        self._executor.shutdown(wait=False)

    def start(self, session: Session, sources: list[CaptureSource]) -> None:
        if not self._active:
            self._active = True
            self._executor.submit(self._start_sync, session, sources)

    def _start_sync(self, session: Session, sources: list[CaptureSource]):
        runner = CaptureSessionRunner(
            session, sources, self.capabilities,
            on_source_started=self.source_started.emit,
            on_source_error=self.source_error.emit,
            on_source_stopped=self.source_stopped.emit,
            on_source_progress=self.duration_changed.emit,
            on_state_changed=self._on_runner_state_changed,
            on_source_exit=self._source_exited,
        )
        self._runner = runner
        try:
            if runner.start():
                self._on_runner_state_changed("recording")
                return
        except Exception as exc:
            logger.exception("Capture start failed")
            self.source_error.emit("", str(exc))
            runner.stop()
        self._runner = None
        self._active = False
        self.state_changed.emit("idle")

    def _source_exited(self, runner):
        if not self._shutting_down:
            self._executor.submit(self._finish_if_done, runner)

    def _finish_if_done(self, runner):
        if self._runner is runner and runner.all_finished():
            self._stop_sync()

    def pause(self) -> None:
        self._executor.submit(self._change_pause, True)

    def resume(self) -> None:
        self._executor.submit(self._change_pause, False)

    def _change_pause(self, paused):
        if self._runner is None or self._paused == paused:
            return
        if paused:
            self._runner.pause()
        else:
            self._runner.resume()

    def stop(self) -> None:
        self._executor.submit(self._stop_sync)

    def stop_and_wait(self) -> None:
        self._executor.submit(self._stop_sync).result()

    def _stop_sync(self) -> None:
        runner = self._runner
        if runner is None:
            return
        try:
            runner.stop()
        except Exception as exc:
            logger.exception("Capture stop failed")
            self.source_error.emit("", str(exc))
        finally:
            self._runner = None
            self._active = False
            self._paused = False
            self.state_changed.emit("stopped")

    def _on_runner_state_changed(self, state: str) -> None:
        self._paused = state == "paused"
        self.state_changed.emit(state)

    def _maybe_notify_finished(self, state: str) -> None:
        if state != "stopped" or not self.settings.get("notify_on_finish", True):
            return
        tray_icon = getattr(QApplication.instance(), "_tray_icon", None)
        if tray_icon is not None and hasattr(tray_icon, "showMessage"):
            tray_icon.showMessage(
                _("Capture Finished"), _("The multi-device capture has finished."),
                QSystemTrayIcon.MessageIcon.Information, 5000,
            )

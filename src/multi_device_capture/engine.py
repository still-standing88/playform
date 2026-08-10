"""Qt-facing wrapper around media_core.av_capture.session_runner
.CaptureSessionRunner - the actual ffmpeg process management, device
resolution and pause/resume-via-segment-concat logic all live there and
know nothing about Qt (same split as
tools.ffmpeg.batch_converter.job.ConvertJob wrapping
media_core.ffmpeg.conversion_job.ConversionRunner).

Unlike the previous QCamera/QScreenCapture/QWindowCapture/QMediaRecorder
engine, none of this needs to run on the GUI thread - it is one `ffmpeg`
subprocess per source, not a live Qt Multimedia object - so start/pause/
resume/stop (pause/stop in particular: each blocks for up to a few seconds
per source while ffmpeg finalizes/concats) run on a single background
worker thread via a 1-worker ThreadPoolExecutor, keeping the UI responsive.
CaptureSessionRunner's own callbacks fire from that same worker thread (or
one of the per-source ffmpeg threads it owns); Qt's signal/slot system
queues the emit()s below onto the GUI thread automatically since this
QObject's thread affinity is the GUI thread, regardless of which thread
calls .emit().
"""
from __future__ import annotations

import concurrent.futures

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from media_core.av_capture.capabilities import CaptureCapabilities
from media_core.av_capture.session_runner import CaptureSessionRunner
from tools.ffmpeg_handler import FFmpegHandler

from .models import CaptureSource, Session
from .settings import MultiDeviceCaptureSettings


class CaptureEngine(QObject):
    source_started = Signal(str, str)     # source_id, output_path
    source_error = Signal(str, str)       # source_id, message ("" source_id => session-level error)
    source_stopped = Signal(str, str)     # source_id, final_output_path
    duration_changed = Signal(str, float)  # source_id, elapsed seconds
    state_changed = Signal(str)           # "idle" | "recording" | "paused" | "stopped"

    def __init__(
        self, capabilities: CaptureCapabilities | None = None,
        settings: MultiDeviceCaptureSettings | None = None, parent=None,
    ):
        super().__init__(parent)
        ffmpeg_path, _ffprobe_path = FFmpegHandler.get_ffmpeg_binary()
        self.capabilities = capabilities or CaptureCapabilities(ffmpeg_executable=ffmpeg_path)
        self.settings = settings
        self._ffmpeg_executable = ffmpeg_path
        self._runner: CaptureSessionRunner | None = None
        self._active = False
        self._paused = False
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="av-capture-ctl")
        # Notify-on-finish touches QApplication/QSystemTrayIcon, so it must
        # run on the GUI thread - connect to our own (auto-queued across
        # threads) signal rather than calling it from
        # _on_runner_state_changed, which session_runner invokes directly
        # from the executor thread.
        self.state_changed.connect(self._maybe_notify_finished)

    def is_active(self) -> bool:
        return self._active

    def is_paused(self) -> bool:
        return self._paused

    def shutdown(self) -> None:
        """Called on real app shutdown (see MainWindow.closeEvent) - stops
        any in-progress capture and releases the worker thread."""
        if self._active:
            self.stop_and_wait()
        self._executor.shutdown(wait=False)

    # -- transport -----------------------------------------------------
    #
    # start()/stop() block briefly (start: up to ~0.6s per source to catch a
    # fast-failing device; stop: up to a few seconds per source to gracefully
    # terminate + concat) - callers that need a synchronous result (a
    # "capture still active, are you sure" shutdown gate) use the *_and_wait
    # variants; everything else fires the async version and reacts to
    # state_changed/source_* signals.

    def start(self, session: Session, sources: list[CaptureSource]) -> None:
        if self._active:
            return
        self._executor.submit(self._start_sync, session, sources)

    def start_and_wait(self, session: Session, sources: list[CaptureSource]) -> bool:
        if self._active:
            return False
        return self._executor.submit(self._start_sync, session, sources).result()

    def _start_sync(self, session: Session, sources: list[CaptureSource]) -> bool:
        self.capabilities.refresh()
        keep_segments = bool(self.settings.get("keep_segments_after_pause", False)) if self.settings else False
        runner = CaptureSessionRunner(
            session, sources, capabilities=self.capabilities, ffmpeg_executable=self._ffmpeg_executable,
            keep_segments=keep_segments,
            on_source_started=self.source_started.emit,
            on_source_error=self.source_error.emit,
            on_source_stopped=self.source_stopped.emit,
            on_source_progress=self.duration_changed.emit,
            on_state_changed=self._on_runner_state_changed,
        )
        ok = runner.start()
        if ok:
            # runner already fired its own on_state_changed("recording")
            # callback (-> self._on_runner_state_changed) during start().
            self._runner = runner
            self._active = True
            self._paused = False
        else:
            # Nothing started - session_runner.start() already reported why
            # through per-source source_error signals; state_changed still
            # fires so the UI can re-enable Start instead of staying stuck
            # showing "starting...".
            self.state_changed.emit("idle")
        return ok

    def pause(self) -> None:
        if not self._active or self._paused or self._runner is None:
            return
        self._executor.submit(self._runner.pause)

    def resume(self) -> None:
        if not self._active or not self._paused or self._runner is None:
            return
        self._executor.submit(self._runner.resume)

    def stop(self) -> None:
        if not self._active or self._runner is None:
            return
        self._executor.submit(self._stop_sync)

    def stop_and_wait(self) -> None:
        if not self._active or self._runner is None:
            return
        self._executor.submit(self._stop_sync).result()

    def _stop_sync(self) -> None:
        runner = self._runner
        if runner is None:
            return
        runner.stop()
        self._runner = None
        self._active = False
        self._paused = False

    def _on_runner_state_changed(self, state: str) -> None:
        # Called directly by session_runner from the executor thread (not a
        # Qt slot) - only touch the emit() here, which is the thread-safe
        # boundary; anything GUI-only (notify-on-finish) hangs off the
        # state_changed signal instead, see _maybe_notify_finished below.
        if state == "paused":
            self._paused = True
        elif state == "recording":
            self._paused = False
        self.state_changed.emit(state)

    def _maybe_notify_finished(self, state: str) -> None:
        if state != "stopped":
            return
        if self.settings is None or not self.settings.get("notify_on_finish", True):
            return
        # Same tray-notification path tools.ffmpeg.batch_converter uses -
        # the app-wide QSystemTrayIcon registered at startup by system_tray.py.
        tray_icon = getattr(QApplication.instance(), "_tray_icon", None)
        if tray_icon is not None and hasattr(tray_icon, "showMessage"):
            tray_icon.showMessage(
                _("Capture Finished"), _("The multi-device capture has finished."),
                QSystemTrayIcon.MessageIcon.Information, 5000,
            )

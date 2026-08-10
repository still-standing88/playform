"""Framework-agnostic multi-source capture engine.

Same shape as media_core.ffmpeg.conversion_job.ConversionRunner and
media_core.m4b_tools.audiobook.Audiobook: reports through plain callbacks,
imports nothing from Qt/app_config, and is meant to be driven from a worker
thread by a tools/ wrapper (see tools.ffmpeg.batch_converter.job.ConvertJob
for the pattern this follows).

One CaptureSourceConfig == one ffmpeg process recording continuously, same
"N sources == N independent captures started/paused/stopped together" model
the previous QtMultimedia engine used - just with a real `ffmpeg` subprocess
per source instead of a QMediaRecorder.

Pause/resume: ffmpeg has no live pause primitive (nothing like a SIGSTOP
that freezes encoding without the input device's own buffer overrunning),
so pause here means gracefully stopping the current segment's ffmpeg
process (FFmpeg.terminate() -> SIGTERM/CTRL_BREAK, the same signal `q`/
Ctrl+C sends on a real ffmpeg CLI session, which lets it finalize the
container) and resume means starting a new ffmpeg process against the same
device for a new segment file. On stop, segments from the same source are
losslessly joined with ffmpeg's own concat demuxer (`-f concat -safe 0`),
the same mechanism media_core.m4b_tools.audiobook.Audiobook uses to join
chapter files - see ffmpeg-formats manual, Demuxers 3.5 "concat".
"""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from media_core.av_capture.capabilities import CaptureCapabilities
from media_core.av_capture.command_builder import build_source_command, sanitize_filename
from media_core.av_capture.models import CaptureSessionConfig, CaptureSourceConfig
from media_core.ffmpeg import FFmpegError

_JOIN_TIMEOUT_SECONDS = 5.0


@dataclass
class _SourceRuntime:
    source: CaptureSourceConfig
    base_name: str
    final_path: str
    segments: list = field(default_factory=list)
    current_ffmpeg: Optional[object] = None
    current_thread: Optional[threading.Thread] = None
    prior_seconds: float = 0.0
    last_reported_seconds: float = 0.0
    running: bool = False
    failed: bool = False


class CaptureSessionRunner:
    def __init__(
        self,
        session: CaptureSessionConfig,
        sources: list[CaptureSourceConfig],
        capabilities: Optional[CaptureCapabilities] = None,
        ffmpeg_executable: str = "ffmpeg",
        on_source_started: Optional[Callable[[str, str], None]] = None,
        on_source_error: Optional[Callable[[str, str], None]] = None,
        on_source_stopped: Optional[Callable[[str, str], None]] = None,
        on_source_progress: Optional[Callable[[str, float], None]] = None,
        on_state_changed: Optional[Callable[[str], None]] = None,
    ):
        self.session = session
        self.sources = sources
        self.capabilities = capabilities or CaptureCapabilities(ffmpeg_executable)
        self.ffmpeg_executable = ffmpeg_executable

        self._on_source_started = on_source_started or (lambda *a: None)
        self._on_source_error = on_source_error or (lambda *a: None)
        self._on_source_stopped = on_source_stopped or (lambda *a: None)
        self._on_source_progress = on_source_progress or (lambda *a: None)
        self._on_state_changed = on_state_changed or (lambda *a: None)

        self._lock = threading.Lock()
        self._runtimes: dict[str, _SourceRuntime] = {}
        self._active = False
        self._paused = False

    def is_active(self) -> bool:
        return self._active

    def is_paused(self) -> bool:
        return self._paused

    # -- transport -----------------------------------------------------

    def start(self) -> bool:
        if self._active:
            return False

        output_dir = self.session.output_dir or os.getcwd()
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as exc:
            self._on_source_error("", f"Could not create output directory: {exc}")
            return False

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        started_any = False
        for source in self.sources:
            if not source.enabled:
                continue
            base_name = f"{sanitize_filename(source.friendly_name)}_{timestamp}"
            final_path = os.path.join(output_dir, f"{base_name}.{self.session.container}")
            runtime = _SourceRuntime(source=source, base_name=base_name, final_path=final_path)
            self._runtimes[source.id] = runtime
            if self._start_segment(runtime, output_dir):
                started_any = True

        if not started_any:
            self._runtimes.clear()
            return False

        self._active = True
        self._paused = False
        self._on_state_changed("recording")
        return True

    def pause(self) -> None:
        if not self._active or self._paused:
            return
        with self._lock:
            for runtime in self._runtimes.values():
                if runtime.running:
                    self._stop_segment(runtime)
        self._paused = True
        self._on_state_changed("paused")

    def resume(self) -> None:
        if not self._active or not self._paused:
            return
        output_dir = self.session.output_dir or os.getcwd()
        with self._lock:
            for runtime in self._runtimes.values():
                if runtime.failed:
                    continue
                self._start_segment(runtime, output_dir)
        self._paused = False
        self._on_state_changed("recording")

    def stop(self) -> None:
        if not self._active:
            return
        with self._lock:
            for runtime in self._runtimes.values():
                if runtime.running:
                    self._stop_segment(runtime)
        for source_id, runtime in self._runtimes.items():
            final_path = self._finalize(runtime)
            self._on_source_stopped(source_id, final_path or "")
        self._runtimes.clear()
        self._active = False
        self._paused = False
        self._on_state_changed("stopped")

    # -- per-segment lifecycle ------------------------------------------

    def _start_segment(self, runtime: _SourceRuntime, output_dir: str) -> bool:
        device = self.capabilities.find_device(runtime.source.kind, runtime.source.device_id)
        if device is None:
            self._on_source_error(runtime.source.id, "Device is no longer available.")
            runtime.failed = True
            return False

        segment_index = len(runtime.segments)
        suffix = f"_seg{segment_index + 1}" if segment_index else ""
        segment_path = os.path.join(output_dir, f"{runtime.base_name}{suffix}.{self.session.container}")

        try:
            ffmpeg = build_source_command(self.capabilities, runtime.source, device, segment_path, self.ffmpeg_executable)
        except Exception as exc:
            self._on_source_error(runtime.source.id, str(exc))
            runtime.failed = True
            return False

        if ffmpeg is None:
            self._on_source_error(runtime.source.id, "This source type is not supported by the active capture backend.")
            runtime.failed = True
            return False

        @ffmpeg.on("progress")
        def _on_progress(progress, _runtime=runtime, _source_id=runtime.source.id):
            elapsed = _runtime.prior_seconds + progress.time.total_seconds()
            _runtime.last_reported_seconds = elapsed
            self._on_source_progress(_source_id, elapsed)

        error_holder: list = []

        def _run(_ffmpeg=ffmpeg, _errors=error_holder):
            try:
                _ffmpeg.execute()
            except FFmpegError as exc:
                _errors.append(exc.message)
            except Exception as exc:  # device vanished, permission denied, etc.
                _errors.append(str(exc))

        thread = threading.Thread(target=_run, daemon=True, name=f"av-capture-{runtime.source.id}")
        runtime.current_ffmpeg = ffmpeg
        runtime.current_thread = thread
        runtime.running = True
        runtime.segments.append(segment_path)
        thread.start()

        # Give a fast-failing device (busy / not found / bad option) a brief
        # moment to surface its error before calling this segment "started"
        # - mirrors the old engine's start()-returns-False-when-nothing-
        # worked contract instead of reporting success and erroring a beat
        # later.
        thread.join(timeout=0.6)
        if not thread.is_alive() and error_holder:
            runtime.running = False
            runtime.segments.pop()
            self._on_source_error(runtime.source.id, error_holder[0])
            runtime.failed = True
            return False

        self._on_source_started(runtime.source.id, segment_path)
        return True

    def _stop_segment(self, runtime: _SourceRuntime) -> None:
        ffmpeg = runtime.current_ffmpeg
        thread = runtime.current_thread
        if ffmpeg is not None:
            try:
                ffmpeg.terminate()
            except FFmpegError:
                pass
        if thread is not None:
            thread.join(timeout=_JOIN_TIMEOUT_SECONDS)
        # last_reported_seconds is already prior_seconds + this segment's own
        # elapsed time (see _on_progress above) - carry it forward as the
        # next segment's baseline so the displayed "recording time" keeps
        # counting across a pause/resume instead of resetting to 0.
        runtime.prior_seconds = runtime.last_reported_seconds
        runtime.running = False
        runtime.current_ffmpeg = None
        runtime.current_thread = None

    # -- final concat / rename --------------------------------------------

    def _finalize(self, runtime: _SourceRuntime) -> Optional[str]:
        segments = [path for path in runtime.segments if os.path.exists(path)]
        if not segments:
            return None

        if len(segments) == 1:
            if segments[0] != runtime.final_path:
                try:
                    os.replace(segments[0], runtime.final_path)
                except OSError as exc:
                    self._on_source_error(runtime.source.id, f"Could not finalize recording: {exc}")
                    return segments[0]
            return runtime.final_path

        return self._concat_segments(runtime, segments)

    def _concat_segments(self, runtime: _SourceRuntime, segments: list) -> Optional[str]:
        from media_core.ffmpeg import FFmpeg

        list_path = runtime.final_path + ".concat.txt"
        try:
            with open(list_path, "w", encoding="utf-8") as handle:
                for segment in segments:
                    # Single quotes in filenames need to be escaped for the
                    # concat demuxer - https://superuser.com/questions/787064
                    safe_name = str(segment).replace("'", "'\\''")
                    handle.write(f"file '{safe_name}'\n")

            ffmpeg = FFmpeg(executable=self.ffmpeg_executable).option("y")
            ffmpeg.input(list_path, **{"f": "concat", "safe": "0"})
            ffmpeg.output(runtime.final_path, **{"c": "copy"})
            ffmpeg.execute()
        except FFmpegError as exc:
            self._on_source_error(runtime.source.id, f"Could not join paused segments: {exc.message}")
            return segments[-1]
        except OSError as exc:
            self._on_source_error(runtime.source.id, f"Could not join paused segments: {exc}")
            return segments[-1]
        finally:
            try:
                os.remove(list_path)
            except OSError:
                pass

        for segment in segments:
            try:
                os.remove(segment)
            except OSError:
                pass
        return runtime.final_path

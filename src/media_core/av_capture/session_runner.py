import json
import os
import re
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime
from time import monotonic
from uuid import uuid4

from .mediacap import PROCESS_OPTIONS, check_mediacap, recording_args
from .models import VIDEO_KINDS


@dataclass
class _Recording:
    source_id: str
    path: str
    process: subprocess.Popen
    ready: threading.Event = field(default_factory=threading.Event)
    finished: threading.Event = field(default_factory=threading.Event)
    started: bool = False

    def send(self, command):
        if self.finished.is_set():
            return
        try:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
        except (OSError, ValueError):
            pass


class CaptureSessionRunner:
    def __init__(
        self, session, sources, capabilities, *,
        on_source_started, on_source_error, on_source_stopped,
        on_source_progress, on_state_changed, on_source_exit,
    ):
        self.session = session
        self.sources = sources
        self.capabilities = capabilities
        self._on_source_started = on_source_started
        self._on_source_error = on_source_error
        self._on_source_stopped = on_source_stopped
        self._on_source_progress = on_source_progress
        self._on_state_changed = on_state_changed
        self._on_source_exit = on_source_exit
        self._recordings = []

    def start(self):
        if not self.capabilities.executable:
            self._on_source_error("", check_mediacap().message)
            return False
        enabled_sources = [source for source in self.sources if source.enabled]
        devices_by_kind = {}
        discovery_errors = {}
        for kind in dict.fromkeys(source.kind for source in enabled_sources):
            try:
                devices_by_kind[kind] = self.capabilities.list_devices(kind)
            except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                discovery_errors[kind] = str(exc)

        available_sources = []
        for source in enabled_sources:
            if source.kind in discovery_errors:
                self._on_source_error(source.id, discovery_errors[source.kind])
                continue
            device = self.capabilities.resolve_device(
                devices_by_kind[source.kind], source.device_id, source.device_name or source.settings.get("screen_name", ""),
            )
            if device is None:
                self._on_source_error(source.id, "The device is no longer available. Edit the source to select it again.")
                continue
            available_sources.append((source, device))

        if not available_sources:
            return False

        output_dir = os.path.abspath(os.path.expanduser(self.session.output_dir))
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as exc:
            self._on_source_error("", f"Could not create output directory: {exc}")
            return False

        has_video = any(device.kind in VIDEO_KINDS for _, device in available_sources)
        container = self.session.video_format if has_video else self.session.audio_format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for source, device in available_sources:
            try:
                name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", source.friendly_name).strip(" .")[:90] or "capture"
                path = os.path.join(output_dir, f"{name}_{timestamp}_{uuid4().hex[:8]}.{container}")
                args = recording_args(device, source.settings, container, path)
                process = subprocess.Popen(
                    [self.capabilities.executable, *args],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    encoding="utf-8", errors="replace", **PROCESS_OPTIONS,
                )
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                self._on_source_error(source.id, str(exc))
                continue
            recording = _Recording(source.id, path, process)
            self._recordings.append(recording)
            threading.Thread(target=self._read_events, args=(recording,), daemon=True).start()

        deadline = monotonic() + 25
        for recording in self._recordings:
            if not recording.ready.wait(max(0, deadline - monotonic())):
                self._on_source_error(recording.source_id, "MediaCap did not start the recording in time.")
                recording.process.kill()
        return any(recording.started for recording in self._recordings)

    def _read_events(self, recording):
        process = recording.process
        error = ""
        last_line = ""
        paused_at = None
        paused_seconds = 0.0
        try:
            with process.stdout:
                for line in process.stdout:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        last_line = line.strip() or last_line
                        continue
                    if not isinstance(event, dict):
                        continue
                    event_type = event.get("event")
                    if event_type == "started":
                        recording.started = True
                        recording.ready.set()
                        self._on_source_started(recording.source_id, recording.path)
                    elif event_type == "paused" and paused_at is None:
                        paused_at = monotonic()
                    elif event_type == "resumed" and paused_at is not None:
                        paused_seconds += monotonic() - paused_at
                        paused_at = None
                    elif event_type == "status" and paused_at is None:
                        elapsed = max(0, event["elapsed_seconds"] - paused_seconds)
                        self._on_source_progress(recording.source_id, elapsed)
                    elif event_type == "error":
                        error = event.get("message", "")
                    elif event_type == "control-error":
                        self._on_source_error(recording.source_id, event.get("message", "MediaCap control failed."))
        finally:
            return_code = process.wait()
            try:
                process.stdin.close()
            except OSError:
                pass
            try:
                if return_code or not recording.started:
                    message = error or last_line or f"MediaCap stopped with exit code {return_code}."
                    self._on_source_error(recording.source_id, message)
                elif os.path.isfile(recording.path):
                    self._on_source_stopped(recording.source_id, recording.path)
                else:
                    self._on_source_error(recording.source_id, "MediaCap did not save a recording.")
            finally:
                recording.ready.set()
                recording.finished.set()
                self._on_source_exit(self)

    def all_finished(self):
        return all(recording.finished.is_set() for recording in self._recordings)

    def pause(self):
        for recording in self._recordings:
            recording.send("pause")
        self._on_state_changed("paused")

    def resume(self):
        for recording in self._recordings:
            recording.send("resume")
        self._on_state_changed("recording")

    def stop(self):
        for recording in self._recordings:
            recording.send("stop")
        deadline = monotonic() + 10
        for recording in self._recordings:
            if not recording.finished.wait(max(0, deadline - monotonic())):
                recording.process.kill()
        for recording in self._recordings:
            recording.finished.wait(1)

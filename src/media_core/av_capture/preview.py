import json
import os
import subprocess
import tempfile
import threading
from pathlib import Path
from time import monotonic

from .mediacap import PROCESS_OPTIONS, source_args
from .models import AUDIO_KINDS


class CapturePreview:
    def __init__(self, executable, device, settings, *, on_frame, on_error, on_finished):
        self._executable = executable
        self._device = device
        self._settings = settings
        self._on_frame = on_frame
        self._on_error = on_error
        self._on_finished = on_finished
        self._stop = threading.Event()

    def start(self):
        threading.Thread(target=self._run, daemon=True, name="mediacap-preview").start()

    def stop(self):
        self._stop.set()

    def _run(self):
        try:
            if not self._executable:
                raise RuntimeError("MediaCap was not found.")
            with tempfile.TemporaryDirectory(prefix="playform-preview-") as directory:
                self._capture(Path(directory))
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
            if not self._stop.is_set():
                self._on_error(str(exc))
        finally:
            self._on_finished()

    def _capture(self, directory):
        path = directory / "frames"
        arguments = source_args(self._device, self._settings, preview=True)
        audio = self._device.kind in AUDIO_KINDS
        sink = "--audio-samples" if audio else "--video-frames"
        with tempfile.TemporaryFile(mode="w+b") as events:
            process = subprocess.Popen(
                [self._executable, "--json", "capture", *arguments, sink, str(path),
                 "--duration", "5", "--stdin-control", "--no-interactive", "--status-interval", "0"],
                stdin=subprocess.PIPE, stdout=events, stderr=subprocess.STDOUT, **PROCESS_OPTIONS,
            )
            try:
                while not path.exists() and process.poll() is None and not self._stop.wait(0.025):
                    pass
                if path.is_file() and not self._stop.is_set():
                    with path.open("rb") as handle:
                        self._read_frames(handle, process, audio)
            finally:
                if process.poll() is None:
                    try:
                        process.stdin.write(b"stop\n")
                        process.stdin.flush()
                    except OSError:
                        pass
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                process.stdin.close()
            if process.returncode and not self._stop.is_set():
                events.seek(0)
                message = ""
                for line in events:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if event.get("event") == "error":
                        message = event.get("message", "")
                raise RuntimeError(message or f"MediaCap exited with code {process.returncode}.")

    def _read_frames(self, handle, process, audio):
        started = False
        next_frame = 0.0
        deadline = monotonic() + 25
        while not self._stop.is_set() and monotonic() < deadline:
            position = handle.tell()
            available = os.fstat(handle.fileno()).st_size
            line = handle.readline(4096)
            if line.endswith(b"\n"):
                if not started:
                    if line != b"MediaCap frames 1\n":
                        raise ValueError("MediaCap returned an invalid preview stream.")
                    started = True
                    continue
                metadata = json.loads(line)
                size = metadata["payload_bytes"]
                if not 0 < size <= 128 * 1024 * 1024:
                    raise ValueError("MediaCap returned an invalid preview frame.")
                if available - handle.tell() >= size:
                    now = monotonic()
                    if audio or now >= next_frame:
                        self._on_frame(metadata, handle.read(size))
                        next_frame = now + 0.2
                    else:
                        handle.seek(size, os.SEEK_CUR)
                    if handle.tell() >= 128 * 1024 * 1024:
                        return
                    continue
            handle.seek(position)
            if process.poll() is not None:
                return
            self._stop.wait(0.025)

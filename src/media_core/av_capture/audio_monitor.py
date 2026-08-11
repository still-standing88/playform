"""Real-time microphone monitoring: hear the mic through the system's
default output, plus a level meter - both driven off one ffmpeg process's
raw PCM output.

One process rather than two (one for astats/level, one for raw PCM):
dshow's shared-mode support for two simultaneous captures of the same
device isn't guaranteed the way it is for, say, PulseAudio, so this reads
raw s16le samples once and computes the peak level locally (same
struct.unpack technique the pre-ffmpeg-rewrite QAudioSource-based level
meter used) rather than also running ffmpeg's astats filter - the samples
needed for playback already give an equally accurate peak. astats
(level_meter.py) stays in use for the Audio output/loopback meter, which
has no playback path to hitch a ride on.
"""
from __future__ import annotations

import struct
import subprocess
import threading
from typing import Callable, Optional

from media_core.av_capture.capabilities import CaptureCapabilities
from media_core.av_capture.models import CaptureDevice, MediaKind
from media_core.ffmpeg.utils import is_windows

SAMPLE_RATE = 48000
CHANNELS = 2
_CHUNK_FRAMES = 1024  # ~21ms per chunk at 48kHz - short for low monitoring latency
_BYTES_PER_SAMPLE = 2  # s16le


def _peak_level(chunk: bytes) -> float:
    sample_count = len(chunk) // _BYTES_PER_SAMPLE
    if sample_count == 0:
        return 0.0
    samples = struct.unpack(f"<{sample_count}h", chunk[: sample_count * _BYTES_PER_SAMPLE])
    return min(1.0, max(abs(s) for s in samples) / 32768.0)


class AudioMonitorProbe:
    sample_rate = SAMPLE_RATE
    channels = CHANNELS

    def __init__(
        self,
        capabilities: CaptureCapabilities,
        device: CaptureDevice,
        ffmpeg_executable: str = "ffmpeg",
        on_level: Optional[Callable[[float], None]] = None,
        on_pcm_chunk: Optional[Callable[[bytes], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self._capabilities = capabilities
        self._device = device
        self._ffmpeg_executable = ffmpeg_executable
        self._on_level = on_level or (lambda level: None)
        self._on_pcm_chunk = on_pcm_chunk or (lambda chunk: None)
        self._on_error = on_error or (lambda message: None)
        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._stderr_lines: list[str] = []
        self._received_any = False
        self._stopping = False

    def start(self) -> bool:
        input_spec = self._capabilities.backend.build_input(
            MediaKind.AUDIO_INPUT, self._device, {"sample_rate": SAMPLE_RATE, "channels": CHANNELS},
        )
        if input_spec is None:
            self._on_error("This device can't be previewed with the active capture backend.")
            return False

        args = [self._ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-f", input_spec.format]
        for key, value in input_spec.options.items():
            args += [f"-{key}", str(value)]
        args += ["-i", input_spec.url, "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS), "-"]

        kwargs = {}
        if is_windows():
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = startupinfo

        try:
            self._process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
        except OSError as exc:
            self._on_error(str(exc))
            return False

        self._stopping = False
        self._stderr_lines = []
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True, name="av-capture-audio-monitor-err")
        self._stderr_thread.start()
        self._thread = threading.Thread(target=self._read_loop, daemon=True, name="av-capture-audio-monitor")
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stopping = True
        if self._process is not None:
            try:
                self._process.kill()  # monitoring only, no output file to finalize
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self._stderr_thread is not None:
            self._stderr_thread.join(timeout=2.0)
        self._process = None
        self._thread = None
        self._stderr_thread = None

    def _read_stderr(self) -> None:
        process = self._process
        if process is None or process.stderr is None:
            return
        for raw_line in process.stderr:
            line = raw_line.decode("utf-8", "replace").strip()
            if line:
                self._stderr_lines.append(line)

    def _read_loop(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        self._received_any = False
        chunk_bytes = _CHUNK_FRAMES * CHANNELS * _BYTES_PER_SAMPLE
        while True:
            chunk = process.stdout.read(chunk_bytes)
            if not chunk:
                break
            self._received_any = True
            self._on_pcm_chunk(chunk)
            self._on_level(_peak_level(chunk))

        process.wait(timeout=2.0)
        if not self._stopping and process.returncode not in (0, None) and not self._received_any:
            message = " ".join(self._stderr_lines) if self._stderr_lines else f"ffmpeg exited with code {process.returncode}"
            self._on_error(message)

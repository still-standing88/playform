"""Real-time audio input level probe, built on ffmpeg's own `astats` +
`ametadata` filters rather than a Qt audio API - grounded in the
ffmpeg-filters manual, Audio Filters section 8.59 "astats" (see
archive/docs/ffmpeg-manuals/ffmpeg-filters/8-audio-filters/astats.md):
`astats=metadata=1` injects `lavfi.astats.Overall.Peak_level` (dBFS) as
frame metadata, and `ametadata=print:key=...:file=-` prints it to stdout
once per short analysis window - this is the same live-metering technique
`ffplay`/`ffmpeg -af astats` based VU meters use, applied to whatever
capture device the source wizard's Preview page has open, so it reflects
the *actual* signal that would be recorded rather than a separate Qt
audio-tap path (the previous QAudioSource-based meter recorded nothing;
this reads the exact same device+options build_input() would use).

Framework-agnostic (no Qt import) - the dialogs.audio_level_meter Qt wrapper
re-emits `on_level`/`on_error` as signals, same split as everything else in
this package.
"""
from __future__ import annotations

import re
import subprocess
import threading
from typing import Callable, Optional

from media_core.av_capture.capabilities import CaptureCapabilities
from media_core.av_capture.models import CaptureDevice, MediaKind
from media_core.ffmpeg.utils import is_windows

_PEAK_LEVEL = re.compile(r"lavfi\.astats\.Overall\.Peak_level=(-?[\d.]+|-inf|nan)")
# `direct=1` matters here: without it, ametadata's file writer batches its
# output like a normal buffered stream, so a short-lived preview meter can
# be stopped before anything is ever flushed to the pipe (confirmed with a
# real device - 0 lines received over 3s without `direct`, immediate
# streaming with it). See ffmpeg-filters manual, Multimedia Filters 20.13
# "metadata, ametadata" - `direct`: "Reduces buffering in print mode when
# output is written to a URL set using file."
_FILTER = "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.Peak_level:file=-:direct=1"


class AudioLevelProbe:
    def __init__(
        self,
        capabilities: CaptureCapabilities,
        device: CaptureDevice,
        kind: MediaKind,
        ffmpeg_executable: str = "ffmpeg",
        on_level: Optional[Callable[[float], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self._capabilities = capabilities
        self._device = device
        self._kind = kind
        self._ffmpeg_executable = ffmpeg_executable
        self._on_level = on_level or (lambda level: None)
        self._on_error = on_error or (lambda message: None)
        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> bool:
        input_spec = self._capabilities.backend.build_input(self._kind, self._device, {})
        if input_spec is None:
            self._on_error("This device can't be previewed with the active capture backend.")
            return False

        args = [self._ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-f", input_spec.format]
        for key, value in input_spec.options.items():
            args += [f"-{key}", str(value)]
        args += ["-i", input_spec.url, "-af", _FILTER, "-f", "null", "-"]

        kwargs = {}
        if is_windows():
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = startupinfo

        try:
            self._process = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="replace", bufsize=1, **kwargs,
            )
        except OSError as exc:
            self._on_error(str(exc))
            return False

        self._thread = threading.Thread(target=self._read_loop, daemon=True, name="av-capture-level-meter")
        self._thread.start()
        return True

    def stop(self) -> None:
        if self._process is not None:
            try:
                self._process.kill()  # metering only, no output file to finalize - a hard kill is fine
            except OSError:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._process = None
        self._thread = None

    def _read_loop(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            match = _PEAK_LEVEL.search(line)
            if not match:
                continue
            raw = match.group(1)
            if raw in ("-inf", "nan"):
                self._on_level(0.0)
                continue
            try:
                db = float(raw)
            except ValueError:
                continue
            self._on_level(max(0.0, min(1.0, 10 ** (db / 20.0))))

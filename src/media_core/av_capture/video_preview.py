"""Live video preview for camera/monitor/window sources - a continuous
downscaled Motion JPEG feed piped from ffmpeg's stdout, rather than a
single test-frame grab, so the Add/Edit Source wizard shows the same kind
of "yes, that's the right device/crop/cursor setting" confirmation a live
feed gives you (ffmpeg's mjpeg encoder is a standard, always-available
video encoder - see ffmpeg-codecs manual, Video Encoders "mjpeg" - so this
needs nothing beyond what capture already uses).

Deliberately capped well below recording quality/resolution: this is a
device-picking aid, not the actual capture path (build_source_command's
`-preset ultrafast` full-resolution encode is untouched by any of this).
"""
from __future__ import annotations

import subprocess
import threading
from typing import Callable, Optional

from media_core.av_capture.capabilities import CaptureCapabilities
from media_core.av_capture.models import CaptureDevice, MediaKind
from media_core.ffmpeg.utils import is_windows

_JPEG_SOI = b"\xff\xd8"
_JPEG_EOI = b"\xff\xd9"

_PREVIEW_WIDTH = 480
_PREVIEW_FPS = 12


class VideoPreviewProbe:
    def __init__(
        self,
        capabilities: CaptureCapabilities,
        device: CaptureDevice,
        kind: MediaKind,
        settings: Optional[dict] = None,
        ffmpeg_executable: str = "ffmpeg",
        on_frame: Optional[Callable[[bytes], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self._capabilities = capabilities
        self._device = device
        self._kind = kind
        self._settings = settings or {}
        self._ffmpeg_executable = ffmpeg_executable
        self._on_frame = on_frame or (lambda frame: None)
        self._on_error = on_error or (lambda message: None)
        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._stderr_lines: list[str] = []
        self._received_any = False
        self._stopping = False

    def start(self) -> bool:
        input_spec = self._capabilities.backend.build_input(self._kind, self._device, self._settings)
        if input_spec is None:
            self._on_error("This device can't be previewed with the active capture backend.")
            return False

        args = [self._ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-f", input_spec.format]
        for key, value in input_spec.options.items():
            args += [f"-{key}", str(value)]
        args += [
            "-i", input_spec.url,
            "-vf", f"scale={_PREVIEW_WIDTH}:-2,fps={_PREVIEW_FPS}",
            "-c:v", "mjpeg", "-q:v", "6", "-f", "mjpeg", "-",
        ]

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
        self._stderr_lines: list[str] = []
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True, name="av-capture-video-preview-err")
        self._stderr_thread.start()
        self._thread = threading.Thread(target=self._read_loop, daemon=True, name="av-capture-video-preview")
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stopping = True
        if self._process is not None:
            try:
                self._process.kill()  # preview only, no output file to finalize
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
        buffer = bytearray()
        while True:
            chunk = process.stdout.read(65536)
            if not chunk:
                break
            buffer.extend(chunk)
            self._extract_frames(buffer)

        # stdout hit EOF - if that happened because ffmpeg exited with an
        # error (device busy, permission denied, ...) rather than because
        # stop() killed it, surface that instead of leaving the preview
        # silently blank. Not reported once at least one frame came through,
        # since a device that worked and then hiccuped isn't "unavailable".
        process.wait(timeout=2.0)
        if not self._stopping and process.returncode not in (0, None) and not self._received_any:
            # -loglevel error keeps ffmpeg's output to just the relevant
            # lines (typically 1-3), so joining all of them is more useful
            # than just the last one - dshow's failures in particular print
            # a descriptive line ("Could not run graph...") followed by a
            # terser one ("...: I/O error").
            message = " ".join(self._stderr_lines) if self._stderr_lines else f"ffmpeg exited with code {process.returncode}"
            self._on_error(message)

    def _extract_frames(self, buffer: bytearray) -> None:
        while True:
            start = buffer.find(_JPEG_SOI)
            if start < 0:
                # No frame start in the buffer - drop it, except a trailing
                # lone 0xFF that could be the first byte of a split marker.
                if buffer and buffer[-1] == 0xFF:
                    del buffer[:-1]
                else:
                    buffer.clear()
                return
            if start > 0:
                del buffer[:start]
            end = buffer.find(_JPEG_EOI, 2)
            if end < 0:
                return  # frame not complete yet - wait for more data
            end += 2
            self._received_any = True
            self._on_frame(bytes(buffer[:end]))
            del buffer[:end]

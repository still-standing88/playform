"""Subprocess helper for short-lived *probe* commands: `ffmpeg -list_devices
true`, `ffmpeg -list_options true`, and the platform tools ffmpeg's own docs
point to for device listing where ffmpeg has no built-in one (`pactl list
sources` per the pulse indev manual, `xrandr`/`wmctrl` for X11 the way the
x11grab manual points at `xdpyinfo`/`xwininfo`).

Not built on media_core.ffmpeg.FFmpeg: that class treats any non-zero exit
as an FFmpegError, but `ffmpeg -list_devices true -i dummy` (and
`-list_options true`) always exit 1 by design after printing the device
list to stderr ("Immediate exit requested") - it is not an error here.

Every call here is expected to fail sometimes (tool not installed, no
devices, permission denied, headless session) - that is normal capability
detection, not an exceptional condition, so callers get a result object
with an `ok` flag instead of an exception.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from media_core.ffmpeg.utils import is_windows


@dataclass
class ProbeResult:
    ok: bool
    returncode: Optional[int]
    stdout: str
    stderr: str

    @property
    def text(self) -> str:
        """ffmpeg's device/format listings go to stderr; most CLI tools
        (pactl, xrandr, wmctrl) print to stdout - combine both so callers
        can grep either without caring which stream a given tool used."""
        return self.stdout + "\n" + self.stderr


def run_probe(args: list[str], timeout: float = 8.0) -> ProbeResult:
    kwargs = {}
    if is_windows():
        # Prevent a console window from flashing up behind the GUI app for
        # every device-list probe.
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            **kwargs,
        )
        return ProbeResult(True, completed.returncode, completed.stdout or "", completed.stderr or "")
    except FileNotFoundError:
        return ProbeResult(False, None, "", f"{args[0]} not found")
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return ProbeResult(False, None, stdout, stderr or "timed out")
    except OSError as exc:
        return ProbeResult(False, None, "", str(exc))


def tool_available(name: str) -> bool:
    return shutil.which(name) is not None

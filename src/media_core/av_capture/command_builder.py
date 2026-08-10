"""Turns one CaptureSourceConfig (+ its resolved CaptureDevice) into a
media_core.ffmpeg.FFmpeg instance ready to `.execute()`.

Encoder choice on the output side is deliberately fixed rather than exposed
as a setting: `-preset ultrafast` matters for a *live* capture in a way it
doesn't for the batch converter's file-to-file jobs (media_core.ffmpeg
.format_capabilities/effects_catalog), because a slower preset can make x264
fall behind the incoming frames and the input device's own buffer isn't
infinite. Per-source settings instead control what the capture *device*
itself is asked for (resolution/fps/cursor/volume) - see
backends/*.build_input().
"""
from __future__ import annotations

import re

from media_core.av_capture.backends.base import InputSpec
from media_core.av_capture.capabilities import CaptureCapabilities
from media_core.av_capture.device_probe import run_probe
from media_core.av_capture.models import CaptureDevice, CaptureSourceConfig, MediaKind

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')


def sanitize_filename(name: str) -> str:
    cleaned = _INVALID_FILENAME_CHARS.sub("_", name).strip()
    return cleaned or "source"


def output_options_for(kind: MediaKind, settings: dict) -> dict:
    if kind in (MediaKind.CAMERA, MediaKind.MONITOR, MediaKind.WINDOW):
        return {"c:v": "libx264", "preset": "ultrafast", "crf": "18", "pix_fmt": "yuv420p"}

    options: dict = {"c:a": "aac", "b:a": "192k"}
    volume = settings.get("volume")
    if volume is not None and int(volume) != 100:
        options["af"] = f"volume={max(0, int(volume)) / 100.0:.3f}"
    return options


def build_source_command(
    capabilities: CaptureCapabilities,
    source: CaptureSourceConfig,
    device: CaptureDevice,
    output_path: str,
    ffmpeg_executable: str = "ffmpeg",
):
    """Returns a ready-to-`.execute()` FFmpeg instance, or None if this
    kind/device can't be captured with the active backend (source is then
    reported as a per-source error by the caller, the same as a vanished
    device)."""
    from media_core.ffmpeg import FFmpeg  # local import: keeps FFmpeg optional for pure device-probing callers

    input_spec: InputSpec = capabilities.backend.build_input(source.kind, device, source.settings)
    if input_spec is None:
        return None

    ffmpeg = FFmpeg(executable=ffmpeg_executable).option("y")
    ffmpeg.input(input_spec.url, **{"f": input_spec.format, **input_spec.options})
    ffmpeg.output(output_path, **output_options_for(source.kind, source.settings))
    return ffmpeg


def capture_still_frame(
    capabilities: CaptureCapabilities,
    kind: MediaKind,
    device: CaptureDevice,
    settings: dict,
    output_path: str,
    ffmpeg_executable: str = "ffmpeg",
    timeout: float = 8.0,
) -> tuple[bool, str]:
    """One-shot device confirmation for the source wizard's Preview page:
    grab a single frame to a PNG rather than a live video feed - simpler
    than decoding a raw video stream from ffmpeg's stdout in real time, and
    still proves the picked device/resolution/crop/cursor setting actually
    produces the expected image, which is the point of a wizard preview."""
    input_spec = capabilities.backend.build_input(kind, device, settings)
    if input_spec is None:
        return False, "This source type is not supported by the active capture backend."

    args = [ffmpeg_executable, "-hide_banner", "-loglevel", "error", "-y", "-f", input_spec.format]
    for key, value in input_spec.options.items():
        args += [f"-{key}", str(value)]
    args += ["-i", input_spec.url, "-frames:v", "1", output_path]

    result = run_probe(args, timeout=timeout)
    if not result.ok or result.returncode != 0:
        return False, result.stderr.strip() or "ffmpeg exited with an error."
    return True, ""

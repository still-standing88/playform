"""Multi-source ffmpeg-based capture engine.

Framework-agnostic (no Qt/app_config imports anywhere in this package - same
rule as media_core.ffmpeg.conversion_job / media_core.m4b_tools), driving
device discovery and recording the same way the `ffmpeg` command line tool
itself does on each platform:

    Windows  - dshow (camera + audio input) and gdigrab (desktop/window)
    macOS    - avfoundation (camera + screen + audio, one unified device list)
    Linux    - v4l2 (camera), x11grab (desktop/window), pulse/alsa (audio)

See backends/base.py for the per-platform interface and capabilities.py for
the single entry point UI code should query ("what can this machine capture
right now"). session_runner.CaptureSessionRunner is the engine every capture
funnels through, in the same spirit as media_core.ffmpeg.conversion_job
.ConversionRunner and media_core.m4b_tools.audiobook.Audiobook - it reports
through plain callbacks and knows nothing about Qt, so a tools/ wrapper
drives it on a QThread the same way tools.ffmpeg.batch_converter.job drives
ConversionRunner.
"""
from __future__ import annotations

from media_core.av_capture.models import (
    AUDIO_KINDS,
    VIDEO_KINDS,
    CaptureDevice,
    CaptureFormatOption,
    CaptureSessionConfig,
    CaptureSourceConfig,
    MediaKind,
    new_id,
)

__all__ = [
    "AUDIO_KINDS",
    "VIDEO_KINDS",
    "CaptureDevice",
    "CaptureFormatOption",
    "CaptureSessionConfig",
    "CaptureSourceConfig",
    "MediaKind",
    "new_id",
]

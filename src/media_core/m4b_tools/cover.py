from __future__ import annotations

import os

from media_core.ffmpeg import FFmpeg
from media_core.ffmpeg.errors import FFmpegError

_ALLOWED_COVER_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def extract_cover(input_path, output_path, ffmpeg_executable: str = "ffmpeg") -> bool:
    """Dump an audio file's embedded cover image to disk.

    Returns False (instead of raising) if the file has no cover - that's the common case
    for plain audiobook chapters, not an error condition callers need to handle specially.
    """
    ext = os.path.splitext(str(output_path))[1].lower()
    if ext not in _ALLOWED_COVER_EXTENSIONS:
        raise ValueError(f"Output extension must be one of {sorted(_ALLOWED_COVER_EXTENSIONS)}")

    ffmpeg = FFmpeg(executable=ffmpeg_executable).option("y")
    ffmpeg.input(str(input_path)).output(str(output_path))
    try:
        ffmpeg.execute()
    except FFmpegError:
        return False
    return os.path.exists(output_path) and os.path.getsize(output_path) > 0


def add_cover(input_path, cover_path, output_path, ffmpeg_executable: str = "ffmpeg") -> None:
    """Attach a cover image to an audio file, stream-copying everything else."""
    ffmpeg = FFmpeg(executable=ffmpeg_executable).option("y")
    ffmpeg.input(str(input_path))
    ffmpeg.input(str(cover_path))
    ffmpeg.output(str(output_path), **{
        "map": ["0:a", "1"],
        "c": "copy",
        "disposition:v:0": "attached_pic",
    })
    ffmpeg.execute()

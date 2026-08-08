from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from media_core.m4b_tools.audiobook import Audiobook
from media_core.m4b_tools.runner import M4bToolsRunner


class BindRunner(M4bToolsRunner):
    """Drives `Audiobook.bind()` from a worker thread with pause/cancel support.

    Mirrors `media_core.ffmpeg.conversion_job.ConversionRunner`: construct it with plain
    callbacks, call `run()` on a worker thread, and `pause()`/`resume()`/`stop()` from the
    UI thread. Wraps the `m4b-util bind` subcommand (a folder or explicit file list, each
    file becoming one chapter, output as a single .m4b).
    """

    def __init__(
        self,
        output_path,
        input_dir: Optional[str] = None,
        input_files: Optional[list] = None,
        author: Optional[str] = None,
        title: Optional[str] = None,
        date: Optional[str] = None,
        bitrate: str = "128k",
        cover: Optional[str] = None,
        use_filenames: bool = False,
        decode_durations: bool = False,
        keep_temp_files: bool = False,
        ffmpeg_executable: str = "ffmpeg",
        ffprobe_executable: str = "ffprobe",
        on_file_progress: Optional[Callable[[str], None]] = None,
        on_log_line: Optional[Callable[[str], None]] = None,
    ):
        super().__init__()
        self.output_path = Path(output_path)
        self.input_dir = input_dir
        self.input_files = input_files
        self.use_filenames = use_filenames
        self.decode_durations = decode_durations

        self.audiobook = Audiobook(
            author=author,
            title=title,
            date=date,
            bitrate=bitrate,
            cover=Path(cover) if cover else None,
            keep_temp_files=keep_temp_files,
            ffmpeg_executable=ffmpeg_executable,
            ffprobe_executable=ffprobe_executable,
            on_log_line=on_log_line or (lambda line: None),
            on_file_progress=on_file_progress or (lambda name: None),
            should_continue=self._checkpoint,
        )

    def run(self) -> bool:
        """Scan the source files, then bind them into `self.output_path`.

        Returns True on success, False if binding failed or `stop()` was called.
        """
        if self.input_files:
            self.audiobook.add_chapters_from_filelist(
                [Path(f) for f in self.input_files], self.use_filenames, self.decode_durations
            )
        elif self.input_dir:
            self.audiobook.add_chapters_from_directory(
                self.input_dir, self.use_filenames, self.decode_durations
            )
        else:
            raise ValueError("Either input_dir or input_files must be provided.")

        if not self._is_running:
            return False

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        return self.audiobook.bind(self.output_path)

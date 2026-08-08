from PySide6.QtCore import QThread, Signal

from tools.ffmpeg_handler import FFmpegHandler
from media_core.ffmpeg.conversion_job import ConversionRunner, resolve_files_from_entries

__all__ = ["BatchConverterJob", "resolve_files_from_entries"]


class BatchConverterJob(QThread):
    overall_progress = Signal(int, int, str)
    file_progress = Signal(str)
    file_completed = Signal(str, bool, str)
    log_line = Signal(str)
    finished_all = Signal(bool)

    def __init__(self, entries, convert_options: dict, processing_effects: list, destination_options: dict):
        super().__init__()
        ffmpeg_path, ffprobe_path = FFmpegHandler.get_ffmpeg_binary()
        self._runner = ConversionRunner(
            entries, convert_options, processing_effects, destination_options,
            ffmpeg_executable=str(ffmpeg_path),
            ffprobe_executable=str(ffprobe_path) if ffprobe_path else "ffprobe",
            on_overall_progress=self.overall_progress.emit,
            on_file_progress=self.file_progress.emit,
            on_file_completed=self.file_completed.emit,
            on_log_line=self.log_line.emit,
        )

    def run(self):
        completed = self._runner.run()
        self.finished_all.emit(completed)

    def stop(self):
        self._runner.stop()

    def pause(self):
        self._runner.pause()

    def resume(self):
        self._runner.resume()

    def is_paused(self) -> bool:
        return self._runner.is_paused()

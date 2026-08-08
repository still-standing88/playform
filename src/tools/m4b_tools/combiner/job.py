from PySide6.QtCore import QThread, Signal

from media_core.m4b_tools import CombineRunner
from media_core.m4b_tools.metadata_dump import dump_metadata_rows, write_metadata_csv


class CombineJob(QThread):
    overall_progress = Signal(int, int, str)
    file_progress = Signal(str)
    log_line = Signal(str)
    finished_job = Signal(bool)

    def __init__(self, **combine_kwargs):
        super().__init__()
        self._runner = CombineRunner(
            **combine_kwargs,
            on_overall_progress=self.overall_progress.emit,
            on_file_progress=self.file_progress.emit,
            on_log_line=self.log_line.emit,
        )

    def run(self):
        success = self._runner.run()
        self.finished_job.emit(success)

    def stop(self):
        self._runner.stop()

    def pause(self):
        self._runner.pause()

    def resume(self):
        self._runner.resume()


class MetadataDumpJob(QThread):
    overall_progress = Signal(int, int, str)
    log_line = Signal(str)
    finished_job = Signal(bool, int)

    def __init__(self, input_paths: list, output_csv: str, ffprobe_executable: str = "ffprobe"):
        super().__init__()
        self.input_paths = list(input_paths)
        self.output_csv = output_csv
        self.ffprobe_executable = ffprobe_executable
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        all_rows = []
        total = len(self.input_paths)

        for index, path in enumerate(self.input_paths):
            if not self._is_running:
                break

            self.overall_progress.emit(index, total, path)
            try:
                rows = dump_metadata_rows(path, self.ffprobe_executable)
                all_rows.extend(rows)
                self.log_line.emit(f"OK: {path} — {len(rows)} row(s)")
            except Exception as error:
                self.log_line.emit(f"FAILED: {path} — {error}")

        if not self._is_running:
            self.finished_job.emit(False, 0)
            return

        try:
            write_metadata_csv(all_rows, self.output_csv)
        except OSError as error:
            self.log_line.emit(f"FAILED to write CSV: {error}")
            self.finished_job.emit(False, 0)
            return

        self.overall_progress.emit(total, total, "")
        self.finished_job.emit(True, len(all_rows))

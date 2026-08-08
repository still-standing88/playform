from PySide6.QtCore import QThread, Signal

from media_core.m4b_tools import BindRunner, SplitRunner


class BindJob(QThread):
    file_progress = Signal(str)
    log_line = Signal(str)
    finished_job = Signal(bool)

    def __init__(self, **bind_kwargs):
        super().__init__()
        self._runner = BindRunner(
            **bind_kwargs,
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


class SplitJob(QThread):
    overall_progress = Signal(int, int, str)
    file_completed = Signal(str, bool, str)
    log_line = Signal(str)
    finished_job = Signal(bool)

    def __init__(self, **split_kwargs):
        super().__init__()
        self._runner = SplitRunner(
            **split_kwargs,
            on_overall_progress=self.overall_progress.emit,
            on_file_completed=self.file_completed.emit,
            on_log_line=self.log_line.emit,
        )

    def run(self):
        successful, total = self._runner.run()
        self.finished_job.emit(total > 0 and successful == total)

    def stop(self):
        self._runner.stop()

    def pause(self):
        self._runner.pause()

    def resume(self):
        self._runner.resume()


class SimpleM4BTask(QThread):
    """Runs a quick, single-outcome m4b_tools function (slide/labels/cover) on a worker
    thread. These don't report incremental progress, only log lines and a final result.
    """

    log_line = Signal(str)
    finished_job = Signal(bool, str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def run(self):
        kwargs = dict(self._kwargs)
        kwargs.setdefault("on_log_line", self.log_line.emit)
        try:
            result = self._func(*self._args, **kwargs)
            self.finished_job.emit(bool(result), "")
        except Exception as error:
            self.finished_job.emit(False, str(error))

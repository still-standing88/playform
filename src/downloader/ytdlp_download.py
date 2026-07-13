from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from PySide6.QtCore import QObject, Signal, QProcess

import player.url as ytdlp_url
from .downloader import DownloadStatus

_PROGRESS_PREFIX = "YTDLP_PROGRESS:"
_FILEPATH_PREFIX = "YTDLP_FILEPATH:"


def _guess_filename(url: str) -> str:
    name = Path(urlparse(url).path).name
    return name or "download"


class YtdlpDownloadItem(QObject):
    progress_changed = Signal(int, int)
    status_changed = Signal(object)
    speed_changed = Signal(float)
    error_occurred = Signal(str)
    finished = Signal(bool)

    def __init__(self, url, destination, filename=None):
        super().__init__()
        self.url = url
        self.destination = Path(destination)
        self.filename = filename or _guess_filename(url)
        self.filepath = self.destination / self.filename

        self.status = DownloadStatus.QUEUED
        self.downloaded_size = 0
        self.total_size = 0
        self.download_speed = 0.0
        self.error_message = ""
        self.retry_count = 0
        self.max_retries = 3

        self._reply = None
        self._process: Optional[QProcess] = None

    def get_info(self):
        return {
            'url': self.url,
            'filename': self.filename,
            'destination': str(self.destination),
            'filepath': str(self.filepath),
            'status': self.status.value,
            'downloaded_size': self.downloaded_size,
            'total_size': self.total_size,
            'speed': self.download_speed,
            'error': self.error_message,
            'retry_count': self.retry_count
        }

    def set_status(self, status):
        if self.status != status:
            self.status = status
            self.status_changed.emit(status)

    def start(self):
        self.destination.mkdir(parents=True, exist_ok=True)

        output_template = str(self.destination / "%(title)s.%(ext)s")
        progress_template = (
            f"download:{_PROGRESS_PREFIX}"
            "%(progress.downloaded_bytes)s|%(progress.total_bytes_estimate)s|%(progress.speed)s"
        )
        args = [
            "--newline",
            "--progress-template", progress_template,
            "--print", f"after_move:{_FILEPATH_PREFIX}%(filepath)s",
            "-o", output_template,
        ] + ytdlp_url._get_deno_arg() + [self.url]

        self._process = QProcess(self)
        self._process.setProgram(ytdlp_url.YTDLP_PATH)
        self._process.setArguments(args)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_process_error)

        self.set_status(DownloadStatus.DOWNLOADING)
        self._process.start()

    def cancel(self):
        if self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
        self.set_status(DownloadStatus.CANCELLED)

    def _on_stdout(self):
        if self._process is None:
            return
        data = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="ignore")
        for line in data.splitlines():
            self._parse_line(line)

    def _parse_line(self, line: str):
        if line.startswith(_PROGRESS_PREFIX):
            parts = line[len(_PROGRESS_PREFIX):].split("|")
            if len(parts) != 3:
                return
            self.downloaded_size = self._safe_number(parts[0], int)
            self.total_size = self._safe_number(parts[1], int)
            self.download_speed = self._safe_number(parts[2], float)
            self.progress_changed.emit(self.downloaded_size, self.total_size)
            self.speed_changed.emit(self.download_speed)
        elif line.startswith(_FILEPATH_PREFIX):
            filepath = line[len(_FILEPATH_PREFIX):].strip()
            if filepath:
                self.filepath = Path(filepath)
                self.filename = self.filepath.name

    @staticmethod
    def _safe_number(value: str, cast):
        try:
            return cast(float(value))
        except (TypeError, ValueError):
            return 0

    def _on_finished(self, exit_code, exit_status):
        if self.status == DownloadStatus.CANCELLED:
            return

        if exit_code == 0 and exit_status == QProcess.ExitStatus.NormalExit:
            if self.total_size:
                self.downloaded_size = self.total_size
            self.set_status(DownloadStatus.COMPLETED)
            self.finished.emit(True)
        else:
            stderr = bytes(self._process.readAllStandardError()).decode("utf-8", errors="ignore") if self._process else ""
            lines = [l for l in stderr.strip().splitlines() if l.strip()]
            self.error_message = lines[-1] if lines else _("yt-dlp exited with an error")
            self.error_occurred.emit(self.error_message)
            self.set_status(DownloadStatus.FAILED)
            self.finished.emit(False)

    def _on_process_error(self, error):
        self.error_message = _("Failed to start yt-dlp process")
        self.error_occurred.emit(self.error_message)
        self.set_status(DownloadStatus.FAILED)
        self.finished.emit(False)

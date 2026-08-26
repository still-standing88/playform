"""Framework-agnostic yt-dlp download queue engine.

Same shape as media_core.m4b_tools / conversion_job: plain callbacks plus
threading primitives, zero Qt/app_config imports. The GUI layer (the
yt-dlp Download Manager dialog) re-emits these callbacks as Qt signals.

The engine owns one background worker thread that downloads queued entries
one at a time by shelling out to the yt-dlp binary with --newline progress
output. Queue state persists to a JSON file in the app's data folder so
downloads survive an app restart (paused/interrupted entries resume via
yt-dlp's own partial-file continuation).
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

CATEGORY_YOUTUBE_VIDEOS = "youtube_videos"
CATEGORY_YOUTUBE_PLAYLISTS = "youtube_playlists"
CATEGORY_YOUTUBE_CHANNELS = "youtube_channels"
CATEGORY_OTHER = "other"

CATEGORY_LABELS = {
    CATEGORY_YOUTUBE_VIDEOS: "YouTube Videos",
    CATEGORY_YOUTUBE_PLAYLISTS: "YouTube Playlists",
    CATEGORY_YOUTUBE_CHANNELS: "YouTube Channels",
    CATEGORY_OTHER: "Other Videos",
}

STATUS_QUEUED = "queued"
STATUS_DOWNLOADING = "downloading"
STATUS_PAUSED = "paused"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

_NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}

_PROGRESS_RE = re.compile(
    r"\[download\]\s+(?P<pct>[\d.]+)% of\s+~?\s*(?P<size>[\d.]+\w+)"
    r"(?: at (?P<speed>[\d.]+\w+/s))?(?: ETA (?P<eta>[\d:]+))?"
)
_DESTINATION_RE = re.compile(r"\[download\] Destination: (?P<path>.+)")
_ALREADY_RE = re.compile(r"\[download\] (?P<path>.+) has already been downloaded")
_MERGER_RE = re.compile(r"\[(?:Merger|ExtractAudio)\] Destination: (?P<path>.+)")


def classify_url(url: str) -> str:
    """Coarse URL classification for the manager's category tree."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return CATEGORY_OTHER
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""
    query = parse_qs(parsed.query or "")

    if host in ("youtu.be",):
        return CATEGORY_YOUTUBE_VIDEOS
    if host.endswith("youtube.com") or host == "youtube.com":
        if path.startswith("/playlist"):
            return CATEGORY_YOUTUBE_PLAYLISTS
        if "list" in query and not path.startswith("/watch"):
            return CATEGORY_YOUTUBE_PLAYLISTS
        if path.startswith(("/@", "/channel/", "/c/", "/user/")):
            return CATEGORY_YOUTUBE_CHANNELS
        if path.startswith("/watch") or "list" in query:
            return CATEGORY_YOUTUBE_VIDEOS
    return CATEGORY_OTHER


def url_has_playlist_param(url: str) -> bool:
    try:
        return "list" in (parse_qs(urlparse(url).query or "") or {})
    except ValueError:
        return False


def _deno_args() -> list:
    # Same helper role as player.util.url._get_deno_arg -- deno is solely a
    # yt-dlp dependency; duplicated here because media_core must not import
    # from the player package.
    name = "deno.exe" if os.name == "nt" else "deno"
    try:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidate = os.path.join(os.path.dirname(base), "bin", name)
        if os.path.isfile(candidate):
            return ["--js-runtimes", f"deno:{candidate}", "--remote-components", "ejs:github"]
    except Exception:
        pass
    return ["--remote-components", "ejs:github"]


def find_ytdlp_binary() -> str:
    """Locate the yt-dlp binary the same way the player does (pref path,
    then PATH) without importing app_config/player."""
    exe = "yt-dlp.exe" if os.name == "nt" else "yt-dlp"
    try:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidate = os.path.join(os.path.dirname(base), "bin", exe)
        if os.path.isfile(candidate):
            return candidate
    except Exception:
        pass
    path_var = os.environ.get("PATH", "")
    for directory in path_var.split(os.pathsep):
        candidate = os.path.join(directory, exe)
        if os.path.isfile(candidate):
            return candidate
    return ""


def _cookies_args() -> list:
    args = []
    try:
        from app_config import prefs as _prefs
        cookies_file = _prefs.prefs.get("youtube_cookies")
        if cookies_file:
            args.extend(["--cookies", cookies_file])
    except Exception:
        pass
    return args


def _ffmpeg_location_args() -> list:
    # Same bin-dir resolution as tools.ffmpeg_handler.FFmpegHandler, inlined
    # because media_core must not import from the tools layer.
    args = []
    try:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidate = os.path.join(os.path.dirname(base), "bin", "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if os.path.isfile(candidate):
            args.extend(["--ffmpeg-location", os.path.dirname(candidate)])
    except Exception:
        pass
    return args


def _entry_from_raw(raw: dict) -> Optional[dict]:
    entry_url = raw.get("url") or raw.get("webpage_url") or ""
    entry_id = raw.get("id") or ""
    if entry_url and not entry_url.startswith("http"):
        entry_url = f"https://www.youtube.com/watch?v={entry_id}"
    if not entry_url and not entry_id:
        return None
    return {
        "id": entry_id,
        "title": raw.get("title") or entry_id or "Untitled",
        "url": entry_url,
        "duration": raw.get("duration") or 0,
        "date": raw.get("upload_date") or raw.get("release_timestamp") or "",
        "playlist_title": raw.get("playlist") or raw.get("playlist_title") or "",
    }


def fetch_flat_entries(url: str, on_log: Optional[Callable[[str], None]] = None,
                       cancel_event: Optional[threading.Event] = None) -> list:
    """List a playlist/channel's videos without downloading (--flat-playlist
    --dump-json; stdout carries one JSON object per entry, the same shape
    the player's own flat listing relies on). Returns [{id, title, url,
    duration, date}, ...]. Runs on its caller's thread."""
    binary = find_ytdlp_binary()
    if not binary:
        raise RuntimeError("yt-dlp executable was not found.")

    cmd = [binary, "--flat-playlist", "--dump-json", "--no-warnings"] \
        + _deno_args() + _cookies_args()
    cmd.append(url)

    if on_log:
        on_log(f"$ {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", **_NO_WINDOW,
    )
    entries = []
    stderr_tail: list = []

    def _drain_stderr():
        assert process.stderr is not None
        for line in process.stderr:
            line = line.strip()
            if not line:
                continue
            stderr_tail.append(line)
            if len(stderr_tail) > 50:
                stderr_tail.pop(0)
            if on_log:
                on_log(line)

    reader = threading.Thread(target=_drain_stderr, daemon=True)
    reader.start()

    cancelled = False
    try:
        assert process.stdout is not None
        for line in process.stdout:
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                break
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data.get("entries"), list):
                for raw in data["entries"]:
                    entry = _entry_from_raw(raw)
                    if entry is not None:
                        entries.append(entry)
            else:
                entry = _entry_from_raw(data)
                if entry is not None:
                    entries.append(entry)
        returncode = process.wait()
    finally:
        if process.poll() is None:
            process.terminate()

    if cancelled:
        raise InterruptedError("Listing cancelled")
    if returncode != 0 and not entries:
        raise RuntimeError(
            "yt-dlp listing failed (code {}): {}".format(returncode, " ".join(stderr_tail[-3:]))
        )

    return entries


@dataclass
class YtDlpEntry:
    id: str
    url: str
    title: str
    category: str
    destination: str
    parent: str = ""
    format_mode: str = "original"
    status: str = STATUS_QUEUED
    progress_pct: float = 0.0
    speed: str = ""
    eta: str = ""
    filepath: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id, "url": self.url, "title": self.title,
            "category": self.category, "destination": self.destination,
            "parent": self.parent, "format_mode": self.format_mode,
            "status": self.status, "filepath": self.filepath, "error": self.error,
        }

    @staticmethod
    def from_dict(data: dict) -> "YtDlpEntry":
        status = data.get("status", STATUS_QUEUED)
        if status == STATUS_DOWNLOADING:
            status = STATUS_PAUSED
        return YtDlpEntry(
            id=data.get("id") or uuid.uuid4().hex,
            url=data.get("url", ""),
            title=data.get("title", ""),
            category=data.get("category", CATEGORY_OTHER),
            destination=data.get("destination", ""),
            parent=data.get("parent", ""),
            format_mode=data.get("format_mode", "original"),
            status=status,
            filepath=data.get("filepath", ""),
            error=data.get("error", ""),
        )


class YtDlpDownloadEngine:
    """Sequential download queue over one worker thread."""

    def __init__(self, persist_path: str, poll_interval: float = 0.2):
        self._persist_path = persist_path
        self._poll_interval = poll_interval
        self._entries: dict[str, YtDlpEntry] = {}
        self._order: list[str] = []
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._stop_requested = threading.Event()
        self._worker: Optional[threading.Thread] = None
        self._current_process: Optional[subprocess.Popen] = None

        self.on_queue_changed: Callable[[], None] = lambda: None
        self.on_entry_updated: Callable[[YtDlpEntry], None] = lambda entry: None
        self.on_log_line: Callable[[str], None] = lambda line: None

        self._restore()

    def start(self):
        if self._worker is not None and self._worker.is_alive():
            return
        self._stop_requested.clear()
        self._worker = threading.Thread(target=self._run, daemon=True, name="YtDlpDownloadWorker")
        self._worker.start()

    def shutdown(self):
        self._stop_requested.set()
        self._wake.set()
        self._pause_current()
        worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=3.0)

    def _restore(self):
        try:
            with open(self._persist_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for item in data.get("entries", []):
                entry = YtDlpEntry.from_dict(item)
                self._entries[entry.id] = entry
                self._order.append(entry.id)
        except FileNotFoundError:
            pass
        except Exception:
            logger.warning("Could not restore yt-dlp download state", exc_info=True)

    def _persist(self):
        try:
            os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
            with open(self._persist_path, "w", encoding="utf-8") as fh:
                json.dump({"entries": [self._entries[eid].to_dict() for eid in self._order]}, fh, indent=1)
        except Exception:
            logger.warning("Could not persist yt-dlp download state", exc_info=True)

    def add_entry(self, url: str, title: str, category: str, destination: str,
                  parent: str = "", format_mode: str = "original") -> YtDlpEntry:
        with self._lock:
            entry = YtDlpEntry(
                id=uuid.uuid4().hex, url=url, title=title, category=category,
                destination=destination, parent=parent, format_mode=format_mode,
            )
            self._entries[entry.id] = entry
            self._order.append(entry.id)
            self._persist()
        self.on_queue_changed()
        self._wake.set()
        return entry

    def set_title(self, entry_id: str, title: str):
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                return
            entry.title = title
            self._persist()
        self.on_entry_updated(entry)
        self.on_queue_changed()

    def pause(self, entry_id: str):
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                return
            if entry.status == STATUS_DOWNLOADING:
                self._pause_current()
                entry.status = STATUS_PAUSED
            elif entry.status == STATUS_QUEUED:
                entry.status = STATUS_PAUSED
            self._persist()
        self.on_entry_updated(entry)
        self.on_queue_changed()

    def resume(self, entry_id: str):
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None or entry.status not in (STATUS_PAUSED, STATUS_FAILED):
                return
            entry.status = STATUS_QUEUED
            entry.error = ""
            self._persist()
        self.on_entry_updated(entry)
        self.on_queue_changed()
        self._wake.set()

    def remove(self, entry_id: str):
        with self._lock:
            entry = self._entries.pop(entry_id, None)
            if entry is None:
                return
            self._order.remove(entry_id)
            if entry.status == STATUS_DOWNLOADING:
                self._pause_current()
            self._persist()
        self.on_queue_changed()

    def pause_all(self):
        with self._lock:
            for entry in self._entries.values():
                if entry.status == STATUS_QUEUED:
                    entry.status = STATUS_PAUSED
                    self.on_entry_updated(entry)
            downloading = any(e.status == STATUS_DOWNLOADING for e in self._entries.values())
            self._persist()
        if downloading:
            self._pause_current()
        self.on_queue_changed()

    def _pause_current(self):
        process = self._current_process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except Exception:
                pass

    def get_entries(self, category: Optional[str] = None) -> list:
        with self._lock:
            entries = [self._entries[eid] for eid in self._order]
        if category is None:
            return list(entries)
        return [e for e in entries if e.category == category]

    def get_entry(self, entry_id: str) -> Optional[YtDlpEntry]:
        with self._lock:
            return self._entries.get(entry_id)

    def _next_queued(self) -> Optional[YtDlpEntry]:
        with self._lock:
            for eid in self._order:
                entry = self._entries[eid]
                if entry.status == STATUS_QUEUED:
                    return entry
        return None

    def _run(self):
        while not self._stop_requested.is_set():
            entry = self._next_queued()
            if entry is None:
                self._wake.wait(timeout=1.0)
                self._wake.clear()
                continue
            self._download(entry)

    def _build_command(self, entry: YtDlpEntry) -> list:
        binary = find_ytdlp_binary()
        output_template = os.path.join(entry.destination, "%(title)s [%(id)s].%(ext)s")
        cmd = [
            binary, "--newline", "--no-warnings", "--no-playlist",
            "--continue", "--retries", "3",
            "-o", output_template,
        ]
        if entry.format_mode == "audio":
            cmd.extend(["-x", "--audio-format", "mp3", "--audio-quality", "0"])
        elif entry.format_mode == "video":
            cmd.extend(["-f", "bestvideo*+bestaudio/best"])
        cmd.extend(_ffmpeg_location_args())
        cmd.extend(_deno_args())
        cmd.extend(_cookies_args())
        cmd.append(entry.url)
        return cmd

    def _download(self, entry: YtDlpEntry):
        binary = find_ytdlp_binary()
        if not binary:
            entry.status = STATUS_FAILED
            entry.error = "yt-dlp executable was not found."
            self.on_entry_updated(entry)
            self.on_queue_changed()
            return

        os.makedirs(entry.destination, exist_ok=True)
        with self._lock:
            entry.status = STATUS_DOWNLOADING
            entry.progress_pct = 0.0
            entry.error = ""
            self._persist()
        self.on_entry_updated(entry)
        self.on_queue_changed()
        self.on_log_line(f"$ {' '.join(self._build_command(entry))}")

        try:
            process = subprocess.Popen(
                self._build_command(entry),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", **_NO_WINDOW,
            )
        except OSError as exc:
            entry.status = STATUS_FAILED
            entry.error = str(exc)
            self.on_entry_updated(entry)
            self.on_queue_changed()
            return

        self._current_process = process
        try:
            assert process.stdout is not None
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                self.on_log_line(line)
                self._parse_progress(entry, line)
        finally:
            returncode = process.wait()
            self._current_process = None

        with self._lock:
            if self._stop_requested.is_set():
                entry.status = STATUS_PAUSED
            elif returncode == 0:
                entry.status = STATUS_COMPLETED
                entry.progress_pct = 100.0
                entry.filepath = self._locate_output(entry)
            else:
                entry.status = STATUS_PAUSED
                entry.error = f"yt-dlp exited with code {returncode} (paused; resume to retry)"
            self._persist()
        self.on_entry_updated(entry)
        self.on_queue_changed()

    def _parse_progress(self, entry: YtDlpEntry, line: str):
        match = _PROGRESS_RE.search(line)
        if match:
            entry.progress_pct = float(match.group("pct"))
            entry.speed = match.group("speed") or ""
            entry.eta = match.group("eta") or ""
            self.on_entry_updated(entry)
            return
        match = _DESTINATION_RE.search(line) or _MERGER_RE.search(line)
        if match:
            entry.filepath = match.group("path").strip()
            self.on_entry_updated(entry)
            return
        match = _ALREADY_RE.search(line)
        if match:
            entry.filepath = match.group("path").strip()
            self.on_entry_updated(entry)

    def _locate_output(self, entry: YtDlpEntry) -> str:
        if entry.filepath and os.path.isfile(entry.filepath):
            return entry.filepath
        try:
            candidates = [f for f in os.listdir(entry.destination) if f"[{entry.url.split('v=')[-1]}]" in f]
            if candidates:
                return os.path.join(entry.destination, candidates[0])
        except OSError:
            pass
        return entry.filepath

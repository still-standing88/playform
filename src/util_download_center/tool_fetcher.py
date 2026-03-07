import json
import platform as _platform_mod

from PySide6.QtCore import QObject, Signal, QUrl, Slot
from PySide6.QtNetwork import (
    QNetworkAccessManager, QNetworkRequest, QNetworkReply,
)

from .tool_registry import ToolDef, current_machine


def _current_platform() -> str:
    s = _platform_mod.system().lower()
    return "macos" if s == "darwin" else ("windows" if s == "windows" else "linux")


class ToolFetcher(QObject):

    links_ready = Signal(list)
    fetch_error = Signal(str, str)
    all_done    = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._platform = _current_platform()
        self._arch     = current_machine()
        self._results: list[dict]        = []
        self._errors:  list[tuple]       = []
        self._active:  int               = 0
        self._nam = QNetworkAccessManager(self)

    def fetch(self, tools: list[ToolDef]):
        self._results = []
        self._errors  = []
        self._active  = len(tools)
        if not tools:
            self.all_done.emit([])
            return
        for tool in tools:
            self._fetch_one(tool)

    def _fetch_one(self, tool: ToolDef):
        url = f"https://api.github.com/repos/{tool.github_repo}/releases/latest"
        req = QNetworkRequest(QUrl(url))
        req.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, "PlayForm")
        req.setRawHeader(b"Accept", b"application/vnd.github+json")
        reply = self._nam.get(req)
        reply.finished.connect(lambda: self._on_reply(reply, tool))

    def _on_reply(self, reply: QNetworkReply, tool: ToolDef):
        try:
            raw  = bytes(reply.readAll()).decode("utf-8", errors="replace")
            release = {}
            if raw:
                try:
                    release = json.loads(raw)
                except json.JSONDecodeError:
                    pass

            if reply.error() != QNetworkReply.NetworkError.NoError:
                self._emit_error(tool, reply.errorString())
                return

            assets        = release.get("assets", [])
            pattern_map   = tool.asset_patterns.get(self._platform, {})
            target        = pattern_map.get(self._arch) or next(iter(pattern_map.values()), None)

            if not target:
                self._emit_error(
                    tool,
                    f"No asset pattern defined for {self._platform}/{self._arch}",
                )
                return

            asset = next((a for a in assets if a["name"] == target), None)
            if asset is None:
                asset = next((a for a in assets if target in a["name"]), None)

            if asset is None:
                self._emit_error(
                    tool,
                    f"Asset '{target}' not found in release {release.get('tag_name', '')}",
                )
                return

            result = {
                "tool_name": tool.name,
                "url":       asset["browser_download_url"],
                "filename":  asset["name"],
                "tool":      tool,
            }
            self._results.append(result)
            self.links_ready.emit([result])

        except Exception as exc:
            self._emit_error(tool, str(exc))

        finally:
            reply.deleteLater()
            self._active -= 1
            if self._active == 0:
                self.all_done.emit(list(self._results))

    def _emit_error(self, tool: ToolDef, msg: str):
        self._errors.append((tool.name, msg))
        self.fetch_error.emit(tool.name, msg)

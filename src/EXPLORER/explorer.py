import os, string
import time, datetime as dt

from enum import Enum
from dataclasses import dataclass
from recursive_size import get_size
from hurry.filesize import size as sz


class PathType(Enum):
    FILE = "file"
    FOLDER = "folder"
    UNKNOWN = "UNKNOWN"

class ExplorerMode(Enum):
    NORMAL = "normal"
    SEARCH_RESULTS = "search_results"
    SEARCH_DERIVED_BROWSE = "search_derived_browse"

class PathInfo:

    @staticmethod
    def get_path_type(path: str) -> PathType:
        return PathType.FOLDER if os.path.isdir(path) else (PathType.FILE if os.path.isfile(path) else PathType.UNKNOWN)

    @staticmethod
    def get_modified_date(path):
        try:
            return dt.date.fromtimestamp(os.path.getmtime(path))
        except (OSError, ValueError, OverflowError):
            return None

    def __init__(self, path):
        self.path: str = path
        self.name: str = os.path.basename(self.path)
        self.type: PathType = self.get_path_type(self.path)
        self.ext: str = os.path.splitext(self.path)[1] if self.type == PathType.FILE else "file folder"
        self.modify_date = self.get_modified_date(self.path)
        try:
            self.size: str = f"{sz(get_size(self.path))}b" if self.type == PathType.FILE else "0"
        except (OSError, ValueError):
            self.size: str = "0"

@dataclass
class PathItem:
    path: str
    type: PathType
    info: PathInfo

class Explorer:
    __drives = []
    default_path = os.path.expanduser("~")
    _sort_mode = "name_asc"

    @staticmethod
    def get_current(): return os.getcwd()

    @staticmethod
    def get_root(path): return os.path.dirname(path)

    @staticmethod
    def list_drives():
        if os.name == "nt":
            return [f"{letter}:" for letter in string.ascii_uppercase if os.path.exists(f"{letter}:\\")]
        return [os.path.sep]

    @staticmethod
    def _is_windows_drive_root(path: str) -> bool:
        normalized = os.path.normpath(path)
        drive, tail = os.path.splitdrive(normalized)
        return os.name == "nt" and bool(drive) and tail in ("\\", "/")

    def __init__(self, file_extensions=None, sort_mode: str = "name_asc"):
        self._file_extensions = [ext.lower() for ext in file_extensions] if file_extensions is not None else []
        self._sort_mode = sort_mode
        self._current_path = self.get_current()
        self._root_path = self.get_root(self._current_path)
        self._prev_path = self._current_path
        self.items = {}
        self.folders = []
        self.files = []

        self.mode = ExplorerMode.NORMAL
        self._pre_search_path = None
        self._search_query = None
        self.search_results: list[PathItem] = []
        self.last_navigation_error: "str | None" = None

        self.__retrieve_listing()

    @property
    def current_path(self) -> str:
        return self._current_path

    @current_path.setter
    def current_path(self, value: str):
        self.set_current_path(value)

    @property
    def root_path(self):
        return self._root_path

    @property
    def search_query(self) -> "str | None":
        return self._search_query

    @property
    def file_extensions(self):
        return self._file_extensions

    def get_prev_path(self): return self._prev_path

    def set_default_path(self, path): self.default_path = path

    def set_sort(self, mode: str):
        self._sort_mode = mode
        self.__retrieve_listing()

    def get_current_path(self): return self._current_path

    def set_current_path(self, path):
        # Windows resolves a bare drive letter like "I:" (no trailing
        # separator) via a hidden per-drive cwd, so os.path.exists("I:")
        # passes -- but os.path.join("I:", "sub") == "I:sub" (no
        # separator inserted), silently corrupting every path built under
        # it from then on. mpv, unlike Windows, doesn't resolve that
        # drive-relative form and fails to open the file. abspath()
        # normalizes it to "I:\\" up front.
        normalized = os.path.abspath(path) if path else path
        if normalized and os.path.exists(normalized):
            self._current_path = normalized
        else:
            self._current_path = self.default_path
        self._root_path = self.get_root(self._current_path)
        self._prev_path = self._current_path
        self.__retrieve_listing()

    def forward(self, path):
        # Opening a folder while viewing search results starts a "derived
        # browse" - normal navigation from here on, but backward() will jump
        # straight back to the search results rather than stepping up one
        # real directory level at a time.
        if self.mode == ExplorerMode.SEARCH_RESULTS:
            self.mode = ExplorerMode.SEARCH_DERIVED_BROWSE

        if self._current_path == "drives" and path in self.items:
            self._current_path = self.items[path].path
        elif ((path in self.items and os.path.exists(path)) or
            (path in self.items and os.path.exists(os.path.join(self._current_path, path))) or
            os.path.exists(path)):
            if path in self.items:
                self._current_path = self.items[path].path
            else:
                self._current_path = path
        else:
            self._current_path = self.default_path
        self._root_path = self.get_root(self._current_path)
        self._prev_path = self._current_path
        self.__retrieve_listing()

    def backward(self):
        if self.mode == ExplorerMode.SEARCH_DERIVED_BROWSE:
            # No matter how many real subfolders deep, back always returns
            # directly to the stored search results - not a normal
            # step-up-one-level.
            self.mode = ExplorerMode.SEARCH_RESULTS
            self._current_path = self._pre_search_path
            self._root_path = self.get_root(self._current_path)
            return

        if self.mode == ExplorerMode.SEARCH_RESULTS:
            self.mode = ExplorerMode.NORMAL
            self._current_path = self._pre_search_path
            self._root_path = self.get_root(self._current_path)
            self._pre_search_path = None
            self._search_query = None
            self.search_results = []
            self.__retrieve_listing()
            return

        normalized = os.path.normpath(self._current_path)
        if self._is_windows_drive_root(normalized):
            self._prev_path = self._current_path
            self._current_path = "drives"
            self._root_path = "drives"
        elif os.path.exists(self.current_path) and os.path.exists(self._root_path):
            self._prev_path = self._current_path
            self._current_path = self._root_path
        else:
            self._current_path = self.default_path
            self._prev_path = self._current_path
        if self._current_path != "drives":
            self._root_path = self.get_root(self._current_path)
        self.__retrieve_listing()

    def begin_search(self, query: str, media_db=None) -> tuple:
        """Record search state without performing the (potentially slow)
        lookup itself - the caller runs the actual search off the UI thread
        and reports back through apply_search_results(). Returns
        (root_path, use_db) for the caller to act on."""
        if self.mode == ExplorerMode.NORMAL:
            self._pre_search_path = self._current_path

        self._search_query = query
        root_path = self._pre_search_path

        use_db = False
        if media_db is not None:
            try:
                use_db = media_db.is_path_cataloged(root_path)
            except Exception:
                use_db = False

        return root_path, use_db

    def apply_search_results(self, paths: list) -> None:
        """Called once a background search (started via begin_search) has
        produced its raw file-path results."""
        results = []
        for path in paths:
            try:
                results.append(PathItem(path=path, type=PathType.FILE, info=PathInfo(path)))
            except (OSError, ValueError):
                continue
        self.search_results = results
        self.mode = ExplorerMode.SEARCH_RESULTS
        self._current_path = self._pre_search_path

    def __retrieve_listing(self):
        self.folders.clear()
        self.files.clear()
        self.items.clear()
        self.last_navigation_error = None

        if self._current_path == "drives":
            drives = self.list_drives()
            for drive in drives:
                drive_path = drive + "\\" if os.name == "nt" else drive
                try:
                    self.items[drive] = PathItem(path=drive_path, type=PathType.FOLDER, info=PathInfo(drive_path))
                    self.folders.append(drive)
                except (OSError, ValueError):
                    continue
        else:
            try:
                contents = os.listdir(self._current_path)
            except (PermissionError, FileNotFoundError, OSError) as e:
                failed_path = self._current_path
                self._current_path = self.default_path
                self._root_path = self.get_root(self._current_path)
                try:
                    contents = os.listdir(self._current_path)
                    self.last_navigation_error = f"{failed_path}: {e.strerror or e}"
                except (PermissionError, FileNotFoundError, OSError):
                    self.last_navigation_error = f"{failed_path}: {e.strerror or e}"
                    return
            for item in contents:
                item_path = os.path.join(self._current_path, item)
                try:
                    if os.path.isdir(item_path):
                        self.items[item] = PathItem(path=item_path, type=PathType.FOLDER, info=PathInfo(item_path))
                        self.folders.append(item)
                    elif os.path.isfile(item_path) and os.path.splitext(item_path)[1].lower() in self._file_extensions:
                        self.items[item] = PathItem(path=item_path, type=PathType.FILE, info=PathInfo(item_path))
                        self.files.append(item)
                except (PermissionError, OSError):
                    continue

        if self._sort_mode in ("date_newest", "date_oldest"):
            rev = self._sort_mode == "date_newest"
            _fallback = dt.date.min
            self.folders.sort(key=lambda x: self.items[x].info.modify_date or _fallback, reverse=rev)
            self.files.sort(key=lambda x: self.items[x].info.modify_date or _fallback, reverse=rev)
        else:
            rev = self._sort_mode == "name_desc"
            self.folders.sort(key=lambda x: x.lower(), reverse=rev)
            self.files.sort(key=lambda x: x.lower(), reverse=rev)

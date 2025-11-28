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

class PathInfo:

    @staticmethod
    def get_path_type(path: str) -> PathType:
        return PathType.FOLDER if os.path.isdir(path) else (PathType.FILE if os.path.isfile(path) else PathType.UNKNOWN)

    @staticmethod
    def get_modified_date(path):
        modify_date = os.path.getmtime(path)
        return dt.date.fromtimestamp(os.path.getmtime(path))

    def __init__(self, path):
        self.path: str = path
        self.name: str = os.path.basename(self.path)
        self.type: PathType = self.get_path_type(self.path)
        self.ext: str = os.path.splitext(self.path)[1] if self.type == PathType.FILE else "file folder"
        self.modify_date:dt.date = self.get_modified_date(self.path)
        self.size: str = f"{sz(get_size(self.path))}b" if self.type == PathType.FILE else "0"

@dataclass
class PathItem:
    path: str
    type: PathType
    info: PathInfo

class Explorer:
    __drives = []
    default_path = os.path.expanduser("~")

    @staticmethod
    def get_current(): return os.getcwd()

    @staticmethod
    def get_root(path): return os.path.dirname(path)

    @staticmethod
    def list_drives():
        return [f"{letter}:" for letter in string.ascii_uppercase if os.path.exists(f"{letter}:")]

    def __init__(self, file_extensions=[]):
        self._file_extensions = file_extensions
        self._current_path = self.get_current()
        self._root_path = self.get_root(self._current_path)
        self.items = {}
        self.folders = []
        self.files = []
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

    def get_prev_path(self): return self.root_path

    def set_default_path(self, path): self.default_path = path

    def get_current_path(self): return self._current_path

    def set_current_path(self, path):
        if os.path.exists(path):
            self._current_path = path
        else:
            self._current_path = self.default_path
        self._root_path = self.get_root(self._current_path)
        self._prev_path = self._current_path
        self.__retrieve_listing()

    def forward(self, path):
        if self._current_path == "drives" and path in self.items:
            self._current_path = self.items[path].path
        elif ((path in self.items and os.path.exists(path)) or
            (path in self.items and os.path.exists(f"{self._current_path}/{path}")) or
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
        if len(self._current_path) <= 3 and self._current_path.endswith(":\\"):
            self._prev_path = self._current_path
            self._current_path = "drives"
            self._root_path = "drives"
        elif os.path.exists(self.current_path) and os.path.exists(self._root_path):
            self._prev_path = self._current_path
            self._current_path = self._root_path
        else:
            self._current_path = self.default_path
            self._prev_path = self._current_path
        self._root_path = self.get_root(self._current_path)
        self.__retrieve_listing()

    def __retrieve_listing(self):
        self.folders.clear()
        self.files.clear()
        self.items.clear()
        
        if self._current_path == "drives":
            drives = self.list_drives()
            for drive in drives:
                self.items[drive] = PathItem(path=drive + "\\", type=PathType.FOLDER, info=PathInfo(drive + "\\"))
                self.folders.append(drive)
        else:
            contents = os.listdir(self._current_path)
            for item in contents:
                item_path = os.path.join(self._current_path, item)
                if os.path.isdir(item_path):
                    self.items[item] = PathItem(path=item_path, type=PathType.FOLDER, info=PathInfo(item_path))
                    self.folders.append(item)
                elif os.path.isfile(item_path) and os.path.splitext(item_path)[1] in self._file_extensions:
                    self.items[item] = PathItem(path=item_path, type=PathType.FILE, info=PathInfo(item_path))
                    self.files.append(item)

from enum import Enum, auto
from typing import Union, Any
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from validators import url, ValidationError


ParameterValue = Union[int, float, bool, str]
formats:dict[str, list[str]] = {
       "audio": ["mp1", "mp2", "mp3", "ogg", "wav", "m4a", "aac", "flac", "wma", "aif", "wv"],
       "video": ["flv", "rm", "3gp", "mp4", "mkv", "mov", "wmv", "mpeg", "avi", "webm"]
}

format_descriptions: dict[str, dict[str, str]] = {
    "audio": {
        "mp1": "MPEG Audio Layer 1",
        "mp2": "MPEG Audio Layer 2",
        "mp3": "MPEG Audio Layer 3",
        "ogg": "Ogg Vorbis Audio Container",
        "wav": "Waveform Audio File Format",
        "m4a": "MPEG-4 Audio (often AAC)",
        "aac": "Advanced Audio Coding",
        "flac": "Free Lossless Audio Codec",
        "wma": "Windows Media Audio",
        "aif": "Audio Interchange File Format",
        "wv":  "WavPack Lossless Audio",
    },
    "video": {
        "flv": "Flash Video",
        "rm":  "RealMedia",
        "3gp": "3rd Generation Partnership Project ",
        "mp4": "MPEG-4 Part 14 Video Container",
        "mkv": "Matroska Multimedia Container",
        "mov": "Apple QuickTime Movie",
        "wmv": "Windows Media Video",
        "mpeg": "Moving Picture Experts Group Video (MPEG-1/MPEG-2)",
        "avi": "Audio Video Interleave",
        "webm": "WebM Video Format (VP8/VP9/AV1 Video, Vorbis/Opus Audio)"
    }
}

class AVErrorInfo(Enum):
      UNKNOWN_ERROR = -1
      INITIALIZATION_ERROR = 0
      FILE_NOTFOUND = 1
      UNSUPPORTED_FORMAT = 2
      INVALID_HANDLE = 3
      HTTP_ERROR = 4
      INVALID_MEDIA_FILTER = 5
      INVALID_FILTER_PARAMETER = 6
      INVALID_FILTER_PARAMETER_TYPE = 7
      INVALID_FILTER_PARAMETER_VALUE = 8
      INVALID_FILTER_PARAMETER_RANGE = 9
      UNINITIALIZED = 10
      NET_ERROR = 11

class AVPlaybackState(Enum):
    AV_STATE_NOTHING = -1
    AV_STATE_STOPPED = 0
    AV_STATE_PLAYING = 1
    AV_STATE_PAUSED = 2
    AV_STATE_BUFFERING = 3
    AV_STATE_LOADING = 4

class AVPlaylistMode(Enum):
    SEQUENTIAL = auto()
    REPEAT_ALL = auto()
    REPEAT_ONE = auto()
    SHUFFLE = auto()

class AVPlaylistState(Enum):
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()
    FINISHED = auto()

class AVMuteState(Enum):
                  AV_AUDIO_MUTED = -1
                  AV_AUDIO_UNMUTED = 1

class AVMediaType(Enum):
        AV_TYPE_AUDIO = "audio"
        AV_TYPE_VIDEO = "video"

class AVMediaBackend(Enum):
        AV_BACKEND_FMOD = "fmod"
        AV_BACKEND_MPV = "mpv"
        AV_BACKEND_VLC = "vlc"

class AVMediaSource(Enum):
      AV_SRC_FILE = 1
      AV_SRC_URL = 2
      AV_SRC_NOT_SET = 3

@dataclass
class AVDevice:
        media_backend:AVMediaBackend
        name: str


class AVError(Exception):
      

      def __init__(self, info:AVErrorInfo, message:str|None = None) -> None:
            self.info = info
            self.message = message
            super().__init__(message if message is not None else f"Info: {info}")

AVFilterType = AVMediaType

class AVFilter:
    
    def __init__(self, filter_type: AVFilterType, media_backend: AVMediaBackend,
                 filter_handle: str, parameters: dict[str, ParameterValue], backend_additional_info: dict[Any, Any]):
        self.__type = filter_type
        self.__backend:AVMediaBackend = media_backend
        self.__handle:str = filter_handle
        self.__parameters:dict[str, ParameterValue] = parameters
        self.__info:dict[Any, Any] = backend_additional_info


    @property
    def type(self):
           return self.__type

    @property
    def backend(self):
           return self.__backend

    @property
    def handle(self):
           return self.__handle

    @property
    def info(self):
           return self.__info



    def get_parameters(self):
            return self.__parameters

    def set_parameters(self, parameters: dict[str, ParameterValue] = {}):
            self.__parameters.update(parameters)

    def get_parameter(self, name: str) -> ParameterValue | None:
        if self.__parameters.__contains__(name):
           return self.__parameters[name]
        return None

    def set_parameter(self, name: str, value: ParameterValue):
            if name in self.__parameters:
                    self.__parameters[name] = value


def is_url(url_string: str, default_scheme: str = "https") -> bool:
    if not isinstance(url_string, str):
        return False
    original_trimmed = url_string.strip()
    if not original_trimmed:
        return False

    if default_scheme not in ("http", "https"):
        default_scheme = "https"
    url_to_validate = original_trimmed
    parsed = urlparse(original_trimmed)
    if not parsed.scheme:
        if original_trimmed.startswith('//'):
            url_to_validate = f"{default_scheme}:{original_trimmed}"
        else:
            potential_host = parsed.path.split('/')[0]
            if '.' in original_trimmed or 'localhost' in potential_host.lower():
                 url_to_validate = f"{default_scheme}://{original_trimmed}"
            else:
                 return False

    try:
        result = url(url_to_validate)
        return bool(result)
    except ValidationError:
        return False
    except Exception:
        return False
       

def is_path(path_str:str) -> bool:
    if not isinstance(path_str, str) or path_str == "":
        return False
    try:
        path = Path(path_str)
        return True
    except:
          return False

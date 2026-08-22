import os

from .media_info import MediaInfo
from .playlist import *
#from .playlist import PlaylistManager, PlaylistParser, Playlist, PlaylistFormat, PlaylistEntry
from .__AV_Common import *
from .__AV_Instance import AVMediaInstance
from .audio_filter import AudioFilter
from .video_filter import VideoFilter
from .__utils import find_lib_path

mpv_lib_path = os.environ.get("MPV_LIB_PATH", None)

if mpv_lib_path and os.path.exists(mpv_lib_path):
    os.environ["PATH"] += os.path.abspath(mpv_lib_path) + os.pathsep


_MPV_LAZY_NAMES = (
    "MPVVideoPlayer", "VideoPlayer",
    "MPVAudioFilter", "MPVBandPassFilter", "MPVChorusFilter", "MPVCompressorFilter",
    "MPVEchoFilter", "MPVFlangerFilter", "MPVGateFilter", "MPVHighPassFilter",
    "MPVLimiterFilter", "MPVLowPassFilter", "MPVPitchShiftFilter", "MPVEqualizerFilter",
)


def _load_mpv_backend():
    try:
        from .mpv_video_player import MPVVideoPlayer
        from . import mpv_audio_filter
    except Exception as e:
        raise RuntimeError(f"Error initializing MPV.\nDetails: {str(e)}")
    resolved = {"MPVVideoPlayer": MPVVideoPlayer, "VideoPlayer": MPVVideoPlayer}
    for name in _MPV_LAZY_NAMES:
        if name not in resolved:
            resolved[name] = getattr(mpv_audio_filter, name)
    globals().update(resolved)
    return resolved


def __getattr__(name):
    if name in _MPV_LAZY_NAMES:
        return _load_mpv_backend()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


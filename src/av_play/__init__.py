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

try:
    from .mpv_video_player import MPVVideoPlayer
    from .mpv_audio_filter import (MPVAudioFilter, MPVBandPassFilter, MPVChorusFilter, MPVCompressorFilter,
                                   MPVEchoFilter, MPVFlangerFilter, MPVGateFilter, MPVHighPassFilter,
                                   MPVLimiterFilter, MPVLowPassFilter, MPVPitchShiftFilter, MPVEqualizerFilter
                                   )
    VideoPlayer = MPVVideoPlayer
except Exception as e:
    raise RuntimeError(f"Error initializing MPV.\nDetails: {str(e)}")


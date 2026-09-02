import os
from media_core.ffmpeg import FFmpeg
from media_core.ffmpeg.asyncio import FFmpeg as AsyncFFmpeg

from utilities.functions import get_parent_dir
from player.util.utilities import resolve_ffmpeg_binary_path
from app_config import prefs

class FFmpegHandler:
    _ffmpeg_path: str | None = None
    _ffprobe_path: str | None = None
    _errors: list = []

    @staticmethod
    def reset():
        """Drop the cached resolution so the next call re-reads prefs. Called
        when the FFmpeg Path pref changes, otherwise every ffmpeg-backed tool
        keeps using the old binary until restart."""
        FFmpegHandler._ffmpeg_path = None
        FFmpegHandler._ffprobe_path = None
        FFmpegHandler._errors.clear()

    @staticmethod
    def get_ffmpeg_binary():
        if FFmpegHandler._ffmpeg_path is not None:
            return FFmpegHandler._ffmpeg_path, FFmpegHandler._ffprobe_path

        ffmpeg_exe_name = 'ffmpeg' + ('.exe' if os.name == 'nt' else '')
        ffprobe_exe_name = 'ffprobe' + ('.exe' if os.name == 'nt' else '')

        # The pref takes priority over the bundled bin dir; a user who points
        # this at their own build expects that build to be used.
        pref_dir = str(prefs.prefs.get('ffmpeg_path', '') or '')
        bin_dir = os.path.join(get_parent_dir(), 'bin')
        for directory in (pref_dir, bin_dir):
            if not directory:
                continue
            ffmpeg_candidate = os.path.join(directory, ffmpeg_exe_name)
            if os.path.isfile(ffmpeg_candidate):
                ffprobe_candidate = os.path.join(directory, ffprobe_exe_name)
                FFmpegHandler._ffmpeg_path = ffmpeg_candidate
                FFmpegHandler._ffprobe_path = ffprobe_candidate if os.path.isfile(ffprobe_candidate) else None
                return FFmpegHandler._ffmpeg_path, FFmpegHandler._ffprobe_path

        found_ffmpeg = resolve_ffmpeg_binary_path()
        if found_ffmpeg and os.path.exists(found_ffmpeg):
            FFmpegHandler._ffmpeg_path = found_ffmpeg
            ffprobe_candidate = os.path.join(os.path.dirname(found_ffmpeg), ffprobe_exe_name)
            FFmpegHandler._ffprobe_path = ffprobe_candidate if os.path.exists(ffprobe_candidate) else None
            return FFmpegHandler._ffmpeg_path, FFmpegHandler._ffprobe_path

        FFmpegHandler._errors.append("FFmpeg not found in system PATH or preferences")
        FFmpegHandler._ffmpeg_path = "ffmpeg"
        FFmpegHandler._ffprobe_path = "ffprobe"
        return FFmpegHandler._ffmpeg_path, FFmpegHandler._ffprobe_path

    @staticmethod
    def create_ffmpeg_instance():
        ffmpeg_path, _ = FFmpegHandler.get_ffmpeg_binary()
        return FFmpeg(executable=str(ffmpeg_path))

    @staticmethod
    def create_ffprobe_instance():
        _, ffprobe_path = FFmpegHandler.get_ffmpeg_binary()
        if not ffprobe_path or not os.path.exists(ffprobe_path):
             return FFmpeg(executable="ffprobe")
        return FFmpeg(executable=str(ffprobe_path))

    @staticmethod
    def create_async_ffmpeg_instance():
        ffmpeg_path, _ = FFmpegHandler.get_ffmpeg_binary()
        return AsyncFFmpeg(executable=str(ffmpeg_path))

    @staticmethod
    def get_errors():
        return FFmpegHandler._errors.copy()
    
    @staticmethod
    def has_errors():
        return len(FFmpegHandler._errors) > 0

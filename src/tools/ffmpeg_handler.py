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
    def get_ffmpeg_binary():
        if FFmpegHandler._ffmpeg_path is not None:
            return FFmpegHandler._ffmpeg_path, FFmpegHandler._ffprobe_path

        base_dir = get_parent_dir()
        bin_dir = os.path.join(base_dir, 'bin')
        ffmpeg_exe_name = 'ffmpeg' + ('.exe' if os.name == 'nt' else '')
        ffprobe_exe_name = 'ffprobe' + ('.exe' if os.name == 'nt' else '')
        local_ffmpeg_path = os.path.join(bin_dir, ffmpeg_exe_name)
        local_ffprobe_path = os.path.join(bin_dir, ffprobe_exe_name)

        if not os.path.exists(local_ffmpeg_path):
            found_ffmpeg = resolve_ffmpeg_binary_path()
            
            if found_ffmpeg and os.path.exists(found_ffmpeg):
                FFmpegHandler._ffmpeg_path = found_ffmpeg
                ffprobe_dir = os.path.dirname(found_ffmpeg)
                ffprobe_candidate = os.path.join(ffprobe_dir, ffprobe_exe_name)
                FFmpegHandler._ffprobe_path = ffprobe_candidate if os.path.exists(ffprobe_candidate) else None
                return FFmpegHandler._ffmpeg_path, FFmpegHandler._ffprobe_path
            
            # Deprecated: FFmpeg is now installed via the Utility Download Center
            # instead of being unpacked from ffmpeg_binary.py / pyffmpeg here.
            # extracted_ffmpeg, extracted_ffprobe = extract_ffmpeg_from_pyffmpeg(bin_dir)
            #
            # if extracted_ffmpeg and os.path.exists(extracted_ffmpeg):
            #     FFmpegHandler._ffmpeg_path = extracted_ffmpeg
            #     FFmpegHandler._ffprobe_path = extracted_ffprobe
            #     return FFmpegHandler._ffmpeg_path, FFmpegHandler._ffprobe_path
            
            FFmpegHandler._errors.append("FFmpeg not found in system PATH or preferences")
            FFmpegHandler._ffmpeg_path = "ffmpeg"
            FFmpegHandler._ffprobe_path = "ffprobe"
            return FFmpegHandler._ffmpeg_path, FFmpegHandler._ffprobe_path

        FFmpegHandler._ffmpeg_path = local_ffmpeg_path
        FFmpegHandler._ffprobe_path = local_ffprobe_path
        
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

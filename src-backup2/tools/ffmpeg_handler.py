import os
import shutil
from pyffmpeg import FFmpeg as FFmpegDownloader
from ffmpeg import FFmpeg
from ffmpeg.asyncio import FFmpeg as AsyncFFmpeg

from utilities.functions import get_app_path

class FFmpegHandler:
    _ffmpeg_path: str | None = None
    _ffprobe_path: str | None = None

    @staticmethod
    def get_ffmpeg_binary():
        if FFmpegHandler._ffmpeg_path is not None:
            return FFmpegHandler._ffmpeg_path, FFmpegHandler._ffprobe_path


        base_dir = get_app_path()
        bin_dir = os.path.join(base_dir, 'bin')
        ffmpeg_exe_name = 'ffmpeg' + ('.exe' if os.name == 'nt' else '')
        ffprobe_exe_name = 'ffprobe' + ('.exe' if os.name == 'nt' else '')
        local_ffmpeg_path = os.path.join(bin_dir, ffmpeg_exe_name)
        local_ffprobe_path = os.path.join(bin_dir, ffprobe_exe_name)

        if not os.path.exists(local_ffmpeg_path):
            os.makedirs(bin_dir, exist_ok=True)
            
            try:
                downloader = FFmpegDownloader()
                temp_ffmpeg_path = downloader.get_ffmpeg_bin()
                shutil.copy2(temp_ffmpeg_path, local_ffmpeg_path)

                temp_dir = os.path.dirname(temp_ffmpeg_path)
                temp_ffprobe_path = os.path.join(temp_dir, ffprobe_exe_name)
                if os.path.exists(temp_ffprobe_path):
                    shutil.copy2(temp_ffprobe_path, local_ffprobe_path)

            except Exception as e:
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
import os
import shutil
from pyffmpeg import FFmpeg as FFmpegDownloader
from ffmpeg import FFmpeg
from ffmpeg.asyncio import FFmpeg as AsyncFFmpeg

class FFmpegHandler:
    _ffmpeg_path: str | None = None
    _ffprobe_path: str | None = None

    @staticmethod
    def get_ffmpeg_binary():
        if FFmpegHandler._ffmpeg_path is not None:
            return FFmpegHandler._ffmpeg_path, FFmpegHandler._ffprobe_path

        # Define the target local './bin' directory relative to this script file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        bin_dir = os.path.join(base_dir, 'bin')
        
        ffmpeg_exe_name = 'ffmpeg' + ('.exe' if os.name == 'nt' else '')
        ffprobe_exe_name = 'ffprobe' + ('.exe' if os.name == 'nt' else '')
        
        local_ffmpeg_path = os.path.join(bin_dir, ffmpeg_exe_name)
        local_ffprobe_path = os.path.join(bin_dir, ffprobe_exe_name)

        # If the local binary doesn't exist, extract and copy it.
        if not os.path.exists(local_ffmpeg_path):
            print("Local FFmpeg binary not found. Extracting from pyffmpeg...")
            os.makedirs(bin_dir, exist_ok=True)
            
            try:
                # Instantiating FFmpegDownloader extracts the binary to a temp location
                downloader = FFmpegDownloader()
                temp_ffmpeg_path = downloader.get_ffmpeg_bin()
                
                # Copy ffmpeg from temp location to our local ./bin directory
                shutil.copy2(temp_ffmpeg_path, local_ffmpeg_path)
                print(f"Copied ffmpeg to {local_ffmpeg_path}")

                # Attempt to find and copy ffprobe as well
                temp_dir = os.path.dirname(temp_ffmpeg_path)
                temp_ffprobe_path = os.path.join(temp_dir, ffprobe_exe_name)
                
                if os.path.exists(temp_ffprobe_path):
                    shutil.copy2(temp_ffprobe_path, local_ffprobe_path)
                    print(f"Copied ffprobe to {local_ffprobe_path}")
                
            except Exception as e:
                print(f"Could not automatically extract FFmpeg: {e}")
                # Fallback to assuming ffmpeg is in the system's PATH
                FFmpegHandler._ffmpeg_path = "ffmpeg"
                FFmpegHandler._ffprobe_path = "ffprobe"
                return FFmpegHandler._ffmpeg_path, FFmpegHandler._ffprobe_path

        # Set the handler's paths to our local binaries
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
        # Fallback if ffprobe wasn't found during extraction
        if not ffprobe_path or not os.path.exists(ffprobe_path):
             return FFmpeg(executable="ffprobe")
        return FFmpeg(executable=str(ffprobe_path))

    @staticmethod
    def create_async_ffmpeg_instance():
        ffmpeg_path, _ = FFmpegHandler.get_ffmpeg_binary()
        return AsyncFFmpeg(executable=str(ffmpeg_path))
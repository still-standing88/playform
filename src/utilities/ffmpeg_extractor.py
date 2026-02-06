import os
import shutil
from typing import Optional, Tuple

def extract_ffmpeg_from_pyffmpeg(target_dir: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        from ffmpeg_binary import FFmpegBin
        
        os.makedirs(target_dir, exist_ok=True)
        
        binary = FFmpegBin()
        binary.enable_log = False
        
        temp_ffmpeg_path = binary.get_ffmpeg_bin()
        
        if not temp_ffmpeg_path or not os.path.exists(temp_ffmpeg_path):
            return None, None
        
        temp_dir = os.path.dirname(temp_ffmpeg_path)
        
        ffmpeg_exe_name = 'ffmpeg' + ('.exe' if os.name == 'nt' else '')
        ffprobe_exe_name = 'ffprobe' + ('.exe' if os.name == 'nt' else '')
        
        local_ffmpeg_path = os.path.join(target_dir, ffmpeg_exe_name)
        local_ffprobe_path = os.path.join(target_dir, ffprobe_exe_name)
        
        shutil.copy2(temp_ffmpeg_path, local_ffmpeg_path)
        
        temp_ffprobe_path = os.path.join(temp_dir, ffprobe_exe_name)
        if os.path.exists(temp_ffprobe_path):
            shutil.copy2(temp_ffprobe_path, local_ffprobe_path)
        else:
            local_ffprobe_path = None
        
        binary.quit()
        del binary
        
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        
        return local_ffmpeg_path, local_ffprobe_path
        
    except ImportError:
        return None, None
    except Exception:
        return None, None

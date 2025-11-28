import os

def format_time(seconds: int) -> str:
    if not isinstance(seconds, (int, float)) or seconds < 0:
        seconds = 0
    
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    else:
        return f"{m:02d}:{s:02d}"

def seconds_to_microseconds(seconds: float) -> int:
    return int(seconds * 1_000_000)

def get_media_files_from_directory(directory: str, audio_formats: list, video_formats: list) -> list:
    media_files = []
    supported_exts = set(audio_formats + video_formats)
    
    try:
        for filename in sorted(os.listdir(directory)):
            ext = filename.split('.')[-1].lower()
            if ext in supported_exts:
                media_files.append(os.path.join(directory, filename))
    except (FileNotFoundError, PermissionError):
        pass
        
    return media_files
def get_common_sample_rates():
    return ["8000", "11025", "16000", "22050", "32000", "44100", "48000", "96000"]

def get_common_audio_bitrates():
    return ["64k", "96k", "128k", "192k", "256k", "320k"]

def get_common_video_bitrates():
    return ["500k", "1000k", "2000k", "4000k", "6000k", "8000k"]

def get_pcm_formats():
    return ["pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le"]

def get_audio_formats_map():
    return {
        "MP3": "libmp3lame",
        "AAC": "aac",
        "FLAC": "flac",
        "WAV": "pcm_s16le",
        "Opus": "libopus",
        "Vorbis": "libvorbis",
    }

def get_video_formats_map():
    return {
        "MP4 (H.264)": "libx264",
        "MKV (H.264)": "libx264",
        "WEBM (VP9)": "libvpx-vp9",
        "AVI (MPEG-4)": "mpeg4",
        "MOV (H.264)": "libx264",
    }

def get_container_from_format(format_name):
    containers = {
        "MP4 (H.264)": ".mp4",
        "MKV (H.264)": ".mkv",
        "WEBM (VP9)": ".webm",
        "AVI (MPEG-4)": ".avi",
        "MOV (H.264)": ".mov",
        "MP3": ".mp3",
        "AAC": ".aac",
        "FLAC": ".flac",
        "WAV": ".wav",
        "Opus": ".opus",
        "Vorbis": ".ogg",
    }
    return containers.get(format_name, "")
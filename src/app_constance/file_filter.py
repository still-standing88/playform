from utilities.formats import formats, format_descriptions

def build_media_file_filter(format_descriptions: dict[str, dict[str, str]]) -> str:
    filter_parts = []
    
    for category, formats in format_descriptions.items():
        for ext, description in formats.items():
            filter_parts.append(f"{description} (*.{ext})")
    
    audio_extensions = list(format_descriptions["audio"].keys())
    audio_pattern = " ".join(f"*.{ext}" for ext in audio_extensions)
    filter_parts.insert(0, f"{_('Audio Files')} ({audio_pattern})")

    video_extensions = list(format_descriptions["video"].keys())
    video_pattern = " ".join(f"*.{ext}" for ext in video_extensions)
    filter_parts.insert(1, f"{_('Video Files')} ({video_pattern})")

    all_extensions = []
    all_extensions.extend(format_descriptions["audio"].keys())
    all_extensions.extend(format_descriptions["video"].keys())
    all_pattern = " ".join(f"*.{ext}" for ext in all_extensions)
    filter_parts.insert(0, f"{_('Supported Media Files')} ({all_pattern})")

    filter_parts.append(_("All Files (*.*)"))
    
    return ";;".join(filter_parts)

file_filter = build_media_file_filter(format_descriptions)

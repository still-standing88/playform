import json

from ffmpeg.errors import FFmpegError
from tools.ffmpeg_handler import FFmpegHandler


def _run_ffprobe(path: str, *show_flags: str) -> dict:
    ffprobe = FFmpegHandler.create_ffprobe_instance()
    ffprobe.option("v", "quiet")
    ffprobe.option("print_format", "json")
    for flag in show_flags:
        ffprobe.option(flag)
    ffprobe.input(path)

    try:
        output = ffprobe.execute()
    except FFmpegError as e:
        raise ValueError(f"ffprobe failed for '{path}': {e}") from e

    if not output:
        return {}
    return json.loads(output)


def get_chapters(path: str) -> list[dict]:
    data = _run_ffprobe(path, "show_chapters")
    chapters = []
    for chapter in data.get("chapters", []):
        chapters.append({
            "start": float(chapter.get("start_time", 0.0)),
            "end": float(chapter.get("end_time", 0.0)),
            "title": chapter.get("tags", {}).get("title", ""),
        })
    return chapters


def get_media_metadata(path: str) -> dict:
    data = _run_ffprobe(path, "show_format", "show_streams")
    return {
        "format": data.get("format", {}),
        "streams": data.get("streams", []),
    }

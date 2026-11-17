import json
import os
import shutil
import subprocess
import sys

from .models import AUDIO_KINDS, CaptureDevice, MediaKind


PROCESS_OPTIONS = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
VIDEO_SOURCE = {
    MediaKind.CAMERA: ("camera", "--camera"),
    MediaKind.MONITOR: ("screen", "--monitor"),
    MediaKind.WINDOW: ("window", "--window"),
}
AUDIO_CODEC_LIMITS = {
    "m4a": {"aac"},
    "mp4": {"aac", "mp3", "opus", "flac", "pcm"},
    "flac": {"flac"},
    "mp3": {"mp3"},
    "opus": {"opus"},
    "webm": {"opus", "vorbis"},
    "wav": {"pcm", "mp3"},
}
VIDEO_CODEC_LIMITS = {"webm": {"vp9", "av1"}}


def escape_audio_id(value):
    return value.replace("%", "%25").replace(";", "%3B")


def find_mediacap(bin_dir=None):
    name = "MediaCap.exe" if sys.platform == "win32" else "MediaCap"
    if bin_dir is not None:
        bundled = os.path.join(bin_dir, name)
        if os.path.isfile(bundled):
            return bundled
    return shutil.which(name)


def query(executable, *args, allow_partial=False):
    if not executable:
        raise RuntimeError("MediaCap was not found. Install it in PlayForm's bin folder or on PATH.")
    try:
        result = subprocess.run(
            [executable, "--json", *args], stdin=subprocess.DEVNULL, capture_output=True,
            encoding="utf-8", errors="replace", timeout=25, **PROCESS_OPTIONS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("MediaCap did not respond in time.") from exc
    try:
        data = json.loads(result.stdout)
    except ValueError as exc:
        detail = result.stderr.strip() or result.stdout.strip() or str(result.returncode)
        raise RuntimeError(f"MediaCap query failed: {detail}") from exc
    if result.returncode and not (allow_partial and isinstance(data, dict) and "failed_lists" in data):
        message = data.get("message") if isinstance(data, dict) else None
        raise RuntimeError(message or result.stderr.strip() or f"MediaCap exited with code {result.returncode}")
    return data


def source_args(device: CaptureDevice, settings: dict, *, preview=False) -> list[str]:
    kind = device.kind
    if kind in AUDIO_KINDS:
        route = device.extra["route"]
        if "audio_id" in device.extra:
            route += f';device={escape_audio_id(device.extra["audio_id"])}'
        if kind == MediaKind.AUDIO_MIX:
            for key in ("mic", "system"):
                if device_id := settings.get(f"{key}_device"):
                    route += f";{key}-device={escape_audio_id(device_id)}"
                route += f";{key}-gain={settings.get(f'{key}_volume', 100) / 100}"
        rate = settings.get("sample_rate", 48000)
        channels = settings.get("channels", 2)
        gain = settings.get("volume", 100) / 100
        route += f";rate={rate};channels={channels};gain={gain}"
        return ["audio", "--audio", route]

    source, selector = VIDEO_SOURCE[kind]
    args = [source, selector, str(device.extra["selector"])]
    if kind == MediaKind.CAMERA:
        if settings.get("resolution"):
            args += ["--capture-size", settings["resolution"]]
        capture_fps = settings.get("capture_fps") or settings.get("fps")
        if capture_fps:
            args += ["--capture-fps", str(capture_fps)]
        pixel_format = "bgra" if preview else settings.get("pixel_format")
        if pixel_format in ("bgra", "bgr24", "rgba", "rgb24", "nv12", "i420"):
            args += ["--pixel-format", pixel_format]
    else:
        interval = 250 if preview else settings.get("capture_interval")
        if not interval:
            interval = max(1, round(1000 / (settings.get("fps") or 30)))
        args += ["--capture-interval", str(interval)]
    return args


def recording_args(device, settings, container, output):
    args = source_args(device, settings)
    args += ["--output", output, "--container", container]
    if device.kind in AUDIO_KINDS:
        options = {
            "sample_rate": "--sample-rate", "channels": "--channels",
            "audio_codec": "--audio-codec", "audio_bitrate": "--audio-bitrate",
        }
        codec_key = "audio_codec"
        compatible_codecs = AUDIO_CODEC_LIMITS.get(container)
    else:
        options = {
            "fps": "--fps", "output_size": "--size",
            "video_codec": "--video-codec", "video_bitrate": "--video-bitrate",
        }
        codec_key = "video_codec"
        compatible_codecs = VIDEO_CODEC_LIMITS.get(container)
    for key, option in options.items():
        value = settings.get(key)
        if key == "fps" and not value:
            continue
        if key == codec_key and compatible_codecs is not None and value not in compatible_codecs:
            continue
        if value is not None and value not in ("", "Passthrough"):
            args += [option, str(value)]
    return ["--json", "record", *args, "--stdin-control", "--no-interactive", "--status-interval", "0.5"]

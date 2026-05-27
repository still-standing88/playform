import platform as _platform
import sys
from dataclasses import dataclass, field


@dataclass
class ToolDef:
    name: str
    label: str
    description: str
    github_repo: str
    asset_patterns: dict
    is_zip: bool = False
    binary_name_posix: str = ""
    binary_name_win: str = ""
    direct_urls: dict = field(default_factory=dict)


def current_machine() -> str:
    m = _platform.machine().lower()
    if m in ("x86_64", "amd64"):
        return "x86_64"
    if m in ("aarch64", "arm64"):
        return "aarch64"
    return m


YTDLP = ToolDef(
    name="yt-dlp",
    label="yt-dlp",
    description=(
        "yt-dlp is a feature-rich command-line audio/video downloader with support "
        "for thousands of sites. PlayForm uses yt-dlp to download media from online "
        "sources such as YouTube and other streaming platforms."
    ),
    github_repo="yt-dlp/yt-dlp",
    asset_patterns={
        "windows": {
            "x86_64":  "yt-dlp.exe",
            "aarch64": "yt-dlp.exe",
        },
        "linux": {
            "x86_64":  "yt-dlp_linux",
            "aarch64": "yt-dlp_linux_aarch64",
        },
        "macos": {
            "x86_64":  "yt-dlp_macos",
            "aarch64": "yt-dlp_macos",
        },
    },
    is_zip=False,
    binary_name_posix="yt-dlp",
    binary_name_win="yt-dlp.exe",
)

DENO = ToolDef(
    name="deno",
    label="Deno",
    description=(
        "Deno is a secure, modern JavaScript and TypeScript runtime built on V8. "
        "PlayForm uses Deno for scripting, automation, and extension support. "
        "The binary is distributed as a zip archive and extracted automatically."
    ),
    github_repo="denoland/deno",
    asset_patterns={
        "windows": {
            "x86_64":  "deno-x86_64-pc-windows-msvc.zip",
            "aarch64": "deno-aarch64-pc-windows-msvc.zip",
        },
        "linux": {
            "x86_64":  "deno-x86_64-unknown-linux-gnu.zip",
            "aarch64": "deno-aarch64-unknown-linux-gnu.zip",
        },
        "macos": {
            "x86_64":  "deno-x86_64-apple-darwin.zip",
            "aarch64": "deno-aarch64-apple-darwin.zip",
        },
    },
    is_zip=True,
    binary_name_posix="deno",
    binary_name_win="deno.exe",
)

FFMPEG = ToolDef(
    name="ffmpeg",
    label="FFmpeg",
    description=(
        "FFmpeg provides ffmpeg and ffprobe binaries used by PlayForm tools for "
        "media conversion, extraction, and thumbnail generation. The download "
        "installs only the ffmpeg and ffprobe executables into PlayForm's bin folder."
    ),
    github_repo="",
    asset_patterns={},
    is_zip=True,
    binary_name_posix="ffmpeg",
    binary_name_win="ffmpeg.exe",
    direct_urls={
        "windows": {
            "x86_64": ["https://github.com/GyanD/codexffmpeg/releases/download/6.0/ffmpeg-6.0-essentials_build.7z"],
            "aarch64": ["https://github.com/GyanD/codexffmpeg/releases/download/6.0/ffmpeg-6.0-essentials_build.7z"],
        },
        "linux": {
            "x86_64": ["https://www.johnvansickle.com/ffmpeg/old-releases/ffmpeg-6.0-amd64-static.tar.xz"],
            "aarch64": ["https://www.johnvansickle.com/ffmpeg/old-releases/ffmpeg-6.0-amd64-static.tar.xz"],
        },
        "macos": {
            "x86_64": [
                "https://evermeet.cx/ffmpeg/ffmpeg-6.0.7z",
                "https://evermeet.cx/ffmpeg/ffprobe-6.0.7z",
            ],
            "aarch64": [
                "https://evermeet.cx/ffmpeg/ffmpeg-6.0.7z",
                "https://evermeet.cx/ffmpeg/ffprobe-6.0.7z",
            ],
        },
    },
)

ALL_TOOLS: list[ToolDef] = [YTDLP, DENO, FFMPEG]

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

ALL_TOOLS: list[ToolDef] = [YTDLP, DENO]

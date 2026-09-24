import platform as _platform
import sys
from dataclasses import dataclass, field

from utilities.i18n import N_


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
    release_tag: str = ""
    asset_regex: dict = field(default_factory=dict)


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
    description=N_(
        "yt-dlp is a feature-rich command-line audio/video downloader with support "
        "for thousands of sites. PlayForm uses yt-dlp to download media from online "
        "sources such as YouTube and other streaming platforms."
    ),
    github_repo="yt-dlp/yt-dlp",
    # yt-dlp publishes no native Windows arm64 build; the x86_64 exe runs under
    # Windows' own emulation. yt-dlp_macos is already a universal2 binary.
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
    description=N_(
        "Deno is a secure, modern JavaScript and TypeScript runtime built on V8. "
        "PlayForm doesn't use Deno directly - yt-dlp uses it as an optional JS "
        "runtime to resolve certain sites' streaming URLs. "
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
    description=N_(
        "FFmpeg provides ffmpeg and ffprobe binaries used by PlayForm tools for "
        "media conversion, extraction, and thumbnail generation. The download "
        "installs the full ffmpeg package into PlayForm's bin folder."
    ),
    github_repo="BtbN/FFmpeg-Builds",
    # BtbN keeps only the last 14 daily releases, but the floating "latest"
    # tag always carries a build for each release branch it still supports
    # (n8.1, n9.0, ...). Resolving the asset there by pattern keeps the
    # download current as branches are added or dropped; the regex prefers
    # the newest numbered branch and falls back to master.
    release_tag="latest",
    asset_patterns={},
    asset_regex={
        "windows": {
            "x86_64":  r"^ffmpeg-(?P<ver>n\d+\.\d+|master)-latest-win64-gpl-shared(?:-[\d.]+)?\.zip$",
            "aarch64": r"^ffmpeg-(?P<ver>n\d+\.\d+|master)-latest-winarm64-gpl-shared(?:-[\d.]+)?\.zip$",
        },
        "linux": {
            "x86_64":  r"^ffmpeg-(?P<ver>n\d+\.\d+|master)-latest-linux64-gpl(?:-[\d.]+)?\.tar\.xz$",
            "aarch64": r"^ffmpeg-(?P<ver>n\d+\.\d+|master)-latest-linuxarm64-gpl(?:-[\d.]+)?\.tar\.xz$",
        },
    },
    is_zip=True,
    binary_name_posix="ffmpeg",
    binary_name_win="ffmpeg.exe",
    # Windows takes the shared build (its bin/ holds the DLLs next to the
    # executables); Linux takes the static one, whose binaries are
    # self-contained, so bin/ alone is enough there.
    direct_urls={
        # macOS keeps evermeet, whose version-pinned URLs are pruned as soon
        # as a new build ships; the getrelease endpoints always serve the
        # current one. They carry no filename of their own, so each is paired
        # with the extension the extractor needs. aarch64 reuses the x86_64
        # build: evermeet publishes no native arm64 build, and Rosetta runs
        # the x86_64 one.
        "macos": {
            "x86_64": [
                ("https://evermeet.cx/ffmpeg/getrelease/7z", "ffmpeg.7z"),
                ("https://evermeet.cx/ffmpeg/getrelease/ffprobe/7z", "ffprobe.7z"),
            ],
            "aarch64": [
                ("https://evermeet.cx/ffmpeg/getrelease/7z", "ffmpeg.7z"),
                ("https://evermeet.cx/ffmpeg/getrelease/ffprobe/7z", "ffprobe.7z"),
            ],
        },
    },
)

ALL_TOOLS: list[ToolDef] = [YTDLP, DENO, FFMPEG]

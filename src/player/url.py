import subprocess
import logging
import os
import json
import sys
import re
import threading
from typing import Optional, List
from urllib.parse import urlparse, parse_qs

headers={ "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3" }
logger = logging.getLogger(__name__)
YTDLP_PATH = 'yt-dlp'
YTDLP_LOG_FILE = None
YTDLP_VERBOSE = False

_NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}


def _get_deno_arg():
    try:
        from utilities.functions import get_parent_dir
        name = "deno.exe" if os.name == "nt" else "deno"
        deno_path = os.path.join(get_parent_dir(), "bin", name)
        if os.path.isfile(deno_path):
            return ["--js-runtimes", f"deno:{deno_path}", "--remote-components", "ejs:github"]
    except Exception:
        pass
    return ["--remote-components", "ejs:github"]

def set_ytdlp_path(path: str):
    global YTDLP_PATH
    YTDLP_PATH = path

def set_ytdlp_log(log_file: Optional[str] = None, verbose: bool = False):
    global YTDLP_LOG_FILE, YTDLP_VERBOSE
    YTDLP_LOG_FILE = log_file
    YTDLP_VERBOSE = verbose

def get_yt_video_info(url: str) -> dict:
    command = [YTDLP_PATH, '--dump-json', '--no-playlist'] + _get_deno_arg() + [url]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            **_NO_WINDOW,
        )
        return json.loads(result.stdout)
    except FileNotFoundError:
        raise RuntimeError(f"yt-dlp executable not found at '{YTDLP_PATH}'.")
    except subprocess.CalledProcessError as e:
        raise ValueError(f"yt-dlp returned an error: {e.stderr}")
    except json.JSONDecodeError:
        raise ValueError(f"Failed to parse JSON from yt-dlp output.")

def run_ytdlp(url: str, as_playlist: bool = True, cookies: Optional[str] = None):
    from app_config import prefs
    
    cmd = [YTDLP_PATH, '--dump-json'] + _get_deno_arg()
    
    if not as_playlist:
        cmd.append('--no-playlist')
    
    cmd.extend(['--format', 'best[protocol^=http]'])
    
    if cookies:
        cmd.extend(['--cookies', cookies])
    else:
        cookies_file = prefs.prefs.get("youtube_cookies")
        if cookies_file:
            cmd.extend(['--cookies', cookies_file])
    
    if YTDLP_VERBOSE:
        cmd.append('--verbose')
    
    if YTDLP_LOG_FILE:
        cmd.extend(['--output', f'%(title)s.%(ext)s', '--write-info-json'])
        cmd.extend(['--no-write-playlist-metafiles'])
    
    cmd.append(url)
    
    if YTDLP_LOG_FILE:
        with open(YTDLP_LOG_FILE, 'a') as log:
            result = subprocess.run(cmd, capture_output=True, text=True, **_NO_WINDOW)
            log.write(f"Command: {' '.join(cmd)}\n")
            log.write(f"STDOUT:\n{result.stdout}\n")
            log.write(f"STDERR:\n{result.stderr}\n")
            log.write("-" * 80 + "\n")
    else:
        result = subprocess.run(cmd, capture_output=True, text=True, **_NO_WINDOW)
    
    if result.returncode != 0:
        raise ValueError(f"yt-dlp failed: {result.stderr}")
    
    lines = [line for line in result.stdout.strip().split('\n') if line]
    
    if len(lines) > 1:
        return [json.loads(line) for line in lines]
    elif lines:
        return json.loads(lines[0])
    else:
        raise ValueError("No output from yt-dlp")

def fetch_full_info(url: str, cookies: Optional[str] = None):
    from app_config import prefs
    
    cmd = [YTDLP_PATH, '--dump-json', '--no-playlist'] + _get_deno_arg() + [url]
    
    if cookies:
        cmd.extend(['--cookies', cookies])
    else:
        cookies_file = prefs.prefs.get("youtube_cookies")
        if cookies_file:
            cmd.extend(['--cookies', cookies_file])
    
    if YTDLP_VERBOSE:
        cmd.append('--verbose')
    
    if YTDLP_LOG_FILE:
        with open(YTDLP_LOG_FILE, 'a') as log:
            result = subprocess.run(cmd, capture_output=True, text=True, **_NO_WINDOW)
            log.write(f"Command: {' '.join(cmd)}\n")
            log.write(f"STDOUT:\n{result.stdout}\n")
            log.write(f"STDERR:\n{result.stderr}\n")
            log.write("-" * 80 + "\n")
    else:
        result = subprocess.run(cmd, capture_output=True, text=True, **_NO_WINDOW)
    
    if result.returncode != 0:
        raise ValueError(f"Failed to fetch full info: {result.stderr}")

    return json.loads(result.stdout.strip())

def fetch_video_comments(url: str, cookies: Optional[str] = None, max_comments: int = 200) -> List[dict]:
    from app_config import prefs

    # yt-dlp's own default is to fetch *all* comments, which can take
    # minutes-to-effectively-forever on popular videos; cap it so this
    # stays usable from an interactive dialog.
    cmd = [
        YTDLP_PATH, '--dump-json', '--no-playlist', '--write-comments',
        '--extractor-args', f'youtube:max_comments={max_comments}',
    ] + _get_deno_arg() + [url]

    if cookies:
        cmd.extend(['--cookies', cookies])
    else:
        cookies_file = prefs.prefs.get("youtube_cookies")
        if cookies_file:
            cmd.extend(['--cookies', cookies_file])

    if YTDLP_VERBOSE:
        cmd.append('--verbose')

    if YTDLP_LOG_FILE:
        with open(YTDLP_LOG_FILE, 'a') as log:
            result = subprocess.run(cmd, capture_output=True, text=True, **_NO_WINDOW)
            log.write(f"Command: {' '.join(cmd)}\n")
            log.write(f"STDOUT:\n{result.stdout}\n")
            log.write(f"STDERR:\n{result.stderr}\n")
            log.write("-" * 80 + "\n")
    else:
        result = subprocess.run(cmd, capture_output=True, text=True, **_NO_WINDOW)

    if result.returncode != 0:
        raise ValueError(f"Failed to fetch comments: {result.stderr}")

    info = json.loads(result.stdout.strip())
    return info.get("comments") or []

def has_playlist_param(url: str) -> bool:
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return 'list' in params
    except:
        return False

def is_playlist(url: str) -> bool:
    url_lower = url.lower()
    
    if has_playlist_param(url_lower):
        return True
    
    return any(indicator in url_lower for indicator in ['/sets/', '/albums/', '/playlist'])

def get_best_format(info) -> str:
    formats = info.get("formats", [])

    if not formats and "url" in info:
        return info["url"]

    http_formats = [f for f in formats if f.get("protocol", "").startswith(("http", "https"))]

    if http_formats:
        muxed = [f for f in http_formats if f.get("acodec") != "none" and f.get("vcodec") != "none"]
        if muxed:
            return muxed[-1]["url"]

        audio = [f for f in http_formats if f.get("acodec") != "none" and f.get("vcodec") == "none"]
        if audio:
            return audio[-1]["url"]

        video = [f for f in http_formats if f.get("vcodec") != "none"]
        if video:
            return video[-1]["url"]

    muxed = [f for f in formats if f.get("acodec") != "none" and f.get("vcodec") != "none"]
    if muxed:
        return muxed[-1]["url"]

    audio = [f for f in formats if f.get("acodec") != "none"]
    if audio:
        return audio[-1]["url"]

    video = [f for f in formats if f.get("vcodec") != "none"]
    if video:
        return video[-1]["url"]

    raise ValueError("No playable formats found")


_supported_extractor_names: set[str] | None = None
_preload_lock = threading.Lock()
_preload_started = False


def _load_extractor_names():
    global _supported_extractor_names
    if _supported_extractor_names is not None:
        return
    result = subprocess.run(
        [YTDLP_PATH, "--extractor-descriptions"],
        capture_output=True, text=True, **_NO_WINDOW,
    )
    names = set()
    for line in result.stdout.splitlines():
        name = line.split(":")[0].strip().lower()
        if name:
            names.add(name)
    _supported_extractor_names = names


def _load_extractor_names_thread():
    try:
        _load_extractor_names()
    except Exception:
        pass


def preload_extractors():
    global _preload_started
    with _preload_lock:
        if _preload_started:
            return
        _preload_started = True
    threading.Thread(target=_load_extractor_names_thread, daemon=True, name="ytdlp-extractor-preload").start()


_TLD_COMPONENTS = frozenset({"com", "co", "org", "net", "gov", "edu", "ac", "uk", "jp", "tv", "be", "io", "ai", "info", "biz", "me", "us", "ca", "de", "fr", "au", "nz", "in"})

_DOMAIN_ALIASES = {
    "youtu.be": "youtube",
    "x.com": "twitter",
    "fb.watch": "facebook",
}


def is_url_supported(url: str) -> bool:
    if _supported_extractor_names is None:
        _load_extractor_names()
    if not _supported_extractor_names:
        return False
    try:
        hostname = (urlparse(url).hostname or "").lower().removeprefix("www.")
    except Exception:
        return False

    if hostname in _DOMAIN_ALIASES:
        return True

    parts = hostname.split(".")
    domain = parts[-2] if len(parts) >= 2 else hostname
    if domain in _TLD_COMPONENTS and len(parts) >= 3:
        domain = parts[-3]

    for extractor in _supported_extractor_names:
        base = extractor.split(":")[0]
        if base == domain:
            return True
        if len(domain) >= 4 and domain in base:
            return True

    return False


def resolve_webpage_url(url: str, cookies: Optional[str] = None) -> str:
    info = run_ytdlp(url, as_playlist=False, cookies=cookies)
    if isinstance(info, list):
        info = info[0]
    return get_best_format(info)


def run_ytdlp_flat_playlist(url: str, cookies: Optional[str] = None) -> List[dict]:
    from app_config import prefs

    cmd = [YTDLP_PATH, "--flat-playlist", "--dump-json"] + _get_deno_arg()

    if cookies:
        cmd.extend(["--cookies", cookies])
    else:
        cookies_file = prefs.prefs.get("youtube_cookies")
        if cookies_file:
            cmd.extend(["--cookies", cookies_file])

    if YTDLP_VERBOSE:
        cmd.append("--verbose")

    cmd.append(url)

    if YTDLP_LOG_FILE:
        with open(YTDLP_LOG_FILE, "a") as log:
            result = subprocess.run(cmd, capture_output=True, text=True, **_NO_WINDOW)
            log.write(f"Command: {' '.join(cmd)}\n")
            log.write(f"STDOUT:\n{result.stdout}\n")
            log.write(f"STDERR:\n{result.stderr}\n")
            log.write("-" * 80 + "\n")
    else:
        result = subprocess.run(cmd, capture_output=True, text=True, **_NO_WINDOW)

    if result.returncode != 0:
        raise ValueError(f"yt-dlp failed: {result.stderr}")

    lines = [line for line in result.stdout.strip().split("\n") if line]
    return [json.loads(line) for line in lines]

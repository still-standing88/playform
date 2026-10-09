import subprocess
import os
import json
import sys
import re
import threading
from typing import Optional, List, NamedTuple
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

headers={ "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3" }
YTDLP_PATH = 'yt-dlp'
YTDLP_LOG_FILE = None
YTDLP_VERBOSE = False

# yt-dlp's own documented selector for "a stream a player can open": best video
# that already carries audio served over plain HTTP/HTTPS (not a DASH/HLS
# manifest), else the best video+audio pair. yt-dlp reports whichever it chose
# in `requested_formats`, so the choice stays yt-dlp's - see select_streams.
# The trailing b* is a catch-all (audio-only sites and anything else the first
# two alternatives cannot match), so the selector can never fail to resolve.
# Reference: the FORMAT SELECTION section of yt-dlp's manual.
_FORMAT_SELECTOR = "(bv*+ba/b)[protocol^=http][protocol!*=dash] / (bv*+ba/b) / b*"

_NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}


def _get_deno_arg():
    # Deno here is solely a yt-dlp dependency (its optional JS runtime for
    # resolving some sites' streaming URLs) - PlayForm itself never invokes it.
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

def _get_cookies_arg(cookies: Optional[str] = None) -> List[str]:
    from media_core.ytdlp_download.cookies import cookie_args
    return cookie_args(cookies or "")

def get_yt_video_info(url: str, cookies: Optional[str] = None) -> dict:
    command = [YTDLP_PATH, '--dump-json', '--no-playlist'] \
        + _get_deno_arg() + _get_cookies_arg(cookies) + [url]
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
        raise RuntimeError(_("yt-dlp executable not found at '{path}'.").format(path=YTDLP_PATH))
    except subprocess.CalledProcessError as e:
        raise ValueError(_("yt-dlp returned an error: {error}").format(error=e.stderr))
    except json.JSONDecodeError:
        raise ValueError(_("Failed to parse JSON from yt-dlp output."))

def run_ytdlp(url: str, as_playlist: bool = True, cookies: Optional[str] = None):
    cmd = [YTDLP_PATH, '--dump-json'] + _get_deno_arg()

    if not as_playlist:
        cmd.append('--no-playlist')

    cmd.extend(['-f', _FORMAT_SELECTOR])

    cmd.extend(_get_cookies_arg(cookies))
    
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
        raise ValueError(_("yt-dlp failed: {error}").format(error=result.stderr))
    
    lines = [line for line in result.stdout.strip().split('\n') if line]
    
    if len(lines) > 1:
        return [json.loads(line) for line in lines]
    elif lines:
        return json.loads(lines[0])
    else:
        raise ValueError(_("No output from yt-dlp"))

def fetch_full_info(url: str, cookies: Optional[str] = None):
    cmd = [YTDLP_PATH, '--dump-json', '--no-playlist'] \
        + _get_deno_arg() + _get_cookies_arg(cookies) + [url]
    
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
        raise ValueError(_("Failed to fetch full info: {error}").format(error=result.stderr))

    return json.loads(result.stdout.strip())

def fetch_video_comments(url: str, cookies: Optional[str] = None, max_comments: int = 200) -> List[dict]:
    # yt-dlp's own default is to fetch *all* comments, which can take
    # minutes-to-effectively-forever on popular videos; cap it so this
    # stays usable from an interactive dialog.
    cmd = [
        YTDLP_PATH, '--dump-json', '--no-playlist', '--write-comments',
        '--extractor-args', f'youtube:max_comments={max_comments}',
    ] + _get_deno_arg() + _get_cookies_arg(cookies) + [url]

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
        raise ValueError(_("Failed to fetch comments: {error}").format(error=result.stderr))

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

def has_video_and_playlist_params(url: str) -> bool:
    """True when the URL has both a video id (v=) and a playlist id
    (list=) - the ambiguous case (e.g. a YouTube "watch?v=...&list=..."
    link) where is_playlist() alone would silently pick the playlist
    without the single-video interpretation ever being offered."""
    try:
        params = parse_qs(urlparse(url).query)
        return 'v' in params and 'list' in params
    except Exception:
        return False

def is_mix_or_radio_playlist(url: str) -> bool:
    """True when list= starts with 'RD' - YouTube's prefix for
    auto-generated Mix/Radio playlists, as opposed to a real user-curated
    playlist (any other prefix, e.g. 'PL', 'OLAK5uy_', ...)."""
    try:
        list_values = parse_qs(urlparse(url).query).get('list', [])
        return bool(list_values) and list_values[0].startswith('RD')
    except Exception:
        return False

def strip_playlist_params(url: str) -> str:
    """Returns url with list/start_radio/index query params removed,
    keeping just the video id - used when the user chooses to load a
    single video from a link that also carries a playlist/Mix id."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    for key in ('list', 'start_radio', 'index'):
        params.pop(key, None)
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

class ResolvedStream(NamedTuple):
    """What to play for one extracted entry.

    `audio_url` is set only when the site offers no muxed stream at all (now
    the norm on YouTube: every format is video-only or audio-only), in which
    case the best video-only and audio-only tracks are chosen here and the
    player opens both together. Resolving this ourselves - rather than handing
    the webpage over for the player's own ytdl hook to sort out - keeps format
    selection in one place and off whatever yt-dlp happens to be on PATH."""

    url: str
    audio_url: Optional[str] = None


def _has_track(stream: dict, key: str) -> bool:
    # yt-dlp reports a missing track as "none" and an unknown one as None.
    return stream.get(key) not in (None, "none")


def select_streams(info) -> ResolvedStream:
    """What to open for one extracted entry, as chosen by yt-dlp.

    The choosing happens in yt-dlp itself (the -f selector run_ytdlp passes);
    this only reads the answer. `requested_formats` lists the formats yt-dlp
    picked: one entry for a single stream, two for the video+audio pair it
    falls back to when nothing is already muxed. Re-deriving that choice from
    the raw format list here is what stopped playback working twice over
    (once for videos with no muxed stream, once for ones whose last candidate
    was an HLS manifest), so it is deliberately not attempted any more.
    """
    requested = info.get("requested_formats") or []
    if requested:
        video = next((f for f in requested if _has_track(f, "vcodec")), None)
        audio = next((f for f in requested if _has_track(f, "acodec")), None)
        if video is not None and audio is not None and video is not audio:
            return ResolvedStream(video["url"], audio["url"])
        chosen = video or audio or requested[0]
        return ResolvedStream(chosen["url"])

    url = info.get("url")
    if url:
        return ResolvedStream(url)

    raise ValueError(_("No playable formats found"))


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


def resolve_stream(url: str, cookies: Optional[str] = None) -> ResolvedStream:
    info = run_ytdlp(url, as_playlist=False, cookies=cookies)
    if isinstance(info, list):
        info = info[0]
    return select_streams(info)


def run_ytdlp_flat_playlist(url: str, cookies: Optional[str] = None) -> List[dict]:
    cmd = [YTDLP_PATH, "--flat-playlist", "--dump-json"] \
        + _get_deno_arg() + _get_cookies_arg(cookies)

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
        raise ValueError(_("yt-dlp failed: {error}").format(error=result.stderr))

    lines = [line for line in result.stdout.strip().split("\n") if line]
    return [json.loads(line) for line in lines]

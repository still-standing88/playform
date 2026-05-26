import subprocess
import logging
import json
import requests
from typing import Optional, List, Union
from urllib.parse import urlparse, parse_qs, parse_qsl, urlencode, urlunparse
from gettext import gettext as _

headers={ "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3" }
logger = logging.getLogger(__name__)
YTDLP_PATH = 'yt-dlp'
YTDLP_LOG_FILE = None
YTDLP_VERBOSE = False

def set_ytdlp_path(path: str):
    global YTDLP_PATH
    YTDLP_PATH = path

def set_ytdlp_log(log_file: Optional[str] = None, verbose: bool = False):
    global YTDLP_LOG_FILE, YTDLP_VERBOSE
    YTDLP_LOG_FILE = log_file
    YTDLP_VERBOSE = verbose

def get_yt_video_info(url: str) -> dict:
    command = [YTDLP_PATH, '--dump-json', '--no-playlist', url]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
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
    
    cmd = [YTDLP_PATH, '--dump-json']
    
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
            result = subprocess.run(cmd, capture_output=True, text=True)
            log.write(f"Command: {' '.join(cmd)}\n")
            log.write(f"STDOUT:\n{result.stdout}\n")
            log.write(f"STDERR:\n{result.stderr}\n")
            log.write("-" * 80 + "\n")
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
    
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
    
    cmd = [YTDLP_PATH, '--dump-json', '--no-playlist', url]
    
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
            result = subprocess.run(cmd, capture_output=True, text=True)
            log.write(f"Command: {' '.join(cmd)}\n")
            log.write(f"STDOUT:\n{result.stdout}\n")
            log.write(f"STDERR:\n{result.stderr}\n")
            log.write("-" * 80 + "\n")
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise ValueError(f"Failed to fetch full info: {result.stderr}")
    
    return json.loads(result.stdout.strip())

def run_ytdlp_flat_playlist(url: str, cookies: Optional[str] = None):
    from app_config import prefs

    cmd = [YTDLP_PATH, '--flat-playlist', '--dump-json']

    if cookies:
        cmd.extend(['--cookies', cookies])
    else:
        cookies_file = prefs.prefs.get("youtube_cookies")
        if cookies_file:
            cmd.extend(['--cookies', cookies_file])

    if YTDLP_VERBOSE:
        cmd.append('--verbose')

    cmd.append(url)

    if YTDLP_LOG_FILE:
        with open(YTDLP_LOG_FILE, 'a') as log:
            result = subprocess.run(cmd, capture_output=True, text=True)
            log.write(f"Command: {' '.join(cmd)}\n")
            log.write(f"STDOUT:\n{result.stdout}\n")
            log.write(f"STDERR:\n{result.stderr}\n")
            log.write("-" * 80 + "\n")
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise ValueError(f"yt-dlp failed: {result.stderr}")

    lines = [line for line in result.stdout.strip().split('\n') if line]
    return [json.loads(line) for line in lines]

def is_supported(url: str) -> bool:
    cmd = [YTDLP_PATH, '--dump-json', '--no-playlist', '--skip-download', url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return False
    
    try:
        info = json.loads(result.stdout.strip())
        return info.get('extractor') != 'generic'
    except:
        return False

def has_playlist_param(url: str) -> bool:
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return 'list' in params
    except:
        return False

def normalize_playlist_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        params = parse_qsl(parsed.query, keep_blank_values=True)
        has_list = any(key == "list" and value for key, value in params)
        if not has_list:
            return url

        normalized_params = [(key, value) for key, value in params if key.lower() != "index"]
        normalized_query = urlencode(normalized_params, doseq=True)
        return urlunparse(parsed._replace(query=normalized_query))
    except Exception:
        return url

def is_playlist(url: str) -> bool:
    url = normalize_playlist_url(url)
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

def resolve_media_url(url: str, cookies: Optional[str] = None) -> str:
    try:
        info = run_ytdlp(url, as_playlist=False, cookies=cookies)
        if isinstance(info, list):
            info = info[0]
        return get_best_format(info)
    except Exception:
        try:
            res = requests.get(url, allow_redirects=True, stream=True, timeout=15, headers=headers)
            resolved_url = res.url
            res.close()
            return resolved_url
        except Exception:
            return url

def build_url_playlist_result(url: str, cookies: Optional[str] = None) -> dict:
    url = normalize_playlist_url(url)
    if is_playlist(url):
        entries = []
        flat_entries = run_ytdlp_flat_playlist(url, cookies=cookies)
        playlist_title = _("Extracted Playlist")

        for info in flat_entries:
            source_url = info.get("webpage_url") or info.get("original_url") or info.get("url")
            if not source_url:
                continue

            playlist_title = (
                info.get("playlist_title")
                or info.get("playlist")
                or playlist_title
            )
            entries.append(
                {
                    "location": source_url,
                    "title": info.get("title") or _("Streaming URL"),
                    "metadata": {
                        "original_location": source_url,
                        "requires_resolution": True,
                    },
                }
            )

        if not entries:
            raise ValueError(_("No playable entries found in playlist"))

        return {
            "title": playlist_title,
            "entries": entries,
            "start_index": 0,
        }

    try:
        info = run_ytdlp(url, as_playlist=False, cookies=cookies)
        if isinstance(info, list):
            info = info[0]
        source_url = info.get("webpage_url") or info.get("original_url") or url
        title = info.get("title") or _("Streaming URL")
        return {
            "title": title,
            "entries": [
                {
                    "location": source_url,
                    "title": title,
                    "metadata": {
                        "original_location": source_url,
                        "requires_resolution": True,
                    },
                }
            ],
            "start_index": 0,
        }
    except Exception:
        resolved_url = resolve_media_url(url, cookies=cookies)
        return {
            "title": _("Streaming URL"),
            "entries": [
                {
                    "location": url,
                    "title": _("Streaming URL"),
                    "metadata": {
                        "original_location": url,
                        "requires_resolution": False,
                        "resolved_location": resolved_url,
                    },
                }
            ],
            "start_index": 0,
        }

def extract(url: str, cookies: Optional[str] = None) -> Union[str, List[str]]:
    url = normalize_playlist_url(url)
    if not is_supported(url):
        logger.info("Attempting to resolve direct URL redirection if any")
        res = requests.get(url, allow_redirects=True, stream=True, timeout=15, headers=headers)
        url = res.url
        res.close()
        logger.info(f"Resolved URL: {url}")
        return url
    
    try:
        if is_playlist(url):
            result = run_ytdlp(url, as_playlist=True, cookies=cookies)
            urls = []
            
            if isinstance(result, list):
                for entry in result:
                    try:
                        if 'url' in entry and not entry.get('formats'):
                            full_info = fetch_full_info(entry['url'], cookies=cookies)
                            urls.append(get_best_format(full_info))
                        else:
                            urls.append(get_best_format(entry))
                    except:
                        continue
            else:
                urls.append(get_best_format(result))
            
            if not urls:
                raise ValueError("No playable entries found in playlist")
            
            return urls
        else:
            info = run_ytdlp(url, as_playlist=False, cookies=cookies)
            if isinstance(info, list):
                info = info[0]
            return get_best_format(info)
            
    except Exception as e:
        if is_supported(url):
            raise ValueError(f"Extraction failed for supported site: {e}")
        return url

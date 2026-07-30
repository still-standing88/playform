import subprocess
import urllib.parse
import re


def is_url_supported(url: str, yt_dlp_path: str) -> bool:
    result = subprocess.run(
        [yt_dlp_path, "--extractor-descriptions"],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
    )

    parsed = urllib.parse.urlparse(url)
    hostname = (parsed.hostname or "").lower()
    hostname = hostname.removeprefix("www.")

    parts = hostname.split(".")
    domain = parts[-2] if len(parts) >= 2 else hostname

    for line in result.stdout.splitlines():
        name_part = line.split(":")[0].strip().lower()
        if re.split(r"[^a-z0-9]", name_part)[0] == domain:
            return True

    return False
print(is_url_supported("https://www.cacebook.com/ww","yt-dlp.exe"))
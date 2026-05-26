from __future__ import annotations

import argparse
import re
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import polib
import requests


ROOT_DIR = Path(__file__).resolve().parent.parent
LANG_DIR = ROOT_DIR / "lang"
DOMAIN = "PlayFormDomain"
TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
TOKEN_RE = re.compile(r"\{[^{}]+\}|<[^>]+>|\n")


_thread_local = threading.local()


def _session() -> requests.Session:
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        _thread_local.session = session
    return session


def _protect(text: str) -> tuple[str, dict[str, str]]:
    placeholders: dict[str, str] = {}

    def repl(match: re.Match[str]) -> str:
        token = f"__PLAYFORM_TOKEN_{len(placeholders)}__"
        placeholders[token] = match.group(0)
        return token

    return TOKEN_RE.sub(repl, text), placeholders


def _translate_once(text: str, target: str) -> str:
    protected, placeholders = _protect(text)
    params = {
        "client": "gtx",
        "sl": "en",
        "tl": target,
        "dt": "t",
        "q": protected,
    }
    response = _session().get(TRANSLATE_URL, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    translated = "".join(part[0] for part in data[0] if part and part[0])
    for token, original in placeholders.items():
        translated = translated.replace(token, original)
    return translated


def translate_text(text: str, target: str, retries: int = 3) -> str:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            return _translate_once(text, target)
        except Exception as exc:
            last_error = exc
            time.sleep(1.0 + attempt)
    if last_error:
        raise last_error
    return text


def translate_po(po_path: Path, target: str, workers: int = 8) -> int:
    po = polib.pofile(str(po_path))
    entries = [entry for entry in po if entry.msgid and not entry.obsolete]
    pending = [entry for entry in entries if not entry.msgstr]
    if not pending:
        print(f"No untranslated entries in {po_path}")
        return 0

    def work(entry: polib.POEntry) -> tuple[str, str]:
        return entry.msgid, translate_text(entry.msgid, target)

    translated_count = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(work, entry): entry for entry in pending}
        for future in as_completed(futures):
            entry = futures[future]
            try:
                _, translated = future.result()
                entry.msgstr = translated
                if "fuzzy" in entry.flags:
                    entry.flags = [flag for flag in entry.flags if flag != "fuzzy"]
                translated_count += 1
            except Exception as exc:
                raise RuntimeError(f"Failed to translate {entry.msgid!r} in {po_path}: {exc}") from exc

    po.save(str(po_path))
    print(f"Translated {translated_count} entries in {po_path}")
    return translated_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Translate gettext PO files using Google Translate.")
    parser.add_argument("languages", nargs="+", help="Language codes to translate, for example es ar")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    total = 0
    for language in args.languages:
        po_path = LANG_DIR / language / "LC_MESSAGES" / f"{DOMAIN}.po"
        if not po_path.exists():
            print(f"Missing translation catalog: {po_path}")
            return 1
        total += translate_po(po_path, language, workers=args.workers)

    print(f"Translated {total} entries total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

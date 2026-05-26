from __future__ import annotations

import gettext
from pathlib import Path

from utilities.functions import get_parent_dir


DOMAIN = "PlayFormDomain"


def get_locale_dir() -> Path:
    return Path(get_parent_dir()) / "lang"


def _language_candidates(language: str | None) -> list[str] | None:
    if not language:
        return None

    raw = str(language).strip()
    if not raw:
        return None

    candidates: list[str] = []
    base = raw.replace("-", "_")
    for candidate in (
        raw,
        raw.lower(),
        base,
        base.lower(),
        base.split("_", 1)[0],
        base.split("_", 1)[0].lower(),
    ):
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def install_translation(language: str | None = None, domain: str = DOMAIN):
    localedir = str(get_locale_dir())
    languages = _language_candidates(language)
    translation = gettext.translation(domain, localedir=localedir, languages=languages, fallback=True)
    translation.install()
    return translation

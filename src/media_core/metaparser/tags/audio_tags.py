"""Common audio tag extraction via mutagen.

Covers the "solved problem" formats plan.md calls out — MP3 (ID3), FLAC,
M4A/AAC, OGG Vorbis/Opus, WavPack, etc. This is the path that also covers
plain music files with no bext/iXML/UCS filename at all, and it's what makes
the eventual index usable for "sfx or not" per the user's ask, not just
field-recorder output.

mutagen already handles WAVE/AIFF (their own ID3-in-RIFF / ID3-in-AIFF tag
support), but for those two formats this module is deliberately *not* the
primary path — metaparser.extractor routes WAV/AIFF through the chunk
walkers first (bext/iXML/LIST are the richer metadata source there), and
only falls back to mutagen's WAVE/AIFF ID3 reading for the plain title/artist
tags a chunk walk wouldn't surface.
"""

from __future__ import annotations

import logging
from pathlib import Path

import mutagen

logger = logging.getLogger(__name__)

# mutagen's easy=True only translates tag keys to friendly names (title,
# artist, ...) for its Easy* wrapper classes (EasyMP3, EasyMP4, ...) — it
# does NOT apply to WAVE/AIFF, whose ID3-in-container tags come back as raw
# ID3 frame IDs even when easy=True is passed. Confirmed against real files
# (a Sound Ideas AIFF with TIT2/TPE1/TALB/COMM::eng instead of title/artist/
# album/comment) — without this mapping, description lookups elsewhere
# silently miss real, present data. Mirrors mutagen's own EasyID3 alias
# table, applied manually for the containers it doesn't cover.
_ID3_FRAME_ALIASES = {
    "TIT2": "title",
    "TPE1": "artist",
    "TPE2": "albumartist",
    "TALB": "album",
    "TCON": "genre",
    "TRCK": "tracknumber",
    "TPOS": "discnumber",
    "TDRC": "date",
    "TYER": "date",
    "TCOP": "copyright",
    "TCMP": "compilation",
    "TCOM": "composer",
    "TENC": "encodedby",
    "TBPM": "bpm",
}


class AudioTagError(Exception):
    pass


def _normalize_key(key: str) -> str:
    if key.startswith("COMM:"):
        # mutagen's ID3 HashKey for COMM frames is "COMM:<description>:<lang>".
        # An empty description is an ordinary comment; anything else (e.g.
        # iTunes' "COMM:iTunNORM:eng") is a distinct, purpose-specific field
        # that shouldn't be conflated with it — left under its raw key.
        parts = key.split(":")
        description = parts[1] if len(parts) > 1 else ""
        return "comment" if not description else key
    return _ID3_FRAME_ALIASES.get(key, key)


def _frame_text(value) -> str | None:
    """Extracts displayable text from a tag value, whatever shape mutagen
    handed back. Returns None for binary frames (cover art, attached
    objects) so callers can skip them entirely — an ID3 APIC frame's
    default str() dumps its raw image bytes as an escaped string, which has
    no business ending up in a text index.
    """
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    if hasattr(value, "data") and not hasattr(value, "text"):
        return None
    if hasattr(value, "text"):
        return "; ".join(str(t) for t in value.text)
    return str(value)


def extract(path: str | Path) -> dict:
    """Returns a flat dict of whatever tags mutagen found, plus basic stream
    info (length, bitrate, sample_rate, channels where the format exposes
    them). Returns an empty dict (never raises) for files mutagen can't
    open at all — that's expected for e.g. a .wav with no ID3 chunk, not
    an error worth surfacing as one.
    """
    path = Path(path)
    try:
        audio = mutagen.File(path, easy=True)
    except Exception as exc:
        logger.warning("mutagen failed to open %s: %s", path, exc)
        return {}

    if audio is None:
        logger.debug("mutagen recognized no tags/format for %s", path)
        return {}

    tags: dict[str, str] = {}
    if audio.tags:
        for key, value in audio.tags.items():
            text = _frame_text(value)
            if text is None:
                logger.debug("skipping binary tag frame %r (cover art or attached object)", key)
                continue
            tags[_normalize_key(key)] = text

    info = {}
    if audio.info is not None:
        for attr in ("length", "bitrate", "sample_rate", "channels", "bits_per_sample", "codec", "fps"):
            if hasattr(audio.info, attr):
                info[attr] = getattr(audio.info, attr)

    return {"tags": tags, "stream_info": info, "format": type(audio).__name__}

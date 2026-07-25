"""Shared text-decoding helper for chunk payloads that the spec calls
"ASCII" but real-world tools (Soundminer, WaveLab, etc.) happily write
Windows-1252 into anyway — the BOOM Library files this was validated
against have a literal '©' byte in the bext Originator field.

Strict ASCII would replace it with U+FFFD (data loss for no reason); tried
in order (UTF-8, then cp1252, then latin-1) recovers the real character in
both the UTF-8 and Windows-1252 cases and never raises, since latin-1 maps
every byte 1:1 and can't fail.
"""

from __future__ import annotations


def decode_lenient(raw: bytes) -> str:
    for encoding in ("utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")

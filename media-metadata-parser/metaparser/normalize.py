"""Alias/normalization table — deliberately deferred (Phase 4, plan.md).

Don't build the `"description" ~ DESCRIPTION ~ Description` mapping against
guesses. This module is a stub with the shape it'll take once there's a real
sample corpus to build the table from (the SFX drive, later phase) — wiring
it up before that point would mean designing a schema blind, which is the
exact mistake plan.md calls out avoiding.

`db.indexer` intentionally does NOT import this module yet — it indexes
straight off the raw blobs in models.RawFileMetadata. Once ALIASES below is
populated from real data, wire normalize_fields() into the indexer's ingest
path so search can work over normalized field names without re-scanning.
"""

from __future__ import annotations

# {canonical_field_name: {raw_key_variant, ...}}. Empty until built from a
# real sample scan — see module docstring.
ALIASES: dict[str, set[str]] = {}


def normalize_fields(raw: dict) -> dict:
    """Maps raw_key -> canonical_field_name for every key in `raw` that has
    a known alias, passing unrecognized keys through unchanged. A no-op
    today since ALIASES is empty; kept as the seam for when it isn't.
    """
    if not ALIASES:
        return dict(raw)

    reverse: dict[str, str] = {}
    for canonical, variants in ALIASES.items():
        for variant in variants:
            reverse[variant.lower()] = canonical

    normalized = {}
    for key, value in raw.items():
        canonical = reverse.get(key.lower(), key)
        normalized[canonical] = value
    return normalized

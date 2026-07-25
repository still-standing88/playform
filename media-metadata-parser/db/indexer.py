"""Directory walk -> metaparser.extractor -> upsert into the SQLite index.

Re-scanning is idempotent and incremental: a file is only re-extracted if
its mtime or size changed since the last index run, so pointing this at a
large SFX library repeatedly doesn't mean re-parsing everything every time.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from metaparser import extractor, models
from db import schema

logger = logging.getLogger(__name__)

# Audio: chunk-walkable formats plus everything mutagen reads natively.
# Video: mutagen-native containers plus exiftool-fallback containers.
SUPPORTED_EXTENSIONS = {
    ".wav", ".wave", ".aif", ".aiff", ".aifc",
    ".mp3", ".flac", ".ogg", ".oga", ".opus", ".m4a", ".wma", ".wv", ".ape", ".aac",
    ".mp4", ".m4v", ".mov", ".wmv", ".asf", ".mkv", ".avi", ".webm",
}


@dataclasses.dataclass
class IndexStats:
    scanned: int = 0
    indexed: int = 0
    skipped_unchanged: int = 0
    failed: int = 0


def _extract_row_fields(meta: models.RawFileMetadata) -> dict:
    """Best-effort pull of the structured columns out of whatever sources
    are actually present, in priority order (UCS filename > iXML sfx fields
    > bext > plain tags), since not every file will have all of them.
    """
    ucs = meta.ucs_from_filename or {}
    ixml_sfx = {}
    steinberg_sfx = {}
    if meta.ixml_raw:
        from metaparser.interpreters import ixml as ixml_module

        ixml_sfx = ixml_module.extract_sfx_fields(meta.ixml_raw)
        # Fallback for vendors (Soundminer/Steinberg-authored iXML, confirmed
        # against a real commercial library) that skip the ASWG tag scheme
        # entirely and encode category info as generic ATTR_LIST NAME/VALUE
        # pairs instead — see ixml.extract_steinberg_sfx_fields.
        steinberg_sfx = ixml_module.extract_steinberg_sfx_fields(meta.ixml_raw)

    tags = (meta.tags_raw or {}).get("tags", {})
    stream_info = (meta.tags_raw or {}).get("stream_info", {})
    # Case-insensitive view: confirmed via real ffmpeg-encoded test files
    # that the same semantic "descriptive text" field lands under different
    # keys depending on format — "comment" (ID3/MP4/WavPack), "description"
    # (Vorbis/Opus), "Description" (ASF/WMA, capitalized, not lowercased by
    # mutagen's easy wrapper for that format). Checking case-insensitively
    # and trying both names avoids silently losing real, present data to a
    # key-name mismatch that's purely a format quirk.
    tags_ci = {k.lower(): v for k, v in tags.items()}

    description = None
    if meta.bext_raw:
        description = meta.bext_raw.get("description") or None
    if not description and meta.info_raw:
        description = meta.info_raw.get("comment") or meta.info_raw.get("title")
    if not description:
        description = tags_ci.get("comment") or tags_ci.get("description") or tags_ci.get("title")

    # Free-text blob for FTS coverage of whatever plain tags/INFO fields
    # exist beyond the structured columns above (genre, keywords, coding
    # history, etc) — joined rather than dropped just because there's no
    # dedicated column for them.
    tags_blob_parts = list(tags.values())
    if meta.info_raw:
        tags_blob_parts.extend(meta.info_raw.values())
    if meta.bext_raw and meta.bext_raw.get("coding_history"):
        tags_blob_parts.append(meta.bext_raw["coding_history"])
    tags_blob = " ".join(str(p) for p in tags_blob_parts if p)

    return {
        "cat_id": ucs.get("cat_id") or ixml_sfx.get("catid") or ixml_sfx.get("cat_id"),
        "category": ucs.get("category") or ixml_sfx.get("category") or steinberg_sfx.get("category"),
        "subcategory": ucs.get("subcategory") or ixml_sfx.get("sub_category"),
        "fx_name": ucs.get("fx_name") or ixml_sfx.get("fx_name"),
        "creator_id": ucs.get("creator_id") or ixml_sfx.get("creator_id"),
        "source_id": ucs.get("source_id") or ixml_sfx.get("source_id") or steinberg_sfx.get("library"),
        "description": description,
        "originator": meta.bext_raw.get("originator") if meta.bext_raw else None,
        "tags_blob": tags_blob or None,
        "duration_secs": stream_info.get("length"),
        "sample_rate": stream_info.get("sample_rate"),
        "channels": stream_info.get("channels"),
    }


def index_file(conn: sqlite3.Connection, path: Path) -> bool:
    """Extracts and upserts a single file. Returns True if it was (re-)
    indexed, False if skipped as unchanged. Extraction failures are caught,
    logged, and recorded on the row as has_errors rather than aborting the
    whole directory scan.
    """
    stat = path.stat()
    existing = conn.execute(
        "SELECT mtime, size_bytes FROM files WHERE path = ?", (str(path),)
    ).fetchone()
    if existing is not None and existing["mtime"] == stat.st_mtime and existing["size_bytes"] == stat.st_size:
        return False

    try:
        meta = extractor.extract(path)
    except Exception as exc:
        logger.warning("extraction failed for %s: %s", path, exc)
        meta = models.RawFileMetadata(
            file_path=str(path), file_format="unknown", errors=[f"extraction raised: {exc}"]
        )

    fields = _extract_row_fields(meta)
    raw_json = json.dumps(dataclasses.asdict(meta), default=str)

    conn.execute(
        """
        INSERT INTO files (
            path, filename, file_format, mtime, size_bytes, indexed_at,
            cat_id, category, subcategory, fx_name, creator_id, source_id,
            description, originator, tags_blob, duration_secs, sample_rate, channels,
            raw_json, has_errors
        ) VALUES (
            :path, :filename, :file_format, :mtime, :size_bytes, :indexed_at,
            :cat_id, :category, :subcategory, :fx_name, :creator_id, :source_id,
            :description, :originator, :tags_blob, :duration_secs, :sample_rate, :channels,
            :raw_json, :has_errors
        )
        ON CONFLICT(path) DO UPDATE SET
            filename=excluded.filename, file_format=excluded.file_format,
            mtime=excluded.mtime, size_bytes=excluded.size_bytes, indexed_at=excluded.indexed_at,
            cat_id=excluded.cat_id, category=excluded.category, subcategory=excluded.subcategory,
            fx_name=excluded.fx_name, creator_id=excluded.creator_id, source_id=excluded.source_id,
            description=excluded.description, originator=excluded.originator, tags_blob=excluded.tags_blob,
            duration_secs=excluded.duration_secs, sample_rate=excluded.sample_rate, channels=excluded.channels,
            raw_json=excluded.raw_json, has_errors=excluded.has_errors
        """,
        {
            "path": str(path),
            "filename": path.name,
            "file_format": meta.file_format,
            "mtime": stat.st_mtime,
            "size_bytes": stat.st_size,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "raw_json": raw_json,
            "has_errors": 1 if meta.errors else 0,
            **fields,
        },
    )
    return True


def index_directory(db_path: str | Path, root: str | Path) -> IndexStats:
    root = Path(root)
    stats = IndexStats()

    conn = schema.open_db(db_path)
    try:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            stats.scanned += 1
            try:
                changed = index_file(conn, path)
            except Exception as exc:
                logger.error("indexing failed for %s: %s", path, exc)
                stats.failed += 1
                continue
            if changed:
                stats.indexed += 1
            else:
                stats.skipped_unchanged += 1

            if stats.scanned % 200 == 0:
                conn.commit()
                logger.info("indexed %d/%d scanned so far", stats.indexed, stats.scanned)

        conn.commit()
    finally:
        conn.close()

    return stats

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
    ".mp4", ".m4v", ".mov", ".wmv", ".asf", ".f4v", ".mkv", ".mka", ".avi", ".webm",
    ".rm", ".rmvb", ".flv", ".mpg", ".mpeg", ".m2v", ".ts", ".m2ts", ".mts", ".dv",
    ".amr", ".3gp", ".3g2",
    # mutagen already reads these natively (ac3, trueaudio, musepack,
    # oggspeex, oggtheora modules) — previously missing from this allowlist
    # meant a directory scan silently skipped them even though extraction
    # would've worked fine if called on one directly.
    ".ac3", ".eac3", ".tta", ".mpc", ".spx", ".ogv",
    # same underlying formats as extensions already listed above, just
    # different naming conventions: .mp1/.mp2 are MPEG audio Layer I/II
    # (same frame-header decode as .mpg's audio path), .vob is MPEG
    # Program Stream (same as .mpg/.mpeg), .ra is RealAudio (same RMFF
    # container as .rm/.rmvb), .divx is AVI/RIFF with a DivX-branded codec.
    ".mp1", ".mp2", ".vob", ".ra", ".divx",
    ".caf", ".dts",
}


@dataclasses.dataclass
class IndexStats:
    scanned: int = 0
    indexed: int = 0
    skipped_unchanged: int = 0
    failed: int = 0


def _descriptive_strings(*values) -> list[str]:
    """Filters to non-empty strings only — the only thing that belongs in a
    free-text search blob. Numbers, raw bytes, and structural/technical
    values (duration ticks, codec version numbers, hex element IDs) never
    get this far, so search never surfaces arbitrary keys or numeric noise,
    only genuinely descriptive text a person actually wrote.
    """
    return [v.strip() for v in values if isinstance(v, str) and v.strip()]


def _fields_from_matroska(meta: models.RawFileMetadata) -> dict:
    if not meta.matroska_raw:
        return {}
    from metaparser.interpreters import matroska as matroska_module

    info = matroska_module.extract_info(meta.matroska_raw)
    tags = matroska_module.extract_tags(meta.matroska_raw)
    tracks = matroska_module.extract_tracks(meta.matroska_raw)
    audio_track = next((t for t in tracks if "sampling_frequency" in t), None)

    return {
        "description": info.get("Title"),
        "blob": _descriptive_strings(info.get("Title"), info.get("MuxingApp"), info.get("WritingApp"), *tags.values()),
        "duration_secs": matroska_module.extract_duration_secs(meta.matroska_raw),
        "sample_rate": int(audio_track["sampling_frequency"]) if audio_track and audio_track.get("sampling_frequency") else None,
        "channels": audio_track.get("channels") if audio_track else None,
    }


def _fields_from_realmedia(meta: models.RawFileMetadata) -> dict:
    if not meta.realmedia_raw:
        return {}
    cont = meta.realmedia_raw.get("CONT") or {}
    mdpr_list = meta.realmedia_raw.get("MDPR") or []
    first_mdpr = mdpr_list[0] if mdpr_list else {}

    # RMFF's MDPR duration field is documented (consistently, across public
    # RealMedia demuxer references) as milliseconds — moderate, not full,
    # confidence, the same tier as this project's other non-ExifTool-sourced
    # bitfield work (see CREDITS.md).
    duration_ms = first_mdpr.get("duration")

    return {
        "description": cont.get("title") or cont.get("comment"),
        "blob": _descriptive_strings(
            cont.get("title"), cont.get("author"), cont.get("copyright"), cont.get("comment"),
            first_mdpr.get("stream_name"), first_mdpr.get("mime_type"),
        ),
        "duration_secs": duration_ms / 1000 if isinstance(duration_ms, (int, float)) and duration_ms else None,
        "sample_rate": None,
        "channels": None,
    }


def _fields_from_flv(meta: models.RawFileMetadata) -> dict:
    if not meta.flv_raw:
        return {}
    script_data = meta.flv_raw.get("script_data") or {}
    duration = script_data.get("duration")

    return {
        "description": None,
        # onMetaData properties are genuinely arbitrary (see amf0.py) — only
        # the string-typed ones are search material; numeric ones (width/
        # height/duration/framerate) never enter the free-text blob.
        "blob": _descriptive_strings(*[v for v in script_data.values() if isinstance(v, str)]),
        "duration_secs": float(duration) if isinstance(duration, (int, float)) else None,
        "sample_rate": None,
        "channels": None,
    }


def _fields_from_mpeg(meta: models.RawFileMetadata) -> dict:
    if not meta.mpeg_raw:
        return {}
    audio = meta.mpeg_raw.get("audio") or {}
    xing = meta.mpeg_raw.get("xing") or {}
    channel_mode = audio.get("channel_mode")

    return {
        "description": None,
        "blob": _descriptive_strings(xing.get("encoder")),
        # not computed — a single frame's header doesn't give total file
        # duration the way a container's own duration field does.
        "duration_secs": None,
        "sample_rate": audio.get("sample_rate"),
        "channels": 1 if channel_mode == "Single Channel" else (2 if channel_mode else None),
    }


def _fields_from_m2ts(meta: models.RawFileMetadata) -> dict:
    if not meta.m2ts_raw:
        return {}
    stream_names = [
        stream.get("stream_type_name")
        for program in meta.m2ts_raw.get("programs") or []
        for stream in program.get("streams", [])
    ]

    return {
        "description": None,
        "blob": _descriptive_strings(*stream_names),
        "duration_secs": meta.m2ts_raw.get("duration_secs"),
        "sample_rate": None,
        "channels": None,
    }


def _fields_from_dv(meta: models.RawFileMetadata) -> dict:
    if not meta.dv_raw or "error" in meta.dv_raw:
        return {}
    dv_data = meta.dv_raw

    return {
        "description": dv_data.get("video_format"),
        "blob": _descriptive_strings(dv_data.get("video_format"), dv_data.get("date_time_original")),
        "duration_secs": dv_data.get("duration"),
        "sample_rate": dv_data.get("audio_sample_rate"),
        "channels": dv_data.get("audio_channels"),
    }


def _fields_from_amr(meta: models.RawFileMetadata) -> dict:
    if not meta.amr_raw:
        return {}
    return {"description": None, "blob": [], "duration_secs": meta.amr_raw.get("duration_secs"), "sample_rate": None, "channels": None}


def _fields_from_udta(meta: models.RawFileMetadata) -> dict:
    if not meta.udta_raw:
        return {}
    # No fixed key list to prefer a "title" from — udta's fourCCs vary by
    # vendor/era. '\xa9nam' is the closest thing to a convention, used when
    # present; every other descriptive string found is still useful search
    # material even without a canonical "this is the title" slot.
    title = meta.udta_raw.get("\xa9nam")

    return {
        "description": title if isinstance(title, str) else None,
        "blob": _descriptive_strings(*meta.udta_raw.values()),
        "duration_secs": None,
        "sample_rate": None,
        "channels": None,
    }


def _fields_from_caf(meta: models.RawFileMetadata) -> dict:
    if not meta.caf_raw:
        return {}
    info = meta.caf_raw.get("info") or {}
    desc = meta.caf_raw.get("desc") or {}
    sample_rate = desc.get("sample_rate")

    return {
        "description": info.get("title") or info.get("Title"),
        "blob": _descriptive_strings(*info.values()),
        # not computed — would need the 'data' chunk's byte length divided
        # by desc's frame rate, which isn't decoded here.
        "duration_secs": None,
        "sample_rate": int(sample_rate) if isinstance(sample_rate, (int, float)) else None,
        "channels": desc.get("channels_per_frame"),
    }


def _fields_from_dts(meta: models.RawFileMetadata) -> dict:
    if not meta.dts_raw:
        return {}
    return {
        "description": None,
        "blob": _descriptive_strings(meta.dts_raw.get("channel_arrangement")),
        # dts_raw's duration is for a single frame only (~10-40ms) — mapping
        # it to the whole file's duration_secs would be actively misleading,
        # not just incomplete, so it's deliberately excluded.
        "duration_secs": None,
        "sample_rate": meta.dts_raw.get("sample_rate"),
        "channels": None,
    }


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
    if meta.axml_raw:
        tags_blob_parts.append(meta.axml_raw)

    duration_secs = stream_info.get("length")
    sample_rate = stream_info.get("sample_rate")
    channels = stream_info.get("channels")

    # Same priority-chain discipline as everything above: each of these
    # formats only contributes a field when the earlier (WAV/AIFF/mutagen)
    # sources didn't already have one, and only ever contributes genuinely
    # descriptive strings to the search blob — see _descriptive_strings and
    # each helper's own comments for what's deliberately excluded (raw
    # bytes, hex element IDs, per-frame-only durations, etc).
    for source in (
        _fields_from_matroska(meta),
        _fields_from_realmedia(meta),
        _fields_from_flv(meta),
        _fields_from_mpeg(meta),
        _fields_from_m2ts(meta),
        _fields_from_dv(meta),
        _fields_from_amr(meta),
        _fields_from_udta(meta),
        _fields_from_caf(meta),
        _fields_from_dts(meta),
    ):
        if not description and source.get("description"):
            description = source["description"]
        tags_blob_parts.extend(source.get("blob") or [])
        if duration_secs is None and source.get("duration_secs") is not None:
            duration_secs = source["duration_secs"]
        if sample_rate is None and source.get("sample_rate") is not None:
            sample_rate = source["sample_rate"]
        if channels is None and source.get("channels") is not None:
            channels = source["channels"]

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
        "duration_secs": duration_secs,
        "sample_rate": sample_rate,
        "channels": channels,
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

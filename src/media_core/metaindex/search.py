"""Query interface over the index: free-text search via FTS5, plus
structured filters over the columns metaindex.schema/metaindex.indexer populate. Every
function returns plain dicts (via sqlite3.Row) rather than leaking cursors,
so callers (cli.py today, potentially a GUI later) don't need to know
anything about the schema beyond field names.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from media_core.metaindex import schema

_SELECT_COLUMNS = """
    files.id, files.path, files.filename, files.file_format,
    files.cat_id, files.category, files.subcategory, files.fx_name,
    files.creator_id, files.source_id, files.description, files.originator,
    files.duration_secs, files.sample_rate, files.channels,
    files.indexed_at, files.has_errors
"""

# bm25() weights, one per files_fts column IN DECLARATION ORDER (filename,
# description, category, subcategory, fx_name, creator_id, source_id,
# tags_blob — see schema.py's _CREATE_FTS). Unweighted bm25 treats a match
# in tags_blob (the broadest, noisiest free-text catch-all) the same as a
# match in filename or description — a filename/description hit is a much
# stronger signal of relevance, so it's weighted higher; tags_blob is
# weighted lowest since it's the most likely to contain an incidental match.
_BM25_WEIGHTS = "10.0, 8.0, 5.0, 4.0, 5.0, 3.0, 3.0, 1.0"


@dataclass
class SearchResult:
    id: int
    path: str
    filename: str
    file_format: str
    cat_id: str | None
    category: str | None
    subcategory: str | None
    fx_name: str | None
    creator_id: str | None
    source_id: str | None
    description: str | None
    originator: str | None
    duration_secs: float | None
    sample_rate: int | None
    channels: int | None
    indexed_at: str
    has_errors: bool

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SearchResult":
        return cls(
            id=row["id"],
            path=row["path"],
            filename=row["filename"],
            file_format=row["file_format"],
            cat_id=row["cat_id"],
            category=row["category"],
            subcategory=row["subcategory"],
            fx_name=row["fx_name"],
            creator_id=row["creator_id"],
            source_id=row["source_id"],
            description=row["description"],
            originator=row["originator"],
            duration_secs=row["duration_secs"],
            sample_rate=row["sample_rate"],
            channels=row["channels"],
            indexed_at=row["indexed_at"],
            has_errors=bool(row["has_errors"]),
        )


def full_text_search(db_path: str | Path, query: str, limit: int = 50) -> list[SearchResult]:
    """FTS5 MATCH search across filename/description/category/subcategory/
    fx_name/creator_id/source_id/tags_blob, ranked by bm25 with
    filename/description weighted above the broader tags_blob catch-all
    (see _BM25_WEIGHTS). A malformed FTS query (unbalanced quotes, bad
    operators) is treated as a plain phrase rather than raising — search
    should degrade, not 500.
    """
    conn = schema.connect(db_path)
    try:
        try:
            cursor = conn.execute(
                f"""
                SELECT {_SELECT_COLUMNS}
                FROM files_fts
                JOIN files ON files.id = files_fts.rowid
                WHERE files_fts MATCH ?
                ORDER BY bm25(files_fts, {_BM25_WEIGHTS})
                LIMIT ?
                """,
                (query, limit),
            )
        except sqlite3.OperationalError:
            escaped = '"' + query.replace('"', '""') + '"'
            cursor = conn.execute(
                f"""
                SELECT {_SELECT_COLUMNS}
                FROM files_fts
                JOIN files ON files.id = files_fts.rowid
                WHERE files_fts MATCH ?
                ORDER BY bm25(files_fts, {_BM25_WEIGHTS})
                LIMIT ?
                """,
                (escaped, limit),
            )
        return [SearchResult.from_row(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def filter_search(
    db_path: str | Path,
    category: str | None = None,
    creator_id: str | None = None,
    file_format: str | None = None,
    min_duration: float | None = None,
    max_duration: float | None = None,
    limit: int = 50,
) -> list[SearchResult]:
    """Structured filtering, all params ANDed, all optional. Uses the plain
    columns rather than FTS since these are exact/range matches, not
    free-text relevance.
    """
    conditions = []
    params: list = []

    if category is not None:
        conditions.append("files.category = ?")
        params.append(category)
    if creator_id is not None:
        conditions.append("files.creator_id = ?")
        params.append(creator_id)
    if file_format is not None:
        conditions.append("files.file_format = ?")
        params.append(file_format)
    if min_duration is not None:
        conditions.append("files.duration_secs >= ?")
        params.append(min_duration)
    if max_duration is not None:
        conditions.append("files.duration_secs <= ?")
        params.append(max_duration)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    conn = schema.connect(db_path)
    try:
        cursor = conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM files {where_clause} ORDER BY filename LIMIT ?",
            params,
        )
        return [SearchResult.from_row(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_raw_metadata(db_path: str | Path, file_id: int) -> dict | None:
    """Full RawFileMetadata blob for one file, for when a caller needs more
    than the structured columns surface (e.g. inspecting cue points or the
    full iXML tree for a specific result).
    """
    conn = schema.connect(db_path)
    try:
        row = conn.execute("SELECT raw_json FROM files WHERE id = ?", (file_id,)).fetchone()
        return json.loads(row["raw_json"]) if row else None
    finally:
        conn.close()


def stats(db_path: str | Path) -> dict:
    conn = schema.connect(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) AS n FROM files").fetchone()["n"]
        by_format = conn.execute(
            "SELECT file_format, COUNT(*) AS n FROM files GROUP BY file_format ORDER BY n DESC"
        ).fetchall()
        with_errors = conn.execute("SELECT COUNT(*) AS n FROM files WHERE has_errors = 1").fetchone()["n"]
        return {
            "total_files": total,
            "by_format": {row["file_format"]: row["n"] for row in by_format},
            "files_with_errors": with_errors,
        }
    finally:
        conn.close()

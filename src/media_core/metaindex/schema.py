"""SQLite schema for the metadata index: a `files` table holding one row per
indexed file (structured columns pulled out of RawFileMetadata, plus the
full raw blob as JSON so nothing extracted is ever lost to the schema), and
an FTS5 virtual table over the searchable text fields.

WAL mode + a single writer connection mirrors the pattern already used
elsewhere in this repo's own DB layer (src/app_db/base_database.py) — SQLite
under concurrent access needs one of those two disciplines, and this module
picks WAL since the indexer is the only writer and search is read-only.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

_CREATE_FILES_TABLE = """
CREATE TABLE IF NOT EXISTS files (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    path            TEXT NOT NULL UNIQUE,
    filename        TEXT NOT NULL,
    file_format     TEXT NOT NULL,
    mtime           REAL NOT NULL,
    size_bytes      INTEGER NOT NULL,
    indexed_at      TEXT NOT NULL,

    -- Pulled out of ucs_from_filename / ixml sfx fields / bext for fast
    -- structured filtering. May be NULL — not every file has UCS/iXML data.
    cat_id          TEXT,
    category        TEXT,
    subcategory     TEXT,
    fx_name         TEXT,
    creator_id      TEXT,
    source_id       TEXT,

    description     TEXT,
    originator      TEXT,
    tags_blob       TEXT,

    duration_secs   REAL,
    sample_rate     INTEGER,
    channels        INTEGER,

    -- Everything RawFileMetadata produced, verbatim, as JSON. The
    -- structured columns above are a convenience index over this, not a
    -- replacement for it — normalize.py landing later reshapes this without
    -- needing a rescan, since the raw blob is preserved here.
    raw_json        TEXT NOT NULL,

    has_errors      INTEGER NOT NULL DEFAULT 0
);
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_files_category ON files(category);",
    "CREATE INDEX IF NOT EXISTS idx_files_cat_id ON files(cat_id);",
    "CREATE INDEX IF NOT EXISTS idx_files_creator_id ON files(creator_id);",
    "CREATE INDEX IF NOT EXISTS idx_files_file_format ON files(file_format);",
    # filter_search's min_duration/max_duration range filter had no index at
    # all — a full table scan on every call once the library is large.
    "CREATE INDEX IF NOT EXISTS idx_files_duration_secs ON files(duration_secs);",
]

# prefix='2 3 4' precomputes prefix indexes for 2-4 character prefixes, so a
# "search as you type" style query (e.g. "expl" while the user is still
# typing "explosion") stays fast without scanning the full term dictionary
# once the library is large — FTS5 handles occasional prefix queries fine
# without this, but it's cheap to have and only helps at scale.
_CREATE_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
    filename,
    description,
    category,
    subcategory,
    fx_name,
    creator_id,
    source_id,
    tags_blob,
    content='files',
    content_rowid='id',
    prefix='2 3 4'
);
"""

# Keep files_fts in sync with files without every caller having to remember to.
_CREATE_TRIGGERS = [
    """
    CREATE TRIGGER IF NOT EXISTS files_ai AFTER INSERT ON files BEGIN
        INSERT INTO files_fts(rowid, filename, description, category, subcategory, fx_name, creator_id, source_id, tags_blob)
        VALUES (new.id, new.filename, new.description, new.category, new.subcategory, new.fx_name, new.creator_id, new.source_id, new.tags_blob);
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS files_ad AFTER DELETE ON files BEGIN
        INSERT INTO files_fts(files_fts, rowid, filename, description, category, subcategory, fx_name, creator_id, source_id, tags_blob)
        VALUES ('delete', old.id, old.filename, old.description, old.category, old.subcategory, old.fx_name, old.creator_id, old.source_id, old.tags_blob);
    END;
    """,
    """
    CREATE TRIGGER IF NOT EXISTS files_au AFTER UPDATE ON files BEGIN
        INSERT INTO files_fts(files_fts, rowid, filename, description, category, subcategory, fx_name, creator_id, source_id, tags_blob)
        VALUES ('delete', old.id, old.filename, old.description, old.category, old.subcategory, old.fx_name, old.creator_id, old.source_id, old.tags_blob);
        INSERT INTO files_fts(rowid, filename, description, category, subcategory, fx_name, creator_id, source_id, tags_blob)
        VALUES (new.id, new.filename, new.description, new.category, new.subcategory, new.fx_name, new.creator_id, new.source_id, new.tags_blob);
    END;
    """,
]


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    # synchronous=NORMAL is the standard, safe pairing with WAL (durability
    # is still guaranteed across app crashes; only an OS-level power loss
    # mid-write is the tradeoff, same as most production SQLite deployments
    # accept) — meaningfully faster writes than the default FULL, which
    # fsyncs on every transaction regardless of journal mode.
    conn.execute("PRAGMA synchronous=NORMAL;")
    # 8MB page cache (default is ~2MB) and a 256MB mmap window — both cheap,
    # both help once the index is large enough that it doesn't fit entirely
    # in the default cache; negative cache_size means "KB", per SQLite's own
    # convention (positive would mean "number of pages").
    conn.execute("PRAGMA cache_size=-8000;")
    conn.execute("PRAGMA mmap_size=268435456;")
    return conn


def initialize(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_FILES_TABLE)
    for stmt in _CREATE_INDEXES:
        conn.execute(stmt)
    # NOTE: CREATE VIRTUAL TABLE IF NOT EXISTS is a no-op against an already-
    # created files_fts from before the prefix= option was added above — an
    # existing database file needs `python cli.py clear <db_path>` (or just
    # deleting the file) followed by a re-index to actually pick it up. No
    # migration path is built for this since no real index exists yet to
    # migrate (see plan.md's testing-phase status) — worth revisiting if
    # that's no longer true by the time this is read.
    conn.execute(_CREATE_FTS)
    for stmt in _CREATE_TRIGGERS:
        conn.execute(stmt)
    conn.commit()


def open_db(db_path: str | Path) -> sqlite3.Connection:
    """Convenience: connect + initialize in one call."""
    conn = connect(db_path)
    initialize(conn)
    return conn


def clear(conn: sqlite3.Connection) -> None:
    """Deletes every indexed row and reclaims the freed disk space.
    files_fts is kept in sync automatically via the files_ad trigger — no
    separate FTS cleanup needed. Schema/indexes/triggers are left in place,
    so a caller can re-run index_directory() immediately afterward without
    needing to reopen or reinitialize anything.
    """
    conn.execute("DELETE FROM files;")
    conn.commit()
    conn.execute("VACUUM;")  # must run outside any open transaction, hence the commit() just above


def _path_under_root(path: str, normalized_root: str, prefix: str) -> bool:
    normalized_path = os.path.normcase(os.path.normpath(path))
    return normalized_path == normalized_root or normalized_path.startswith(prefix)


def count_under_root(conn: sqlite3.Connection, root_path: str | Path) -> int:
    """Total indexed files whose path is root_path itself or somewhere
    beneath it - the same prefix-matching rule app_db.media_db.is_path_cataloged
    uses, so a catalog root's reported count always matches what search
    actually treats as "this folder's files".
    """
    normalized_root = os.path.normcase(os.path.normpath(str(root_path)))
    prefix = normalized_root + os.sep
    cursor = conn.execute("SELECT path FROM files")
    return sum(1 for row in cursor.fetchall() if _path_under_root(row["path"], normalized_root, prefix))


def delete_by_root(conn: sqlite3.Connection, root_path: str | Path) -> int:
    """Deletes every indexed row under root_path (itself or any descendant) -
    the single-folder counterpart to clear(), for a "remove this cataloged
    folder" action rather than wiping the whole index. files_fts stays in
    sync automatically via the files_ad trigger. Returns the number of rows
    deleted.
    """
    normalized_root = os.path.normcase(os.path.normpath(str(root_path)))
    prefix = normalized_root + os.sep
    cursor = conn.execute("SELECT id, path FROM files")
    ids = [row["id"] for row in cursor.fetchall() if _path_under_root(row["path"], normalized_root, prefix)]
    if not ids:
        return 0
    conn.executemany("DELETE FROM files WHERE id = ?", [(i,) for i in ids])
    conn.commit()
    return len(ids)


def optimize(conn: sqlite3.Connection) -> None:
    """Refreshes the query planner's statistics — SQLite doesn't do this on
    its own as a table grows, and stale statistics on a formerly-small,
    now-large table can lead to a genuinely worse query plan being chosen.
    Recommended by SQLite's own docs to run periodically (e.g. once per
    indexing session), not on every single write.
    """
    conn.execute("PRAGMA optimize;")

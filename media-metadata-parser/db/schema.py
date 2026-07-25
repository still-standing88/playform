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
]

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
    content_rowid='id'
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
    return conn


def initialize(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_FILES_TABLE)
    for stmt in _CREATE_INDEXES:
        conn.execute(stmt)
    conn.execute(_CREATE_FTS)
    for stmt in _CREATE_TRIGGERS:
        conn.execute(stmt)
    conn.commit()


def open_db(db_path: str | Path) -> sqlite3.Connection:
    """Convenience: connect + initialize in one call."""
    conn = connect(db_path)
    initialize(conn)
    return conn

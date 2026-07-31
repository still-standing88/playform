# Integration plan: wiring this module into PlayForm's app

This branch is scoped to the module only — nothing in `src/` is touched
here. This document exists so that when this module *is* imported into the
app, the actual code change is small, obvious, and doesn't require
re-deriving the plan from scratch.

## Install

From the main app's own virtualenv:

```bash
pip install -e path/to/media-metadata-parser
```

That makes `import metaparser` (and `import db`, if the richer path below is
used) work anywhere in the app, editable — changes to this module's source
take effect immediately, no reinstall step. `pyproject.toml` is the
canonical dependency list (`mutagen`, `lxml`); `pip install -e .[dev]` also
pulls in `pytest`.

## The integration point

[`src/app_db/catalog_worker.py:89`](../src/app_db/catalog_worker.py) (line
number as of this module's last audit — re-check before relying on it)
currently always writes `metadata={}` when building each `MediaFile`:

```python
batch.append(MediaFile(
    id=app_db.media_db._generate_file_id(str(file_path)),
    path=str(file_path),
    filename=file_path.name,
    size=stat.st_size,
    duration=None,
    media_type=media_type,
    metadata={},                    # <-- always empty today
    date_added=str(stat.st_ctime),
    date_modified=str(stat.st_mtime),
))
```

`MediaDatabase.MEDIA_SCHEMA` already has a `metadata TEXT` column
(`src/app_db/media_db.py`) that this dict gets JSON-serialized into via
`_add_media_worker`/`_add_media_batch_worker` — so the storage side needs no
schema change for the cheap path below.

## Option 1 — cheap: fill that column, nothing else changes

```python
import metaparser
...
metadata=metaparser.extract_as_dict(file_path),
```

One line. `extract_as_dict()` never raises for a recognized-but-malformed
file (see `metaparser/extractor.py`'s own graceful-degradation contract) —
worst case for a bad file is a metadata dict with an `errors` list in it,
not a crashed scan. This is the option discussed and recommended earlier:
get real metadata flowing into the column that already exists before
deciding whether the richer option below is worth building.

Tradeoff: `MediaDatabase` has no FTS5/structured-column search over this
JSON blob — `search_by_filename` is a plain `LIKE` on the filename only.
Metadata becomes inspectable per-file but not searchable across the library
without also querying into the JSON text.

## Option 2 — richer: structured columns + FTS5 search

Port `db/schema.py`'s structured columns (`cat_id`, `category`, `duration_secs`,
...) and its `files_fts` FTS5 virtual table into `MediaDatabase.MEDIA_SCHEMA`
(a migration, since `media_files` already has rows), then have
`CatalogWorker` populate both the existing columns and the new ones via
`db.indexer._extract_row_fields()` — already built, tested, and — as of the
most recent pass — wired for descriptive text vs. technical/structured
fields (see `db/indexer.py`'s `_fields_from_*` helpers): real content only
ever reaches free-text search, never raw keys, byte blobs, or per-frame-only
values pretending to be whole-file numbers.

This is meaningfully more work (a schema migration on a live table) and
should only happen once there's an actual query pattern from real usage
that `LIKE`-on-filename doesn't serve — same reasoning as before: don't
design the richer schema blind.

## Verification once either option lands

```bash
python -m pytest tests/ -q          # from media-metadata-parser/
```

Then in the app itself: catalog a folder with at least one `.mkv`/`.caf`/
legacy `.mov` file (formats mutagen alone doesn't fully cover), and confirm
the `metadata` column — or the FTS index, for option 2 — actually reflects
what's in the file, not just `{}`.

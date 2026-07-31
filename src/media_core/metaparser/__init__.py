"""metaparser: dynamic, ExifTool-inspired audio/video metadata extraction.

Quick start for an external caller (e.g. PlayForm's own CatalogWorker in
src/app_db/catalog_worker.py — see ../INTEGRATION.md for the intended
pattern; this package deliberately doesn't reach into that code itself,
only exposes what a caller there would need):

    import metaparser
    metadata_dict = metaparser.extract_as_dict(file_path)   # JSON-safe dict
    # or, for a caller writing straight into a TEXT/JSON column:
    metadata_json = metaparser.extract_as_json(file_path)

Both call metaparser.extractor.extract() underneath, which never raises for
a recognized-but-malformed file — see that function's own docstring, and
plan.md's "never let failure to parse one chunk kill the whole file's
extraction", for the graceful-degradation contract every format in this
package follows.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from media_core.metaparser import extractor
from media_core.metaparser.models import RawFileMetadata

try:
    from importlib.metadata import version

    __version__ = version("media-metaparser")
except Exception:  # not installed as a package (running straight from source) — fall back
    __version__ = "0.1.0"

__all__ = ["extract", "extract_as_dict", "extract_as_json", "RawFileMetadata"]

extract = extractor.extract


def extract_as_dict(path: str | Path) -> dict:
    """Runs extract() and flattens the result to a plain, JSON-safe dict —
    the shape a caller storing this in a generic JSON column (e.g.
    PlayForm's own media_files.metadata TEXT column, currently always
    written as `{}` by CatalogWorker) wants directly, without needing to
    know this is a dataclass or handle its one non-JSON-native field type
    (raw bytes, from chunks/objects this package couldn't further decode)
    itself.
    """
    meta = extractor.extract(path)
    # Round-trips through json.dumps/loads rather than stopping at
    # dataclasses.asdict(): asdict() alone leaves nested bytes values (e.g.
    # an unrecognized RealMedia object's raw payload) as real bytes objects,
    # which a caller's own json.dumps would then fail on. default=str here
    # matches the same convention metaindex/indexer.py already uses for raw_json.
    return json.loads(json.dumps(dataclasses.asdict(meta), default=str))


def extract_as_json(path: str | Path) -> str:
    """Same as extract_as_dict(), pre-serialized — for a caller writing
    straight into a TEXT/JSON column without an intermediate dict step."""
    return json.dumps(dataclasses.asdict(extractor.extract(path)), default=str)

"""UCS category list loader/lookup.

Backed by metaparser/data/ucs_categories.json, which is explicitly a
*starter* table, not the official 82-category/753-subcategory UCS 8.2.1
spreadsheet (that's a gated download from universalcategorysystem.com, not
something fetchable at build time). Every lookup here degrades gracefully —
an unknown CatID returns None, it never raises, since an incomplete category
table is expected, not exceptional.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).parent.parent / "data" / "ucs_categories.json"


@dataclass(frozen=True)
class CategoryEntry:
    cat_id: str
    category: str
    subcategory: str
    synonyms: tuple[str, ...]


@lru_cache(maxsize=1)
def _load() -> dict[str, CategoryEntry]:
    with open(_DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    entries: dict[str, CategoryEntry] = {}
    for cat_id, fields in raw.get("categories", {}).items():
        entries[cat_id] = CategoryEntry(
            cat_id=cat_id,
            category=fields["category"],
            subcategory=fields["subcategory"],
            synonyms=tuple(fields.get("synonyms", [])),
        )
    logger.debug("loaded %d UCS category entries from starter table", len(entries))
    return entries


def lookup(cat_id: str) -> CategoryEntry | None:
    """Exact CatID lookup (case-sensitive — UCS CatIDs are case-defined:
    category in caps, subcategory in title case).
    """
    return _load().get(cat_id)


def lookup_ci(cat_id: str) -> CategoryEntry | None:
    """Case-insensitive fallback lookup, for filenames that don't preserve
    the official casing (common in the wild).
    """
    target = cat_id.lower()
    for entry in _load().values():
        if entry.cat_id.lower() == target:
            return entry
    return None


def search_by_category_name(category: str) -> list[CategoryEntry]:
    """All entries under a given top-level category name (case-insensitive)."""
    target = category.lower()
    return [e for e in _load().values() if e.category.lower() == target]


def all_entries() -> list[CategoryEntry]:
    return list(_load().values())


def build_from_csv(csv_path: str | Path, output_path: str | Path | None = None) -> Path:
    """Regenerate metaparser/data/ucs_categories.json from the official UCS
    CSV export once it's available (universalcategorysystem.com spreadsheet,
    columns are typically CatID/Category/SubCategory/Synonyms — verify
    against the actual header row before trusting this blindly, vendor
    exports have varied column names across UCS versions).
    """
    csv_path = Path(csv_path)
    output_path = Path(output_path) if output_path else _DATA_PATH

    categories: dict[str, dict] = {}
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat_id = (row.get("CatID") or row.get("Cat ID") or "").strip()
            if not cat_id:
                continue
            synonyms_raw = row.get("Synonyms") or row.get("Synonym", "")
            synonyms = [s.strip() for s in synonyms_raw.split(",") if s.strip()] if synonyms_raw else []
            categories[cat_id] = {
                "category": (row.get("Category") or "").strip(),
                "subcategory": (row.get("SubCategory") or row.get("Sub Category") or "").strip(),
                "synonyms": synonyms,
            }

    payload = {
        "_meta": {
            "note": f"Generated from {csv_path.name} via categories.build_from_csv().",
            "source_version_targeted": "official UCS export",
        },
        "categories": categories,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _load.cache_clear()
    logger.info("wrote %d categories to %s", len(categories), output_path)
    return output_path

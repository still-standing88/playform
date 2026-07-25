"""UCS filename tokenizer.

Basic UCS format: CatID_FXName_CreatorID_SourceID(_UserData)
The CatID block is the only mandatory piece of the convention; everything
after it is positional but frequently missing (plenty of real files are just
`CatID_FXName.wav`). This is deliberately lenient rather than pattern-matched
against a rigid regex, since this is the fallback label source precisely for
files with thin/absent iXML — being strict here would defeat the purpose.

The "Advanced" UCS format (`CatID-UserCategory_VendorCategory-FXName_...`)
is not specifically modeled yet: without a real sample corpus showing how
common it actually is in practice, building dedicated parsing for it risks
guessing at a shape that doesn't match what's really out there (the same
"go look before you design" principle plan.md applies to Phase 4). The
basic-format tokenizer already segments on underscores generically enough
that advanced-format filenames still get *a* cat_id/fx_name/creator_id split,
just without decomposing the User/Vendor category sub-blocks.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from metaparser.ucs import categories

logger = logging.getLogger(__name__)

# CatID shape, confirmed against a real commercial library (BOOM Library
# Doors, 373 files): the category is an all-caps run of letters, and the
# subcategory abbreviation is very often concatenated directly onto it with
# NO hyphen and NOT all-caps — e.g. "DOORAntq", "DOORAppl", "WNDWCover".
# The hyphenated form ("BLAST-Large", "GUNShot-Single") also occurs, and the
# UCS "Advanced" format documents CatID blocks with more than one hyphenated
# piece (e.g. "CatID-UserCategory-FXName") — not seen in real data yet, but
# accepting it costs nothing since it only adds matches, never removes any.
#
# The leading-caps run requires 3+ letters, not 2+: confirmed against a real
# non-UCS library (PM Phone Foley) that "PM_Phone_Foley_..." — a 2-letter
# product-line prefix, not a category — was matching as a false-positive
# CatID under a 2+ threshold. Every real CatID seen so far (or documented in
# the UCS category list) runs 3+ letters, so this closes that false-positive
# class without excluding anything actually confirmed real. What
# distinguishes a real CatID token from an ordinary capitalized English word
# (e.g. "Slamming") is that run of leading capitals — a normal word only
# capitalizes its first letter. Deliberately permissive beyond that — this
# is a heuristic gate to decide "does the first block look like a CatID at
# all", not a validator against the official list (that's categories.lookup).
_CAT_ID_RE = re.compile(r"^[A-Z]{3,}[A-Za-z0-9]*(-[A-Za-z][A-Za-z0-9]*)*$")


@dataclass
class UcsFilenameResult:
    cat_id: str | None
    fx_name: str | None
    creator_id: str | None
    source_id: str | None
    user_data: str | None
    raw_tokens: list[str]
    category_entry: "categories.CategoryEntry | None"


def _looks_like_cat_id(token: str) -> bool:
    return bool(_CAT_ID_RE.match(token))


def parse_filename(path: str | Path) -> UcsFilenameResult:
    """Tokenize a filename against the UCS convention. Works on the stem
    (extension stripped). Never raises — a filename that doesn't follow UCS
    at all just comes back with everything None except raw_tokens.
    """
    stem = Path(path).stem
    tokens = stem.split("_")

    if not tokens or not tokens[0]:
        return UcsFilenameResult(None, None, None, None, None, tokens, None)

    cat_id = None
    rest = tokens
    if _looks_like_cat_id(tokens[0]):
        cat_id = tokens[0]
        rest = tokens[1:]
    else:
        logger.debug("first token %r doesn't look like a UCS CatID — treating filename as non-UCS", tokens[0])

    fx_name = rest[0] if len(rest) >= 1 and rest[0] else None
    creator_id = rest[1] if len(rest) >= 2 and rest[1] else None
    source_id = rest[2] if len(rest) >= 3 and rest[2] else None
    user_data = "_".join(rest[3:]) if len(rest) > 3 else None

    entry = None
    if cat_id is not None:
        entry = categories.lookup(cat_id) or categories.lookup_ci(cat_id)
        if entry is None:
            logger.debug("CatID %r not found in starter category table (expected for an incomplete table)", cat_id)

    return UcsFilenameResult(
        cat_id=cat_id,
        fx_name=fx_name,
        creator_id=creator_id,
        source_id=source_id,
        user_data=user_data,
        raw_tokens=tokens,
        category_entry=entry,
    )


def cross_check_against_ixml(ucs_result: UcsFilenameResult, ixml_sfx_fields: dict[str, str]) -> dict:
    """Compares the filename-derived category against an iXML CATEGORY/CATID
    tag, when both exist. This is the thesis-relevant bit from plan.md: does
    the filename's category claim agree with what the embedded metadata
    says? Returns a dict describing what was compared and whether it agreed
    — never raises, and clearly marks itself inconclusive when there isn't
    enough on one side or the other to compare.
    """
    ixml_cat_id = ixml_sfx_fields.get("catid") or ixml_sfx_fields.get("cat_id")
    ixml_category = ixml_sfx_fields.get("category")

    if ucs_result.cat_id is None and ixml_cat_id is None and ixml_category is None:
        return {"comparable": False, "reason": "no category information on either side"}

    if ucs_result.cat_id is None:
        return {"comparable": False, "reason": "filename has no UCS CatID to compare"}

    if ixml_cat_id is None and ixml_category is None:
        return {"comparable": False, "reason": "iXML has no CATEGORY/CATID tag to compare"}

    filename_category = ucs_result.category_entry.category if ucs_result.category_entry else None

    if ixml_cat_id is not None:
        agrees = ixml_cat_id.strip().lower() == ucs_result.cat_id.strip().lower()
        return {
            "comparable": True,
            "method": "catid_exact",
            "filename_cat_id": ucs_result.cat_id,
            "ixml_cat_id": ixml_cat_id,
            "agrees": agrees,
        }

    # Only a bare CATEGORY tag to go on — compare against the resolved
    # top-level category name if the starter table happened to know this CatID.
    if filename_category is None:
        return {
            "comparable": False,
            "reason": "filename CatID not in starter category table, can't resolve to a category name to compare",
        }

    agrees = ixml_category.strip().lower() == filename_category.strip().lower()
    return {
        "comparable": True,
        "method": "category_name",
        "filename_category": filename_category,
        "ixml_category": ixml_category,
        "agrees": agrees,
    }

"""iXML chunk interpreter.

iXML is an XML payload embedded in a WAV/AIFF chunk, but despite being
"industry-agreed", it is not a fixed field list — beyond the core
PROJECT/SCENE/TAKE block there's an open-ended ASWG (Audio Standards Working
Group) extension covering sound-effects metadata (CATEGORY, SUB_CATEGORY,
CATID, FX_NAME, LIBRARY, CREATOR_ID, SOURCE_ID — this is a second place UCS
data can live, independent of the filename), plus dialogue/music sub-blocks,
plus vendor-specific blocks (e.g. Steinberg's own tag namespace).

Because the real tag surface is much wider than any one recorder or library
vendor uses, this module never hardcodes a tag whitelist: it walks the tree
generically and returns whatever showed up, keyed by tag name, nested as it
was in the source XML. A small set of known aliases is used only to make
common fields easy to reach without walking the tree by hand — it never
drops or renames anything from the raw structure.

Vendor iXML in the wild is often not well-formed (unclosed tags, unescaped
entities), so this uses lxml's recovering parser rather than stdlib
ElementTree, which would just raise on the first malformed byte.
"""

from __future__ import annotations

import logging

from lxml import etree

logger = logging.getLogger(__name__)

# Tags commonly worth surfacing directly without the caller walking the tree.
# Not exhaustive, not authoritative — a convenience index over ixml_raw, not
# a substitute for it. Names are lower-cased for lookup; iXML in the wild
# mixes case (CATEGORY vs Category vs category).
KNOWN_SFX_TAGS = {
    "category",
    "sub_category",
    "catid",
    "cat_id",
    "fx_name",
    "library",
    "creator_id",
    "source_id",
    "user_category",
    "vendor_category",
}


class IxmlParseError(Exception):
    pass


def _element_to_obj(elem: etree._Element):
    """Recursively convert an lxml element to a plain dict/str tree.
    Leaf elements (no children) become their stripped text. Elements with
    repeated child tags (e.g. multiple <TRACK> under <TRACK_LIST>) become a
    list under that tag instead of clobbering earlier entries.
    """
    children = [c for c in elem if isinstance(c.tag, str)]  # skip comments/PIs
    if not children:
        return (elem.text or "").strip()

    result: dict = {}
    for child in children:
        tag = child.tag
        value = _element_to_obj(child)
        if tag in result:
            existing = result[tag]
            if isinstance(existing, list):
                existing.append(value)
            else:
                result[tag] = [existing, value]
        else:
            result[tag] = value
    return result


def parse(raw: bytes) -> dict:
    """Parse an iXML chunk payload into a nested dict, tag names as-is.
    Uses lxml's recovering parser so malformed vendor XML degrades to
    "whatever could be salvaged" instead of raising.
    """
    parser = etree.XMLParser(recover=True, resolve_entities=False)
    try:
        root = etree.fromstring(raw, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise IxmlParseError(f"iXML payload unparseable even in recovery mode: {exc}") from exc

    if root is None:
        raise IxmlParseError("iXML payload produced no root element (empty or entirely malformed)")

    if parser.error_log:
        logger.warning(
            "iXML payload had %d recoverable XML error(s); salvaged what lxml could parse",
            len(parser.error_log),
        )

    return {root.tag: _element_to_obj(root)}


def flatten_leaves(tree: dict) -> dict[str, str | list[str]]:
    """Flatten every leaf value in a parsed iXML tree into a single
    {tag_name: value} dict, regardless of nesting depth. Tag name collisions
    across different branches (e.g. PROJECT appearing both at top level and
    inside an ASWG block) collect into a list rather than overwriting —
    ambiguity is surfaced, not silently resolved.
    """
    flat: dict[str, str | list[str]] = {}

    def _walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, str):
                    _add(key, value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            _add(key, item)
                        else:
                            _walk(item)
                elif isinstance(value, dict):
                    _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    def _add(key: str, value: str):
        if key in flat:
            existing = flat[key]
            if isinstance(existing, list):
                existing.append(value)
            else:
                flat[key] = [existing, value]
        else:
            flat[key] = value

    _walk(tree)
    return flat


def extract_sfx_fields(tree: dict) -> dict[str, str]:
    """Convenience lookup over the known ASWG sound-effects tag set. Case-
    insensitive by tag name since vendors vary (CATEGORY vs Category).
    Returns only tags that were actually present — never fabricates keys.
    """
    flat = flatten_leaves(tree)
    lowered = {k.lower(): v for k, v in flat.items()}
    return {tag: lowered[tag] for tag in KNOWN_SFX_TAGS if tag in lowered and isinstance(lowered[tag], str)}


# Confirmed against a real commercial library (BOOM Library Doors, authored
# by Soundminer): the ASWG tag scheme above is not universal. This vendor's
# iXML has zero ASWG tags at all — instead it nests a generic
# <ATTR_LIST><ATTR TYPE="string" NAME="MediaCategoryPost" VALUE="DOORS"/>...
# </ATTR_LIST> structure (a Steinberg/WaveLab convention), where the
# semantic field name is itself a VALUE rather than an XML tag. flatten_leaves
# can't surface this — "category" never appears as a tag name, it's buried
# as one NAME/VALUE pair among many identically-shaped ATTR siblings. This
# walks the whole tree for any ATTR_LIST, wherever it's nested, and turns it
# into an ordinary {NAME: VALUE} dict.
_STEINBERG_SFX_ALIASES = {
    "category": ("MediaCategoryPost", "MusicalCategory"),
    "library": ("MediaLibrary",),
    "vendor": ("MediaLibraryManufacturerName", "MediaArtist"),
}


def extract_attr_list_pairs(tree: dict) -> dict[str, str]:
    """Flattens every ATTR_LIST/ATTR{NAME,VALUE} structure found anywhere in
    the tree into a single {NAME: VALUE} dict. A NAME seen more than once
    with different values keeps the first and logs rather than raising —
    ambiguous vendor data shouldn't block extraction of everything else.
    """
    pairs: dict[str, str] = {}

    def _walk(node):
        if isinstance(node, dict):
            attr_list = node.get("ATTR_LIST")
            if isinstance(attr_list, dict):
                attrs = attr_list.get("ATTR")
                entries = attrs if isinstance(attrs, list) else [attrs] if isinstance(attrs, dict) else []
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    name, value = entry.get("NAME"), entry.get("VALUE")
                    if isinstance(name, str) and isinstance(value, str):
                        if name in pairs and pairs[name] != value:
                            logger.debug("ATTR_LIST key %r seen twice with differing values — keeping first", name)
                            continue
                        pairs[name] = value
            for child in node.values():
                _walk(child)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(tree)
    return pairs


def extract_steinberg_sfx_fields(tree: dict) -> dict[str, str]:
    """Convenience lookup mapping known Steinberg ATTR_LIST attribute names
    to the same canonical field names extract_sfx_fields uses, so callers
    (metaindex.indexer) can try both without caring which vendor scheme a given
    file happens to use.
    """
    attrs = extract_attr_list_pairs(tree)
    result = {}
    for canonical, source_names in _STEINBERG_SFX_ALIASES.items():
        for name in source_names:
            if name in attrs:
                result[canonical] = attrs[name]
                break
    return result

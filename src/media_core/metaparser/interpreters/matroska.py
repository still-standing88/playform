"""Matroska (MKV/MKA) / WebM interpreter, built on metaparser.chunks.ebml_walker.

Element IDs and their meaning come from the public EBML/Matroska
specification (https://www.matroska.org/technical/specs/index.html), the
standard wire-format IDs (marker bit included) used by every implementation —
not copied from any single tool's source. See ../../CREDITS.md for how
ExifTool's Matroska.pm was used as a cross-check during development.

Scoped to what this project's indexing/search use case needs: Segment/Info
(title, duration, muxer), Tags/Tag/SimpleTag (arbitrary key/value pairs,
walked generically — not a hardcoded field whitelist, same rule iXML follows),
and Tracks (per-track codec/language/audio format). Elements outside that
scope are still walked and kept under their raw hex ID rather than dropped,
mirroring list_info.py's "nothing gets silently dropped" rule for unrecognized
RIFF fourCCs.

Matches ExifTool's own documented default behavior: stops at the first
Cluster element (the actual, potentially huge, media payload — not metadata)
rather than reading the whole file. A Tags block placed after the first
Cluster (legal but unusual) won't be seen; that's a known, precedented
limitation, not an oversight.
"""

from __future__ import annotations

import logging
import struct

from media_core.metaparser.chunks import ebml_walker
from media_core.metaparser.interpreters._text import decode_lenient

logger = logging.getLogger(__name__)

# EBML/Matroska element IDs -> friendly names.
ELEMENT_NAMES: dict[int, str] = {
    0x1A45DFA3: "EBML",
    0x4286: "EBMLVersion",
    0x42F7: "EBMLReadVersion",
    0x42F2: "EBMLMaxIDLength",
    0x42F3: "EBMLMaxSizeLength",
    0x4282: "DocType",
    0x4287: "DocTypeVersion",
    0x4285: "DocTypeReadVersion",
    0x18538067: "Segment",
    0x1549A966: "Info",
    0x2AD7B1: "TimecodeScale",
    0x4489: "Duration",
    0x4461: "DateUTC",
    0x7BA9: "Title",
    0x4D80: "MuxingApp",
    0x5741: "WritingApp",
    0x1654AE6B: "Tracks",
    0xAE: "TrackEntry",
    0xD7: "TrackNumber",
    0x73C5: "TrackUID",
    0x83: "TrackType",
    0x86: "CodecID",
    0x258688: "CodecName",
    0x536E: "Name",
    0x22B59C: "Language",
    0x88: "FlagDefault",
    0xE1: "Audio",
    0xB5: "SamplingFrequency",
    0x9F: "Channels",
    0x6264: "BitDepth",
    0xE0: "Video",
    0xB0: "PixelWidth",
    0xBA: "PixelHeight",
    0x1254C367: "Tags",
    0x7373: "Tag",
    0x63C0: "Targets",
    0x68CA: "TargetTypeValue",
    0x63CA: "TargetType",
    0x67C8: "SimpleTag",
    0x45A3: "TagName",
    0x447A: "TagLanguage",
    0x4484: "TagDefault",
    0x4487: "TagString",
    0x4485: "TagBinary",
    0xEC: "Void",
    0xBF: "CRC-32",
}

# Payload is itself a sequence of child elements — walked recursively.
# SimpleTag nests recursively (a SimpleTag can contain child SimpleTags) per spec.
_MASTER_ELEMENT_IDS = {
    0x1A45DFA3,  # EBML
    0x18538067,  # Segment
    0x1549A966,  # Info
    0x1654AE6B,  # Tracks
    0xAE,  # TrackEntry
    0xE0,  # Video
    0xE1,  # Audio
    0x1254C367,  # Tags
    0x7373,  # Tag
    0x63C0,  # Targets
    0x67C8,  # SimpleTag
}

# Media payload, not metadata — never recurse. Matches ExifTool's own
# documented default ("extracts tags only up to the first Cluster").
CLUSTER_ID = 0x1F43B675

_STRING_ELEMENT_IDS = {
    0x4282,  # DocType
    0x7BA9,  # Title
    0x4D80,  # MuxingApp
    0x5741,  # WritingApp
    0x86,  # CodecID
    0x258688,  # CodecName
    0x536E,  # Name
    0x22B59C,  # Language
    0x63CA,  # TargetType
    0x45A3,  # TagName
    0x447A,  # TagLanguage
    0x4487,  # TagString
}

_UINT_ELEMENT_IDS = {
    0x4286, 0x42F7, 0x42F2, 0x42F3, 0x4287, 0x4285,
    0x2AD7B1, 0x4461, 0xD7, 0x73C5, 0x83, 0x88, 0x9F, 0x6264,
    0xB0, 0xBA, 0x68CA, 0x4484,
}

_FLOAT_ELEMENT_IDS = {
    0x4489,  # Duration
    0xB5,  # SamplingFrequency
}


class MatroskaParseError(Exception):
    pass


def _key_for(element_id: int) -> str:
    return ELEMENT_NAMES.get(element_id, f"0x{element_id:X}")


def _decode_float(raw: bytes) -> float | None:
    if len(raw) == 4:
        return struct.unpack(">f", raw)[0]
    if len(raw) == 8:
        return struct.unpack(">d", raw)[0]
    return None


def _decode_value(element_id: int, raw: bytes):
    if element_id in _STRING_ELEMENT_IDS:
        return decode_lenient(raw.split(b"\x00", 1)[0]).strip()
    if element_id in _FLOAT_ELEMENT_IDS:
        return _decode_float(raw)
    if element_id in _UINT_ELEMENT_IDS:
        return int.from_bytes(raw, "big") if raw else None
    return raw


def _walk_tree(data: bytes, depth: int = 0, max_depth: int = 8) -> dict:
    """Recursively walks `data` as a flat EBML element sequence, expanding
    known master elements into nested dicts and stopping at Cluster or
    max_depth (defensive termination guard against malformed files — real
    Matroska nesting never goes this deep). Repeated sibling tags (multiple
    SimpleTag/TrackEntry) collect into a list rather than overwriting, same
    rule the iXML tree builder follows.
    """
    result: dict = {}
    if depth > max_depth:
        logger.warning("EBML nesting exceeded max_depth=%d — stopping recursion here", max_depth)
        return result

    for element in ebml_walker.walk(data):
        if element.element_id == CLUSTER_ID:
            logger.debug("reached Cluster element — stopping (media data, not metadata)")
            break

        key = _key_for(element.element_id)
        if element.element_id in _MASTER_ELEMENT_IDS:
            value = _walk_tree(element.raw, depth + 1, max_depth)
        else:
            value = _decode_value(element.element_id, element.raw)

        if key in result:
            existing = result[key]
            if isinstance(existing, list):
                existing.append(value)
            else:
                result[key] = [existing, value]
        else:
            result[key] = value

    return result


def parse(data: bytes) -> dict:
    """Parses a Matroska/WebM file's EBML structure into a nested dict,
    stopping before the first Cluster. `data` is the file's bytes (or at
    minimum everything up to the first Cluster).
    """
    if not ebml_walker.is_ebml(data):
        raise MatroskaParseError("not an EBML file (missing EBML header magic 0x1A45DFA3)")
    return _walk_tree(data)


def _first(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _segment(tree: dict) -> dict:
    segment = _first(tree.get("Segment"))
    return segment if isinstance(segment, dict) else {}


def extract_info(tree: dict) -> dict:
    """Segment/Info fields — title, duration, muxing/writing app — as a flat
    {name: value} dict. Returns {} if no Info block was found.

    'Duration' is left exactly as the element stores it: a raw tick count in
    units of 'TimecodeScale' (nanoseconds per tick), NOT literal seconds —
    faithful to what's actually in the file, matching this project's raw-
    blob philosophy elsewhere. Use extract_duration_secs() below for the
    converted value; don't read this key as seconds directly.
    """
    info = _first(_segment(tree).get("Info"))
    return info if isinstance(info, dict) else {}


DEFAULT_TIMECODE_SCALE_NS = 1_000_000  # 1ms/tick — the spec's default when TimecodeScale is absent


def extract_duration_secs(tree: dict) -> float | None:
    """Converts Segment/Info's Duration (a tick count) into seconds using
    the file's own TimecodeScale (defaulting to 1ms/tick per spec when that
    element isn't present). Returns None if there's no Duration to convert.
    """
    info = extract_info(tree)
    duration_ticks = info.get("Duration")
    if not isinstance(duration_ticks, (int, float)):
        return None
    timecode_scale = info.get("TimecodeScale")
    if not isinstance(timecode_scale, (int, float)):
        timecode_scale = DEFAULT_TIMECODE_SCALE_NS
    return duration_ticks * timecode_scale / 1_000_000_000


def extract_tags(tree: dict) -> dict[str, str]:
    """Flattens every Tags/Tag/SimpleTag block into a single
    {TagName: TagString} dict. A SimpleTag missing a TagString (binary-only)
    is skipped. TagName collisions keep the first occurrence and log rather
    than raising, same rule ixml.py's ATTR_LIST flattening follows.
    """
    result: dict[str, str] = {}
    tags_block = _first(_segment(tree).get("Tags"))
    if not isinstance(tags_block, dict):
        return result

    tag_entries = tags_block.get("Tag")
    tag_entries = tag_entries if isinstance(tag_entries, list) else [tag_entries] if tag_entries else []

    for tag in tag_entries:
        if not isinstance(tag, dict):
            continue
        simple_tags = tag.get("SimpleTag")
        simple_tags = simple_tags if isinstance(simple_tags, list) else [simple_tags] if simple_tags else []
        for simple_tag in simple_tags:
            if not isinstance(simple_tag, dict):
                continue
            name, value = simple_tag.get("TagName"), simple_tag.get("TagString")
            if isinstance(name, str) and isinstance(value, str):
                if name in result and result[name] != value:
                    logger.debug("Matroska TagName %r seen twice with differing values — keeping first", name)
                    continue
                result[name] = value

    return result


def extract_tracks(tree: dict) -> list[dict]:
    """One dict per TrackEntry with whatever of {track_type, codec_id, name,
    language, sampling_frequency, channels} was present — never fabricates
    fields that weren't in the file."""
    tracks_block = _first(_segment(tree).get("Tracks"))
    entries = tracks_block.get("TrackEntry") if isinstance(tracks_block, dict) else None
    entries = entries if isinstance(entries, list) else [entries] if entries else []

    tracks = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        track: dict = {}
        for field, key in (("TrackType", "track_type"), ("CodecID", "codec_id"),
                            ("Name", "name"), ("Language", "language")):
            if field in entry:
                track[key] = entry[field]
        audio = entry.get("Audio")
        if isinstance(audio, dict):
            if "SamplingFrequency" in audio:
                track["sampling_frequency"] = audio["SamplingFrequency"]
            if "Channels" in audio:
                track["channels"] = audio["Channels"]
        tracks.append(track)

    return tracks

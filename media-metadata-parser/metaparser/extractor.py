"""Top-level orchestrator: sniff format, route to the right walker/
interpreters, assemble a models.RawFileMetadata. This is the only module
callers (db.indexer, cli) should need to import directly.

Every interpreter call is wrapped so a single bad chunk records an error and
moves on instead of aborting the whole file — per plan.md, "never let
failure to parse one chunk kill the whole file's extraction."
"""

from __future__ import annotations

import logging
from pathlib import Path

from metaparser import models
from metaparser.chunks import iff_walker, rf64, riff_walker
from metaparser.chunks.riff_walker import RawChunk
from metaparser.interpreters import bext, ixml, list_info, opportunistic
from metaparser.tags import audio_tags, video_tags
from metaparser.ucs import filename_parser

logger = logging.getLogger(__name__)

# .avi is deliberately here, not in _VIDEO_EXTENSIONS: AVI is itself a RIFF
# container (form type "AVI " instead of "WAVE"), so it gets its metadata
# (the same LIST/INFO title/artist/comment convention WAV uses) from this
# package's own RIFF walker below — no need for mutagen or any external
# tool for the container types this package can already parse natively.
_CHUNK_WALKER_EXTENSIONS = {".wav", ".wave", ".aif", ".aiff", ".aifc", ".avi"}
_VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".wmv", ".asf", ".mkv", ".webm"}

# bext/iXML chunk ids show up with inconsistent casing across vendors
# ('iXML', 'IXML', 'ixml'). Compare lower-cased, but chunk_id is preserved
# as-read everywhere it's stored.
_BEXT_ID = "bext"
_IXML_IDS = {"ixml"}
_AXML_ID = "axml"
_CUE_ID = "cue "
_LIST_ID = "list"


class ExtractionError(Exception):
    pass


def extract(path: str | Path) -> models.RawFileMetadata:
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in _CHUNK_WALKER_EXTENSIONS:
        return _extract_chunked(path)
    if suffix in _VIDEO_EXTENSIONS:
        return _extract_video(path)
    return _extract_tagged_audio(path)


def _extract_chunked(path: Path) -> models.RawFileMetadata:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ExtractionError(f"could not read {path}: {exc}") from exc

    errors: list[str] = []

    if rf64.is_rf64(data):
        # Must be checked before is_riff(): RF64/BW64 has its own magic
        # ("RF64"/"BW64"), disjoint from plain RIFF's ("RIFF") — the two are
        # mutually exclusive on the same 4 bytes, so this can't be nested
        # inside the is_riff() branch below (that ordering was a bug: it
        # made this branch unreachable and every real RF64/BW64 file fell
        # through to the "unknown format" case at the bottom).
        file_format = "rf64"
        try:
            chunks = rf64.walk(data)
        except rf64.Rf64ParseError as exc:
            errors.append(f"rf64 walk failed: {exc}")
            chunks = []
    elif riff_walker.is_riff(data):
        # RIFF's form type (offset 8-12) distinguishes WAVE from AVI ("AVI "
        # padded with a trailing space) — both are walked identically since
        # the chunk-level shape is the same, only the label differs.
        form = (riff_walker.form_type(data) or "").strip().upper()
        file_format = "avi" if form == "AVI" else "wav"
        try:
            chunks = riff_walker.walk(data)
        except riff_walker.RiffParseError as exc:
            errors.append(f"riff walk failed: {exc}")
            chunks = []
    elif iff_walker.is_iff(data):
        file_format = "aiff"
        try:
            chunks = iff_walker.walk(data)
        except iff_walker.IffParseError as exc:
            errors.append(f"iff walk failed: {exc}")
            chunks = []
    else:
        errors.append("file has neither RIFF/RF64 nor FORM magic despite chunk-walkable extension")
        file_format = "unknown"
        chunks = []

    meta = models.RawFileMetadata(file_path=str(path), file_format=file_format, errors=errors)
    _process_chunks(chunks, meta)

    # Plain ID3-in-RIFF / ID3-in-AIFF tags (title/artist/etc) as a
    # supplementary source — mutagen handles both containers' tag schemes.
    try:
        plain_tags = audio_tags.extract(path)
        if plain_tags:
            meta.tags_raw = plain_tags
    except Exception as exc:  # defensive: audio_tags.extract already catches broadly, but never let this be fatal
        meta.errors.append(f"supplementary tag extraction failed: {exc}")

    ucs_result = filename_parser.parse_filename(path)
    meta.ucs_from_filename = _ucs_result_to_dict(ucs_result)

    if meta.ixml_raw is not None and meta.ucs_from_filename is not None:
        sfx_fields = ixml.extract_sfx_fields(meta.ixml_raw)
        meta.ucs_ixml_cross_check = filename_parser.cross_check_against_ixml(ucs_result, sfx_fields)

    return meta


def _process_chunks(chunks: list[RawChunk], meta: models.RawFileMetadata) -> None:
    for chunk in chunks:
        chunk_key = chunk.chunk_id.strip().lower()

        try:
            if chunk_key == _BEXT_ID:
                meta.bext_raw = bext.to_raw_dict(bext.parse(chunk.raw))

            elif chunk_key in _IXML_IDS:
                meta.ixml_raw = ixml.parse(chunk.raw)

            elif chunk_key == _AXML_ID:
                meta.axml_raw = opportunistic.parse_axml(chunk.raw)

            elif chunk_key == _CUE_ID:
                meta.cue_points = opportunistic.parse_cue(chunk.raw)

            elif chunk_key == _LIST_ID:
                _process_list_chunk(chunk, meta)

        except Exception as exc:
            # Broad on purpose: a single interpreter throwing must not take
            # the rest of the file's chunks down with it.
            meta.errors.append(f"chunk {chunk.chunk_id!r} at offset {chunk.offset} failed to parse: {exc}")
            logger.warning("chunk %r failed to parse for a file: %s", chunk.chunk_id, exc)


def _process_list_chunk(chunk: RawChunk, meta: models.RawFileMetadata) -> None:
    if len(chunk.raw) < 4:
        meta.errors.append("LIST chunk too short to contain a list type")
        return

    list_type = chunk.raw[0:4].decode("ascii", errors="replace")
    if list_type == "INFO":
        meta.info_raw = list_info.parse_info(chunk.raw)
    elif list_type == "adtl":
        meta.adtl_labels = opportunistic.parse_adtl(chunk.raw)
    else:
        logger.debug("unhandled LIST type %r — not INFO or adtl, skipping", list_type)


def _extract_video(path: Path) -> models.RawFileMetadata:
    tags = video_tags.extract(path)
    meta = models.RawFileMetadata(file_path=str(path), file_format=tags.get("format", "unknown_video"), tags_raw=tags)
    meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))
    return meta


def _extract_tagged_audio(path: Path) -> models.RawFileMetadata:
    tags = audio_tags.extract(path)
    meta = models.RawFileMetadata(file_path=str(path), file_format=tags.get("format", "unknown_audio"), tags_raw=tags)
    meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))
    return meta


def _ucs_result_to_dict(result: filename_parser.UcsFilenameResult) -> dict | None:
    if result.cat_id is None and not any((result.fx_name, result.creator_id, result.source_id)):
        return None
    return {
        "cat_id": result.cat_id,
        "fx_name": result.fx_name,
        "creator_id": result.creator_id,
        "source_id": result.source_id,
        "user_data": result.user_data,
        "raw_tokens": result.raw_tokens,
        "category": result.category_entry.category if result.category_entry else None,
        "subcategory": result.category_entry.subcategory if result.category_entry else None,
    }

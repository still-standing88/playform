"""Top-level orchestrator: sniff format, route to the right walker/
interpreters, assemble a models.RawFileMetadata. This is the only module
callers (metaindex.indexer, cli) should need to import directly.

Every interpreter call is wrapped so a single bad chunk records an error and
moves on instead of aborting the whole file — per plan.md, "never let
failure to parse one chunk kill the whole file's extraction."
"""

from __future__ import annotations

import logging
from pathlib import Path

from media_core.metaparser import models
from media_core.metaparser.chunks import (
    amr_walker,
    caf_walker,
    dts_walker,
    dv_walker,
    ebml_walker,
    flv_walker,
    iff_walker,
    mp4_walker,
    mpeg_walker,
    realmedia_walker,
    rf64,
    riff_walker,
    ts_walker,
)
from media_core.metaparser.chunks.riff_walker import RawChunk
from media_core.metaparser.interpreters import (
    amr,
    bext,
    caf,
    dts,
    dv,
    flash_video,
    ixml,
    list_info,
    m2ts,
    matroska,
    mpeg,
    opportunistic,
    quicktime_udta,
    realmedia,
)
from media_core.metaparser.tags import audio_tags, video_tags
from media_core.metaparser.ucs import filename_parser

logger = logging.getLogger(__name__)

# .avi is deliberately here, not in _VIDEO_EXTENSIONS: AVI is itself a RIFF
# container (form type "AVI " instead of "WAVE"), so it gets its metadata
# (the same LIST/INFO title/artist/comment convention WAV uses) from this
# package's own RIFF walker below — no need for mutagen or any external
# tool for the container types this package can already parse natively.
_CHUNK_WALKER_EXTENSIONS = {".wav", ".wave", ".aif", ".aiff", ".aifc", ".avi", ".divx"}
# Matroska/WebM: same reasoning as AVI above — EBML is a different binary
# shape from RIFF/IFF, so it gets its own walker (metaparser.chunks.ebml_walker)
# instead of going through mutagen (which has no MKV/WebM support at all).
_EBML_WALKER_EXTENSIONS = {".mkv", ".mka", ".webm"}
# .ra (RealAudio) is the same RMFF container as .rm/.rmvb, just an
# audio-only encoder convention for the file extension — no separate walker
# needed, it's already the exact format realmedia_walker.py reads.
_REALMEDIA_EXTENSIONS = {".rm", ".rmvb", ".ra"}
# .f4v is deliberately NOT here: despite the "flv" lineage in the name, F4V
# is Adobe's later ISO-BMFF (MP4-family) container, not the classic FLV
# tag-stream format this walker reads — real .f4v files start with an MP4
# 'ftyp' box, not "FLV" magic, so they're routed through _VIDEO_EXTENSIONS
# (mutagen's MP4 reader) alongside .mp4/.m4v/.mov instead.
_FLV_EXTENSIONS = {".flv"}
# .mp1/.mp2 (MPEG audio Layers I/II) and .vob (DVD Video Object, which is
# just MPEG Program Stream under a different extension convention) are all
# the exact same underlying format mpeg_walker.py/mpeg.py already read —
# mutagen's mp3 module is Layer III (MP3) only, so .mp1/.mp2 would otherwise
# get no metadata at all despite this project already having the decoder.
_MPEG_EXTENSIONS = {".mpg", ".mpeg", ".m2v", ".mp1", ".mp2", ".vob"}
_M2TS_EXTENSIONS = {".ts", ".m2ts", ".mts"}
_DV_EXTENSIONS = {".dv"}
_AMR_EXTENSIONS = {".amr"}
_CAF_EXTENSIONS = {".caf"}
_DTS_EXTENSIONS = {".dts"}
# ISO-BMFF (MP4-family) extensions where the legacy pre-ilst udta text-atom
# walker is worth running as a supplementary source alongside mutagen. .wmv/
# .asf are ASF-family, not ISO-BMFF, so they're excluded from that walk (see
# _extract_video) despite being routed through the same mutagen-based path.
_VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".wmv", ".asf", ".f4v", ".3gp", ".3g2"}
_ISO_BMFF_EXTENSIONS = {".mp4", ".m4v", ".mov", ".f4v", ".3gp", ".3g2"}

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
    if suffix in _EBML_WALKER_EXTENSIONS:
        return _extract_ebml(path)
    if suffix in _REALMEDIA_EXTENSIONS:
        return _extract_realmedia(path)
    if suffix in _FLV_EXTENSIONS:
        return _extract_flv(path)
    if suffix in _MPEG_EXTENSIONS:
        return _extract_mpeg(path)
    if suffix in _M2TS_EXTENSIONS:
        return _extract_m2ts(path)
    if suffix in _DV_EXTENSIONS:
        return _extract_dv(path)
    if suffix in _AMR_EXTENSIONS:
        return _extract_amr(path)
    if suffix in _CAF_EXTENSIONS:
        return _extract_caf(path)
    if suffix in _DTS_EXTENSIONS:
        return _extract_dts(path)
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


def _extract_ebml(path: Path) -> models.RawFileMetadata:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ExtractionError(f"could not read {path}: {exc}") from exc

    if not ebml_walker.is_ebml(data):
        meta = models.RawFileMetadata(
            file_path=str(path),
            file_format="unknown",
            errors=["file has no EBML magic (0x1A45DFA3) despite EBML-walkable extension"],
        )
        meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))
        return meta

    errors: list[str] = []
    try:
        tree = matroska.parse(data)
    except matroska.MatroskaParseError as exc:
        errors.append(f"matroska parse failed: {exc}")
        tree = {}

    ebml_header = tree.get("EBML") if tree else None
    if isinstance(ebml_header, list):
        ebml_header = ebml_header[0] if ebml_header else {}
    doc_type = ebml_header.get("DocType") if isinstance(ebml_header, dict) else None
    file_format = "webm" if isinstance(doc_type, str) and doc_type.lower() == "webm" else "matroska"

    meta = models.RawFileMetadata(file_path=str(path), file_format=file_format, errors=errors)
    if tree:
        meta.matroska_raw = tree

    # mutagen has no MKV/WebM support at all today, so this is currently a
    # no-op for these extensions — kept for consistency with the WAV/AIFF
    # supplementary-tag call in _extract_chunked, and picks up mutagen
    # support automatically if it's ever added upstream.
    try:
        plain_tags = audio_tags.extract(path)
        if plain_tags:
            meta.tags_raw = plain_tags
    except Exception as exc:  # defensive: audio_tags.extract already catches broadly, but never let this be fatal
        meta.errors.append(f"supplementary tag extraction failed: {exc}")

    meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))

    return meta


def _extract_realmedia(path: Path) -> models.RawFileMetadata:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ExtractionError(f"could not read {path}: {exc}") from exc

    if not realmedia_walker.is_realmedia(data):
        meta = models.RawFileMetadata(
            file_path=str(path),
            file_format="unknown",
            errors=["file has no '.RMF' magic despite RealMedia extension"],
        )
        meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))
        return meta

    errors: list[str] = []
    try:
        tree = realmedia.parse(data)
    except realmedia_walker.RealMediaParseError as exc:
        errors.append(f"realmedia walk failed: {exc}")
        tree = {}

    meta = models.RawFileMetadata(
        file_path=str(path),
        file_format="rmvb" if path.suffix.lower() == ".rmvb" else "realmedia",
        errors=errors,
    )
    if tree:
        meta.realmedia_raw = tree

    meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))
    return meta


def _extract_flv(path: Path) -> models.RawFileMetadata:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ExtractionError(f"could not read {path}: {exc}") from exc

    if not flv_walker.is_flv(data):
        meta = models.RawFileMetadata(
            file_path=str(path),
            file_format="unknown",
            errors=["file has no 'FLV' magic despite .flv extension"],
        )
        meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))
        return meta

    errors: list[str] = []
    try:
        summary = flash_video.parse(data)
    except flv_walker.FlvParseError as exc:
        errors.append(f"flv walk failed: {exc}")
        summary = None

    meta = models.RawFileMetadata(file_path=str(path), file_format="flv", errors=errors)
    if summary:
        meta.flv_raw = summary

    meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))
    return meta


def _extract_mpeg(path: Path) -> models.RawFileMetadata:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ExtractionError(f"could not read {path}: {exc}") from exc

    summary = mpeg.parse(data)
    errors: list[str] = []
    if not summary:
        errors.append("no recognizable MPEG audio frame sync or video sequence header found")

    meta = models.RawFileMetadata(file_path=str(path), file_format="mpeg", errors=errors)
    if summary:
        meta.mpeg_raw = summary

    meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))
    return meta


def _extract_m2ts(path: Path) -> models.RawFileMetadata:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ExtractionError(f"could not read {path}: {exc}") from exc

    if not ts_walker.is_transport_stream(data):
        meta = models.RawFileMetadata(
            file_path=str(path),
            file_format="unknown",
            errors=["no MPEG-TS sync pattern found despite .ts/.m2ts/.mts extension"],
        )
        meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))
        return meta

    errors: list[str] = []
    try:
        summary = m2ts.parse(data)
    except ts_walker.TsParseError as exc:
        errors.append(f"m2ts walk failed: {exc}")
        summary = None

    meta = models.RawFileMetadata(file_path=str(path), file_format="m2ts", errors=errors)
    if summary:
        meta.m2ts_raw = summary

    meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))
    return meta


def _extract_dv(path: Path) -> models.RawFileMetadata:
    try:
        data = path.read_bytes()
        file_size = path.stat().st_size
    except OSError as exc:
        raise ExtractionError(f"could not read {path}: {exc}") from exc

    errors: list[str] = []
    try:
        summary = dv.parse(data, file_size=file_size)
    except dv.DvParseError as exc:
        errors.append(f"dv parse failed: {exc}")
        summary = None

    meta = models.RawFileMetadata(file_path=str(path), file_format="dv", errors=errors)
    if summary:
        meta.dv_raw = summary

    meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))
    return meta


def _extract_amr(path: Path) -> models.RawFileMetadata:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ExtractionError(f"could not read {path}: {exc}") from exc

    errors: list[str] = []
    try:
        summary = amr.parse(data)
    except amr_walker.AmrParseError as exc:
        errors.append(f"amr parse failed: {exc}")
        summary = None

    meta = models.RawFileMetadata(file_path=str(path), file_format="amr", errors=errors)
    if summary:
        meta.amr_raw = summary

    meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))
    return meta


def _extract_caf(path: Path) -> models.RawFileMetadata:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ExtractionError(f"could not read {path}: {exc}") from exc

    if not caf_walker.is_caf(data):
        meta = models.RawFileMetadata(
            file_path=str(path),
            file_format="unknown",
            errors=["file has no 'caff' magic despite .caf extension"],
        )
        meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))
        return meta

    errors: list[str] = []
    try:
        summary = caf.parse(data)
    except caf_walker.CafParseError as exc:
        errors.append(f"caf walk failed: {exc}")
        summary = None

    meta = models.RawFileMetadata(file_path=str(path), file_format="caf", errors=errors)
    if summary:
        meta.caf_raw = summary

    meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))
    return meta


def _extract_dts(path: Path) -> models.RawFileMetadata:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ExtractionError(f"could not read {path}: {exc}") from exc

    errors: list[str] = []
    try:
        summary = dts.parse(data)
    except dts.DtsInterpretError as exc:
        errors.append(f"dts parse failed: {exc}")
        summary = None

    meta = models.RawFileMetadata(file_path=str(path), file_format="dts", errors=errors)
    if summary:
        meta.dts_raw = summary

    meta.ucs_from_filename = _ucs_result_to_dict(filename_parser.parse_filename(path))
    return meta


def _extract_video(path: Path) -> models.RawFileMetadata:
    tags = video_tags.extract(path)
    meta = models.RawFileMetadata(file_path=str(path), file_format=tags.get("format", "unknown_video"), tags_raw=tags)

    # Supplementary: closes the specific gap mutagen's ilst-only MP4 reader
    # has for pre-iTunes QuickTime files (see quicktime_udta.py's docstring).
    # Best-effort and never fatal to the primary mutagen-based extraction —
    # a udta walk failure just means this project's own bonus source is
    # unavailable, not that the whole file's extraction should fail.
    if path.suffix.lower() in _ISO_BMFF_EXTENSIONS:
        try:
            data = path.read_bytes()
            if mp4_walker.is_iso_bmff(data):
                udta = quicktime_udta.parse(data)
                if udta:
                    meta.udta_raw = udta
        except Exception as exc:
            meta.errors.append(f"udta extraction failed: {exc}")

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

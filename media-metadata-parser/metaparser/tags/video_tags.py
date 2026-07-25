"""Video container metadata extraction — mutagen only, no external tools.

mutagen covers MP4/MOV (its `mp4` module reads iTunes-style `ilst` atoms)
and ASF/WMV natively. It has no Matroska (MKV) or WebM support, and no AVI
support either — but AVI is itself a RIFF container (form type "AVI "
instead of "WAVE"), so it's routed through metaparser.extractor's own
RIFF chunk walker instead of landing here at all; that gets its LIST/INFO
metadata (the same title/artist/comment convention WAV uses) from this
package's own code, not a third-party binary.

This delegates straight to tags.audio_tags.extract() rather than calling
mutagen directly — there used to be a second, independent mutagen call
here that omitted `easy=True` and the ID3-frame/binary-frame normalization
audio_tags.py does. That divergence was a real bug found via testing:
ffmpeg-generated .mp4 files came back with raw atom codes (`©nam`/
`©ART`) here while audio_tags.py's path on the same container type
correctly returned friendly `title`/`artist` keys. One tag-normalization
implementation, used everywhere, so behavior can't silently diverge by
which code path a given extension happens to take.

Known gap (confirmed via ExifTool as a dev-time diagnostic, not a runtime
dependency): classic QuickTime `.mov` files can carry metadata in a `udta`
box structure that predates the `ilst`/iTunes convention — mutagen's MP4
reader doesn't parse that older structure, so such files come back with no
tags even though the data is genuinely present in the file. Confirmed
against an ffmpeg-generated .mov specifically. A from-scratch MP4/QuickTime
atom walker (same idea as the RIFF/IFF ones, just ISO-BMFF box shaped)
would close this; not built, since it's a bigger, separately-scoped task.

MKV/WebM (EBML-based, a fundamentally different binary structure from RIFF/
IFF) have no independent parser here yet — mutagen can't read them, and per
project policy ExifTool is a dev-time cross-check oracle only (see
exiftool_bridge.py), never a runtime dependency. Files in those two formats
come back with empty tags rather than silently reaching for the external
binary. Building a minimal EBML tag reader (Segment/Tags/Tag/SimpleTag) is
future work if real samples in these formats show up.
"""

from __future__ import annotations

import logging
from pathlib import Path

from metaparser.tags import audio_tags

logger = logging.getLogger(__name__)

# mp4/m4v/mov share one atom structure; asf covers wmv. AVI is handled by
# metaparser.extractor's RIFF path, not here — see module docstring.
_MUTAGEN_VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".wmv", ".asf"}

# No parser exists for these yet (see module docstring) — logged once per
# call at debug level so a scan over a library containing them is visibly
# explainable, without treating "no metadata" as an error.
_UNSUPPORTED_EXTENSIONS = {".mkv", ".webm"}


def extract(path: str | Path) -> dict:
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix in _UNSUPPORTED_EXTENSIONS:
        logger.debug("%s has no independent parser yet (EBML-based, not RIFF/IFF) — returning no tags", suffix)
        return {}

    return audio_tags.extract(path)

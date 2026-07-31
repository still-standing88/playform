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
would close this; not built, since it's a bigger, separately-scoped task —
see ../../supported-formats-to-be-ported.md.

MKV/WebM (EBML-based, a fundamentally different binary structure from RIFF/
IFF) no longer land here at all: metaparser.extractor routes `.mkv`/`.mka`/
`.webm` through its own EBML walker + metaparser.interpreters.matroska before
this module would ever see them — see extractor._extract_ebml.
"""

from __future__ import annotations

from pathlib import Path

from media_core.metaparser.tags import audio_tags

# mp4/m4v/mov/f4v share one atom structure (f4v is ISO-BMFF despite the FLV-
# suggestive name — see extractor._FLV_EXTENSIONS); asf covers wmv. AVI is
# handled by metaparser.extractor's RIFF path, MKV/MKA/WebM by its EBML path,
# and classic .flv by its own tag-stream path — none of those reach this module.
_MUTAGEN_VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".wmv", ".asf", ".f4v"}


def extract(path: str | Path) -> dict:
    return audio_tags.extract(Path(path))

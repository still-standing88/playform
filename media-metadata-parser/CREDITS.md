# Credits

## ExifTool

Some container formats in `metaparser/` (see
[`supported-formats-to-be-ported.md`](supported-formats-to-be-ported.md) for
the current list, starting with Matroska/EBML) were built by reading
[ExifTool](https://exiftool.org) by Phil Harvey as a specification reference
for container layout and tag-ID meaning — a copy is bundled in this repo at
`archive/exiftool` under the GNU General Public License v3
(`archive/exiftool/LICENSE`).

Two different relationships to ExifTool's source exist in this codebase,
and they're worth distinguishing precisely rather than blanket-labeling
everything the same way:

**Fresh tables, cross-checked against ExifTool as one reference among
others** — the declarative tag-ID tables in `metaparser/interpreters/`
(e.g. the EBML element-ID → friendly-name mapping in `matroska.py`, the
M2TS `stream_type`/`table_id` registries in `m2ts.py`) are written fresh in
Python, following the same *kind* of table ExifTool's own per-format modules
use (a plain `id -> {name, ...}` lookup, generically walked, unrecognized
IDs passed through raw rather than dropped) — this table shape is itself the
general, long-established way to describe compressed/id-keyed binary tag
formats and isn't unique to ExifTool. The specific ID values are genuine
spec constants (matroska.org for Matroska; ISO/IEC 13818-1 and ISO/IEC
11172-3/13818-2 for M2TS's stream types and MPEG's audio/video bitfield
tables in `mpeg.py`) — ExifTool was used to cross-check the reading, not as
the original source of the values.

**Direct, disclosed transliteration** — `metaparser/interpreters/dv.py` and
`metaparser/chunks/dv_walker.py` are the one exception: DV's raw bitstream
layout (DIF block byte offsets, VAUX/AAUX pack field positions) has no
public specification this project holds a copy of, and no real DV sample
file exists here to validate an independent reading against. Those two
modules' byte-offset arithmetic and format-profile table are ported directly
from `archive/exiftool/lib/Image/ExifTool/DV.pm`'s own `ProcessDV` logic —
disclosed explicitly in both modules' docstrings, consistent with GPLv3
terms (Section 5: a modified/derived work carries its own notice of what was
changed, and remains available under the same license terms as the
original).

**No ExifTool involvement at all** — several modules in this codebase don't
fall into either category above, for a few different reasons, worth being
precise about rather than lumping them in by default:

- `metaparser/chunks/mp4_walker.py` and `metaparser/interpreters/quicktime_udta.py`
  (ISO-BMFF box walking + legacy pre-`ilst` QuickTime user-data text atoms)
  were built from general public knowledge of the ISO/IEC 14496-12 box format
  and the classic QTFF user-data text-atom shape — `archive/exiftool`'s
  `QuickTime.pm` (over 10,000 lines, almost entirely camera-maker-note
  decoding irrelevant to this project's audio/video-library use case) was
  **not** read or consulted for this feature.
- `metaparser/chunks/amr_walker.py` and `metaparser/interpreters/amr.py`
  (AMR frame-size tables) are sourced from RFC 4867 (IETF's public AMR RTP
  payload spec) — ExifTool has no AMR module at all to reference either way.
- `metaparser/chunks/caf_walker.py` and `metaparser/interpreters/caf.py`
  (Apple Core Audio Format) are built from Apple's own public CAF
  specification — again, no ExifTool module exists for this format.
- `metaparser/chunks/dts_walker.py` and `metaparser/interpreters/dts.py`
  (DTS Coherent Acoustics) are the most hedged module in this codebase: no
  ExifTool coverage exists, and the primary spec (ETSI TS 102 114) isn't a
  freely available document this project holds a copy of the way an IETF
  RFC is. The sync word is high-confidence (near-universally documented);
  the bitfield layout past it is reproduced from commonly-circulated
  secondary documentation, and decoding deliberately stops before fields
  (a ~30-entry bitrate table, several post-CRC fields) this project isn't
  confident enough to present as fact — see `dts_walker.py`'s and
  `dts.py`'s own docstrings for the precise boundary. This is the one
  module in this project where "unverified against a real sample" carries
  more real risk than everywhere else it's disclosed.

## mutagen

MP3/FLAC/OGG family/MP4/WavPack/APEv2/ASF/DSF/AAC/AC3/Musepack/TrueAudio/TAK
tag reading is handled entirely by [mutagen](https://mutagen.readthedocs.io/),
not reimplemented — see `metaparser/tags/audio_tags.py` and `video_tags.py`.

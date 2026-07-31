# Supported-formats audit: what's covered, what's missing, what to port

Cross-references three sources directly (not assumed):

1. PlayForm's declared format list — [`docs/source/en/documentation.md`](../docs/source/en/documentation.md)
   section 1.3.
2. `mutagen`'s actually-installed module list (checked via
   `import mutagen, os; os.listdir(os.path.dirname(mutagen.__file__))` against
   the project's own `venv`, not the PyPI docs).
3. ExifTool's per-format module list — `archive/exiftool/lib/Image/ExifTool/*.pm`
   (GPLv3, see [`archive/exiftool/LICENSE`](../archive/exiftool/LICENSE)) — used
   here purely as a **specification reference**: which container/tag-ID layout
   each format uses. No Perl source is copied; see [`CREDITS.md`](CREDITS.md)
   for how it's used and cited.

`metaparser` already covers WAV/AIFF/RF64 via its own chunk walkers
(`metaparser/chunks/`), plus everything `mutagen` reads natively: MP3 (ID3),
FLAC, OGG Vorbis/Opus/Speex/Theora/FLAC, M4A/MP4 (`ilst`), WavPack, APEv2
(Monkey's Audio), ASF/WMA, DSF/DSDIFF, AAC, AC3, Musepack, TrueAudio, TAK, SMF,
OptimFROG. That list is intentionally not reimplemented — mutagen already
solves it (per `plan.md`'s own "solved problem, don't reinvent" call).

## Gap table

| Format | Extensions | Status today | ExifTool reference module | Priority |
|---|---|---|---|---|
| Matroska / WebM | `.mkv`, `.mka`, `.webm` | **Ported.** `metaparser/chunks/ebml_walker.py` + `metaparser/interpreters/matroska.py`. | `Matroska.pm` | Done |
| RealMedia | `.rm`, `.rmvb` | **Ported.** `metaparser/chunks/realmedia_walker.py` + `metaparser/interpreters/realmedia.py` (`CONT`/`MDPR` decoded, every other object kept raw by ID). | `Real.pm` | Done |
| Flash Video | `.flv` | **Ported.** `metaparser/chunks/flv_walker.py` + `metaparser/interpreters/amf0.py` (generic AMF0 decoder, no fixed schema) + `metaparser/interpreters/flash_video.py`. **Correction from the first pass of this table:** `.f4v` was originally grouped with `.flv` here — it isn't. Despite the name, F4V is Adobe's later ISO-BMFF (MP4-family) container, not the classic FLV tag-stream format; real `.f4v` files start with an MP4 `ftyp` box. It's routed through the existing MP4/mutagen path instead (`extractor.py`'s `_VIDEO_EXTENSIONS`), not this new walker. | `Flash.pm` | Done |
| MPEG-PS / elementary | `.mpg`, `.mpeg`, `.m2v` | **Ported.** `metaparser/chunks/mpeg_walker.py` + `metaparser/interpreters/mpeg.py` — full audio-frame-header bitfield tables (5 bitrate tables, 3 sample-rate tables) and video sequence-header decode, plus Xing/LAME VBR header. These are genuine ISO 11172-3/13818-2 spec constants, not ExifTool-invented labels — worth full fidelity. | `MPEG.pm` | Done |
| MPEG-TS / M2TS | `.ts`, `.m2ts`, `.mts` | **Ported.** `metaparser/chunks/ts_walker.py` + `metaparser/interpreters/m2ts.py` — dynamic PAT/PMT stream discovery (nothing about what streams exist is assumed), full `stream_type` (40+ entries) and `table_id` registries, AC-3 descriptor decode, PCR-derived duration. **Not ported**: M2TS.pm's per-dashcam-vendor GPS/accelerometer telemetry decoders (Novatek, Innovv, Jomise, Blueskysea, ...) — explicitly marked by ExifTool's own comments as "empirical based on 1 sample" and "highly experimental" reverse-engineering of undocumented proprietary formats. Unverifiable without real samples and out of scope for general media metadata. | `M2TS.pm` | Done (partial by design) |
| DV | `.dv` | **Ported, best-effort.** `metaparser/chunks/dv_walker.py` + `metaparser/interpreters/dv.py` — full format-profile table (10 variants) plus VAUX/AAUX pack decode (date/time, aspect ratio, scan type, audio params). Byte offsets are disclosed direct transliterations of `DV.pm`'s own arithmetic (see CREDITS.md) — the DV bitstream layout isn't independently re-derivable from general knowledge with this project's usual confidence bar, and there's no real DV sample to validate an independent reading against. Only the common-case DIF sync pattern is implemented, not ExifTool's secondary fallback regex for non-standard header placement. | `DV.pm` | Done (best-effort) |
| QuickTime legacy `udta` | `.mov` (and other ISO-BMFF video: `.mp4`/`.m4v`/`.f4v`/`.3gp`/`.3g2`) | **Ported.** `metaparser/chunks/mp4_walker.py` (generic ISO-BMFF box walker) + `metaparser/interpreters/quicktime_udta.py` — decodes the legacy pre-`ilst` QTFF text-atom shape, run as a supplementary source alongside mutagen's own `ilst`-based reading, never replacing it. Confirmed live (not assumed) that mutagen's reader genuinely returns zero tags for this shape even when it correctly parses everything else about the file (stream duration, etc.) — see the regression-flavored test `test_quicktime_udta_decodes_legacy_text_atoms_mutagen_would_miss`. | `QuickTime.pm` (huge — only the `moov/udta` legacy text-atom shape is in scope, not the 10k-line module, which is mostly camera-maker-note decoding irrelevant here). | Done |
| 3GP | `.3gp`, `.3g2` | **Verified live, then wired.** Built a synthetic 3GP-shaped ISO-BMFF file and ran `mutagen.File()` on it directly: it correctly content-sniffs 3GP as MP4-family (stream duration came back exactly right) but — same as `.mov` — returns no tags for legacy `udta` text atoms. Previously these extensions weren't in `extractor.py`'s routing at all (silently fell through to the generic audio-tag path, which happened to work by accident since it calls the same mutagen function, but never got the new `udta` walk). Now explicitly routed through `_VIDEO_EXTENSIONS`/`_ISO_BMFF_EXTENSIONS`. | `QuickTime.pm` (3GP subset) | Done |
| AMR | `.amr` | **Ported, minimal by design** — AMR genuinely defines no tag/metadata mechanism (confirmed: no ExifTool module exists for it at all, the only format in this whole audit with zero ExifTool coverage to cross-check against). `metaparser/chunks/amr_walker.py` + `metaparser/interpreters/amr.py` report variant (NB/WB), frame count, and a duration estimate (every AMR frame is a fixed 20ms), per the public RFC 4867 frame-size table — stops gracefully rather than guesses on any reserved/unrecognized frame-type index. | — (no ExifTool reference; RFC 4867 is the public spec used instead) | Done |

| DTS | `.dts` | **Ported, narrow scope by design.** `metaparser/chunks/dts_walker.py` (sync word) + `metaparser/interpreters/dts.py` — frame type, block count, frame size, channel arrangement, sample rate. The one format in this whole audit with **no ExifTool module and no bundled spec** to cross-check against at all (ETSI TS 102 114 isn't public/free like an RFC); decode deliberately stops before the fields whose exact bit positions and the ~30-entry bitrate table this project doesn't hold enough confidence to present as fact — those come back as a raw, undecoded index rather than a guessed value. | — (no ExifTool reference; ETSI TS 102 114 not available to this project) | Done (intentionally partial) |
| Core Audio Format | `.caf` | **Ported.** `metaparser/chunks/caf_walker.py` + `metaparser/interpreters/caf.py` — `desc` (technical: sample rate, format, channels, bit depth) and `info` (Apple's own free-form key/value text metadata chunk, genuinely no fixed key list, walked dynamically) decoded; every other chunk kept raw by fourCC. Built from Apple's own public CAF spec, not ExifTool (no module exists for this format either). | — (no ExifTool reference; Apple's public CAF spec used instead) | Done |

A second pass also caught and fixed **extension-routing gaps for formats
this project already had full support for**, found by cross-referencing
`extractor.py`'s actual routing tables and `metaindex/indexer.py`'s scan allowlist
against PlayForm's declared list line by line, not from memory:
`.mp1`/`.mp2` (MPEG Layer I/II — same decoder as `.mpg`'s audio path) and
`.vob` (DVD Video Object — literally MPEG Program Stream) now route through
`mpeg_walker.py`/`mpeg.py`; `.ra` (RealAudio) now routes through
`realmedia_walker.py` (same RMFF container as `.rm`/`.rmvb`); `.divx` routes
through the AVI/RIFF path. Separately, `.ac3`, `.eac3`, `.tta`, `.mpc`,
`.spx`, and `.ogv` were already fully supported by `mutagen` but had never
been added to `metaindex/indexer.py`'s `SUPPORTED_EXTENSIONS` — a directory scan
was silently skipping them even though direct extraction worked fine.

Everything else in PlayForm's declared list (`.avi` via our own RIFF walker
with `AVI ` form type, `.wma`/`.wmv`/`.asf` via mutagen's `asf` module) is
already covered — verified by checking `mutagen`'s module list and
`metaparser/extractor.py`'s routing directly, not assumed.

**Roadmap status: this table is now fully worked through**, with one
deliberate exception. Every format identified in the original audit is
either already covered by mutagen or has been ported, *except* tracker/
module formats (`.s3m`, `.xm`, `.mod`, `.it`) — no mutagen support, no
ExifTool coverage, four genuinely distinct binary layouts, and minimal
metadata value even if built (at most an embedded title string). Left
undone as the one deliberately out-of-scope item, not an oversight. Future
additions to this project's format coverage beyond that should start a
fresh audit pass rather than assume this list is exhaustive of everything
PlayForm might ever encounter.

**Design note carried through every ported format above:** none of them use a
fixed field whitelist for what they extract. Matroska/RealMedia/MP4-udta keep
every unrecognized element/object/box under its raw ID rather than dropping
it; M2TS's PAT/PMT discovers whatever streams the file's own tables declare,
never assumes a fixed set; FLV's script-data metadata and RealMedia's `CONT`
distinguish the two genuinely different cases honestly — see CREDITS.md's
"Fresh tables" vs "Direct, disclosed transliteration" split (the latter is
DV only). Every walker follows the same graceful-degradation contract as the
original RIFF/IFF walkers: truncated or malformed input is logged and the
walk stops or skips that element, nothing raises past the top-level per-file
extraction call (`metaparser.extractor.extract`), so one bad file never
aborts a batch scan.

## Licensing note

The bundled `archive/exiftool` copy is GPLv3 (see its `LICENSE` file). PlayForm
is moving to GPL, so referencing ExifTool's format specs and tag-ID tables as a
design source is license-compatible, provided it's credited — see
[`CREDITS.md`](CREDITS.md) for the precise, non-uniform breakdown of what's a
fresh table cross-checked against spec constants versus DV's disclosed direct
transliteration (not every format falls into the same category, and the
credits file says so explicitly rather than making one blanket claim).

## Build order

Each format follows the same recipe established by `riff_walker.py` /
`iff_walker.py` + `list_info.py`:

1. A generic container walker in `metaparser/chunks/` — never hardcode unless
   the spec is genuinely positional binary (bext-style); log-and-skip on
   truncation, never raise.
2. A declarative tag-ID → friendly-name table in `metaparser/interpreters/`,
   with unrecognized IDs kept raw rather than dropped.
3. Synthetic byte-exact tests in `tests/test_synthetic.py` before any real
   file is involved, per the project's existing testing discipline.

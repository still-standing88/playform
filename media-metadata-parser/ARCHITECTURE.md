# Media Metadata Parser — execution plan

Research pass over `plan.md` plus what actually got confirmed against the specs, then
the concrete module layout and build order. Testing against real SFX libraries is the
last phase — everything up to that point is built and self-tested against synthetic
files I generate myself, since I don't have sample data yet.

## Research findings (Phase 0)

**bext chunk (EBU Tech 3285 v2, 2011)** — fixed 602-byte struct, hardcoded by necessity
(it's positional binary, not key-value). Confirmed field layout:

| Offset | Field | Size | Type |
|---|---|---|---|
| 0 | Description | 256 | ASCII, null-padded |
| 256 | Originator | 32 | ASCII |
| 288 | OriginatorReference | 32 | ASCII |
| 320 | OriginationDate | 10 | ASCII `YYYY-MM-DD` |
| 330 | OriginationTime | 8 | ASCII `HH-MM-SS` |
| 338 | TimeReferenceLow | 4 | uint32 LE |
| 342 | TimeReferenceHigh | 4 | uint32 LE |
| 346 | Version | 2 | uint16 (0=none, 1=UMID, 2=+loudness) |
| 348 | UMID | 64 | binary (SMPTE UMID) |
| 412 | LoudnessValue | 2 | int16, LUFS×100 (v2+) |
| 414 | LoudnessRange | 2 | int16, LU×100 (v2+) |
| 416 | MaxTruePeakLevel | 2 | int16, dBTP×100 (v2+) |
| 418 | MaxMomentaryLoudness | 2 | int16, LUFS×100 (v2+) |
| 420 | MaxShortTermLoudness | 2 | int16, LUFS×100 (v2+) |
| 422 | Reserved | 180 | zero-filled |
| 602 | CodingHistory | variable | ASCII, newline-terminated entries, runs to end of chunk |

Version <2 files won't have valid loudness fields — read them only when `Version >= 2`,
never assume they're populated.

**iXML** — confirmed the real-world tag surface is much bigger than plan.md's four
examples. It's not just `PROJECT/SCENE/TAKE/FX_NAME/CATEGORY` — there's a whole ASWG
(Audio Standards Working Group) extension block with dedicated SFX fields
(`CATEGORY`, `SUB_CATEGORY`, `CATID`, `FX_NAME`, `LIBRARY`, `CREATOR_ID`, `SOURCE_ID` —
this is where UCS data often gets embedded directly, separate from the filename), plus
dialogue/music sub-blocks, plus vendor extensions (Steinberg has its own tag block).
This confirms the plan's approach: **walk generically, collect every leaf as a raw key,
don't hardcode a tag whitelist** — a fixed list would silently drop half of what's
actually out there. `lxml` with `recover=True` is the right call; iXML in the wild
includes vendor XML with unescaped entities and unclosed tags.

**UCS (Universal Category System)** — current spreadsheet is v8.2.1 (Jan 2024): 82
top-level categories, 753 subcategories. `CatID` format is `CATEGORY-SubCategory`
(category in caps, subcategory in title case), used both as an iXML field (`CatID`)
and as the first underscore-delimited block of the filename. The full spreadsheet
is distributed from universalcategorysystem.com as a gated Dropbox download, not a
stable fetchable URL — so `data/ucs_categories.json` ships as a **starter table**
covering common categories, not the full 753-row list, with a documented path to
regenerate it from the official CSV once it's on hand.

**RF64/BW64 (EBU Tech 3306 / ITU-R BS.2088)** — RIFF ID becomes `RF64` (or `BW64`),
32-bit size field at offset 4 is set to `0xFFFFFFFF`, and a `ds64` chunk is inserted
immediately before `fmt `. Layout: `riffSizeLow/High` (8 bytes), `dataSizeLow/High`
(8 bytes), `sampleCountLow/High` (8 bytes), `tableLength` (4 bytes), then
`tableLength` entries of `(chunkId: 4 bytes, sizeLow: 4, sizeHigh: 4)` for any other
chunk that also exceeds 32 bits. Any chunk whose 32-bit size reads as `0xFFFFFFFF`
needs its real size looked up in that table instead. Unlikely in an SFX library, but
must not crash the walker if encountered.

## Build order (why this order)

1. **Chunk walkers first** (`metaparser/chunks/`) — every downstream parser depends on
   correct offsets. Handles size-field lies, missing pad bytes, truncation by logging
   and skipping, never raising.
2. **Payload interpreters** (`metaparser/interpreters/`) — bext is a hardcoded struct
   unpack, iXML/LIST/INFO are generic walks, everything else is best-effort and
   isolated so one bad chunk can't kill the whole file's extraction.
3. **UCS filename path** (`metaparser/ucs/`) — independent of chunk parsing, since it
   has to work even when iXML is thin or absent, and doubles as a cross-check against
   an iXML `CATEGORY`/`CatID` tag when both exist.
4. **Raw storage, no unification yet** (`metaparser/models.py`) — `bext_raw`,
   `ixml_raw`, `info_raw`, `ucs_from_filename` kept separate and shaped as they came.
   `normalize.py` (the alias table: `"description" ~ DESCRIPTION ~ Description`) is
   deliberately a stub until there's a real sample corpus to build it from.
5. **Common tag formats** (`metaparser/tags/`) — MP3/FLAC/M4A/video containers via
   `mutagen`, not reinvented. This is the path that also covers plain music/video
   files with no bext/iXML at all.
6. **Indexing/search** (`db/`) — SQLite + FTS5, built against the raw-blob shape from
   step 4 so it doesn't need to change when normalization lands later.
7. **CLI** (`cli.py`) — thin glue over `extractor` + `db`.
8. **Synthetic self-tests** — hand-built WAV/AIFF byte strings with known bext/iXML/
   LIST payloads, so the walkers and interpreters are verified byte-exact before any
   real-world file ever touches them.
9. **Real-world testing (later phase, blocked on the SFX drive)** — run the bundled
   `exiftool-13.59_64/ExifTool.exe -j` over the same files as a diff oracle, per
   plan.md's testing approach. `metaparser/exiftool_bridge.py` shells out to it; it's
   a dev-time cross-check, never a runtime dependency.

## Module layout

```
media-metadata-parser/
├── plan.md                        existing — original brief
├── ARCHITECTURE.md                this file
├── requirements.txt
├── metaparser/
│   ├── __init__.py
│   ├── models.py                  raw-blob dataclasses (Phase 4)
│   ├── extractor.py               format sniff -> route -> assemble
│   ├── normalize.py               alias table (stub, deferred to real-sample phase)
│   ├── exiftool_bridge.py         subprocess wrapper, dev-time oracle only
│   ├── chunks/
│   │   ├── __init__.py
│   │   ├── riff_walker.py         RIFF/WAV, little-endian
│   │   ├── iff_walker.py          IFF/AIFF, big-endian
│   │   └── rf64.py                RF64/BW64 ds64 handling
│   ├── interpreters/
│   │   ├── __init__.py
│   │   ├── bext.py                EBU Tech 3285 struct unpack
│   │   ├── ixml.py                generic lxml tree walk
│   │   ├── list_info.py           RIFF LIST/INFO fourCC table + raw fallback
│   │   └── opportunistic.py       cue/labl/note/axml, best-effort
│   ├── ucs/
│   │   ├── __init__.py
│   │   ├── filename_parser.py     CatID_FXName_CreatorID_SourceID tokenizer
│   │   └── categories.py          category list loader/lookup
│   ├── data/
│   │   └── ucs_categories.json    starter UCS category table
│   └── tags/
│       ├── __init__.py
│       ├── audio_tags.py          mutagen-based MP3/FLAC/etc
│       └── video_tags.py          mutagen-based MP4/MKV/etc
├── db/
│   ├── __init__.py
│   ├── schema.py                  SQLite schema + FTS5 virtual table
│   ├── indexer.py                 directory walk -> extractor -> upsert
│   └── search.py                  FTS5 + structured query interface
├── cli.py                         scan / index / search commands
└── tests/
    └── test_synthetic.py          in-memory WAV/AIFF round-trip checks
```

That's 21 files (well past the 12-file floor) split across five real concerns —
container parsing, payload interpretation, UCS, common tags, and indexing — rather
than one monolith.

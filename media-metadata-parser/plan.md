Fair — let's do this properly. Here's the build plan, structured by what to learn before you write anything, then the architecture.



\## Phase 0: What to actually read (couple hours, not two weeks)



\- \*\*EBU Tech 3285\*\* (bext spec, v2 2011) — official PDF, gives you the exact byte-offset struct. This is the only place with authoritative offsets, don't trust secondhand blog posts on this one.

\- \*\*iXML spec\*\* (ixml.info) — not an ISO/EBU standard, it's an industry-agreed-but-loosely-enforced XML schema. Read it to know the \*intended\* tag names (`BWFXML`, `PROJECT`, `SCENE`, `TAKE`, `FX\_NAME`, `CATEGORY` etc.), but treat it as a guideline, not a contract — vendors deviate.

\- \*\*UCS (Universal Category System)\*\* — universalcategorysystem.com. This is the important one for your thesis angle: it defines both a filename convention (`CatID\_FXName\_CreatorID\_SourceID.wav`) \*and\* a canonical category/subcategory list. This is separate from iXML — some libraries embed CatID inside iXML, others rely purely on filename. You need both extraction paths.

\- Skim \*\*EBU Tech 3285 Supplement 5 (`axml`)\*\* just enough to recognize it and not choke on it — it's an ADM/XML chunk some newer BWF files carry. Low priority to fully parse, high priority to not crash on.



Also worth logging: RF64/BW64 exists (64-bit WAV variant, some field recorders emit it for long files, has a `ds64` chunk before `fmt`) — you probably won't hit it in an SFX library, but note it so a weird file doesn't silently corrupt your scan.



\## Phase 1: Container-level chunk walker (format-agnostic core, build this first)



Two chunk walkers, structurally almost identical:

\- \*\*RIFF/WAV\*\* — little-endian, 4-byte ID + 4-byte size + payload + optional pad byte

\- \*\*IFF/AIFF\*\* — same shape, big-endian



Output at this stage: just `(chunk\_id, offset, raw\_bytes)` tuples. No interpretation. This is where you handle the actually annoying stuff — size field lies, missing pad bytes, truncated files — by logging and skipping rather than raising. Get this bulletproof before touching any payload logic, since every downstream parser depends on walking being correct.



\## Phase 2: Payload interpreters — dynamic, not hardcoded



This is the part answering your "can't guess field names" concern directly:



\- \*\*`bext`\*\*: fixed positional struct (per spec, not guessable) → dict. This one \*is\* hardcoded by necessity, it's a C struct, not key-value.

\- \*\*`iXML`\*\*: parse as XML, but walk the tree generically — collect every leaf tag as a key, whatever it is, rather than looking for a known field list. Use `lxml` with `recover=True` instead of stdlib `ElementTree`, since malformed vendor XML (unclosed tags, bad entities) is going to happen and `lxml`'s recovery mode salvages what it can instead of throwing.

\- \*\*`LIST/INFO`\*\*: walk fourCC sub-chunks generically, map known codes (`INAM`, `IART`, `ICMT`...) through a small lookup \*table\* for friendly names, but keep unrecognized fourCCs as raw keys — nothing gets silently dropped just because it's not in your table.

\- Everything else (`cue`, `labl`, `note`, `axml`) — parse opportunistically, low priority, never let failure to parse one chunk kill the whole file's extraction.



\## Phase 3: UCS filename extraction (separate path, not chunk-based)



Regex/tokenize filenames against the UCS `CatID\_FXName\_CreatorID` pattern, cross-reference CatID against the published category list for a human-readable label. This matters because plenty of files will have thin or missing iXML but \*will\* follow UCS naming — it's your fallback label source, and given your thesis, possibly a cross-validation source (does the filename category agree with the iXML CATEGORY tag, when both exist?).



\## Phase 4: Don't unify too early



Store per-file output as raw blobs first: `bext\_raw`, `ixml\_raw` (as nested dict, whatever shape it came in), `info\_raw`, `ucs\_from\_filename`. Build the alias/normalization table (`"description"` \~ `DESCRIPTION` \~ `Description`) \*after\* you've scanned a real sample and seen what key names actually show up — not before. This is the "go look before you design the schema" point from earlier, now baked into the architecture instead of a suggestion.



\## Libraries, by task



| Task | Tool |

|---|---|

| MP3/FLAC tags | `mutagen` — solved problem, don't reinvent |

| Binary struct unpack (bext, chunk headers) | stdlib `struct` |

| Malformed XML (iXML) | `lxml` (`recover=True`), not stdlib ElementTree |

| Filename parsing | stdlib `re` / `pathlib` |

| Cross-check oracle during dev | `pyexiftool` — diff your output against exiftool's on the same files, not a runtime dep |

| Later: index | `sqlite3` + FTS5 |



\## Testing approach



Don't write the generic parser against the spec blind. Pull \~15-20 files spanning your different vendors now, run them through `exiftool -j`, look at what's actually there, \*then\* write Phase 2's interpreters against real shapes. Keep exiftool's JSON as a running diff-check while you build — if your parser and exiftool disagree on a field, that's your bug to chase, not a shrug.




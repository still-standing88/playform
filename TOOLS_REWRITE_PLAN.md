# Tools Rewrite Plan (`tools-rewrite` branch)

Status: **Phases A–D implemented and verified** (2026-08-07 session), except M4B
Tools which stays a reserved stub per the deferral agreed with the user. See
`git log` on this branch for the full commit-by-commit trail (one commit per
file/edit, per the branch convention). Every new/moved widget was smoke-tested
headless (`QT_QPA_PLATFORM=offscreen`) and the Speech Converter's SAPI5 file-save
+ pitch-XML path was verified against the real Windows SAPI engine on this
machine (see commit history around `tools.speech_converter`).

What shipped:
- Phase A (steps 1–5): `media_core.ffmpeg` vendored, all import sites repointed,
  `python-ffmpeg` dropped from requirements, `PathTreeWidget` built, and
  `format_capabilities.py` built from the real ffmpeg-codecs manuals.
- Phase B (steps 6–8): Batch Converter fully rewritten (Source/Convert/Processing/
  Destination tabs, presets, 32-effect catalog grounded in the real ffmpeg-filters
  manuals, threaded job runner); Media Extractor rewritten with a new Video mode
  and reused Convert-tab panels; Thumbnail Generator moved mechanically.
- Phase C (steps 9–12): Subtitle tools and Tag Editor moved into their own
  modules; Speech Converter built new on `QTextToSpeech` + Windows SAPI5 direct
  COM (file-save, `<pitch middle="N">` XML tags); M4B Tools stubbed + disabled
  menu entry.
- Phase D (step 14): `.claude/CLAUDE.md` updated with a new "Tools" section
  describing the layout above.

Not done / explicitly deferred: M4B Tools' real feature set (§2 of the original
task) — parked until the user supplies the manuals/resources folder, per their
answer in this session.

Working rule for every phase below: **one commit per edit/file**, short/concise
messages, per the repo convention already in `.claude/CLAUDE.md` and reiterated
by the user for this branch. This doc itself lands as commit 1.

## 0. Ground truth found in the repo (why this plan looks the way it does)

- Current tools live as **flat files** in `src/tools/*.py` (`batch_converter_ui.py`,
  `extractor_ui.py`, `tag_editor_ui.py`, `thumbnail_generator_ui.py`,
  `subtitle_converter_ui.py`, `subtitle_editor_ui.py`, `subtitle_handler.py`,
  `ffmpeg_handler.py`, `utils.py`) and are wired into the app in exactly one place:
  [`src/gui/managers/tool_window_manager.py`](src/gui/managers/tool_window_manager.py)
  via `from tools.<file> import <Class>`.
- `python-ffmpeg==2.0.12` (imported today as `from ffmpeg import FFmpeg` /
  `ffmpeg.asyncio.FFmpeg`) is a **pip dependency**, used from
  [`src/tools/ffmpeg_handler.py`](src/tools/ffmpeg_handler.py),
  `src/tools/batch_converter_ui.py`, `src/tools/extractor_ui.py`,
  `src/tools/thumbnail_generator_ui.py`, `src/player/__init__.py`, and
  `src/utilities/chapter_probe.py`.
- The library's actual source is already sitting vendorable at
  `archive/python-ffmpeg/ffmpeg/` (upstream repo, MIT-licensed `ffmpeg-python`-style
  package — `ffmpeg.py`, `options.py`, `file.py`, `progress.py`, `protocol.py`,
  `statistics.py`, `errors.py`, `asyncio/`). This is the exact same shape of move
  already done for radios → `media_core.pyradios` (commits `a8f8c66`…`ca81c38` on
  this branch) — **this task repeats that pattern for ffmpeg.**
- FFmpeg reference manuals (per-encoder options, filters, formats) are at
  `archive/docs/ffmpeg-manuals/` — notably
  `archive/docs/ffmpeg-manuals/ffmpeg-codecs/8-audio-encoders/` has one file per
  audio encoder (`libmp3lame.md`, `libopus.md`, `libvorbis.md`, `aac.md`,
  `flac.md`, `wavpack.md`, `libfdk-aac.md`, `liblc3.md`, `libtwolame.md`,
  `libshine.md`, `libopencore-amrnb.md`, `libvo-amrwbenc.md`) plus
  `ffmpeg-filters/8-audio-filters` for the Processing-tab DSP chain and
  `ffmpeg-formats/` for muxer-level options (e.g. m4a/mp4 metadata, wav bit depth).
  This is the source of truth for the format→option maps in §1.1.
- `tts_demo.py` (repo root, untracked prototype) is a working `QTextToSpeech`
  reference implementation — confirms Speech Converter is built on Qt's
  `PySide6.QtTextToSpeech` (SAPI5 backend on Windows), not the custom `SpeechCore`
  binary, and gives a real component (`QTextToSpeech`, engine picking, voice/locale
  combo, pause/resume/stop state machine) to lift into the new tool.
- No `resources/` folder or M4B manuals exist anywhere in the repo yet — **§3 (M4B
  Tools) is deferred**, per your answer. This plan only reserves its module shape.
- Confirmed with you: §1.1's Source/Convert/Processing/Destination/preset spec is
  the **Batch Converter** rewrite (upgrading `batch_converter_ui.py`); §1.2 is the
  **Media Extractor** rewrite (upgrading `extractor_ui.py`). I've renamed the
  sections below accordingly to avoid the two tools colliding on the same name.

## 1. Target module layout under `src/tools/`

```
src/media_core/ffmpeg/            # vendored python-ffmpeg, ported from archive/python-ffmpeg/ffmpeg
    __init__.py                   # re-exports FFmpeg, so call sites do `from media_core.ffmpeg import FFmpeg`
    ffmpeg.py, options.py, file.py, progress.py, protocol.py, statistics.py, errors.py
    asyncio/...

src/tools/
    ffmpeg/                       # tool group #1
        __init__.py
        batch_converter/          # was batch_converter_ui.py  (§1.1 below)
            __init__.py
            ui.py                 # tab widget shell (Source/Convert/Processing/Destination)
            source_tab.py
            convert_tab.py
            processing_tab.py
            destination_tab.py
            format_capabilities.py   # per-format encoder/option map, sourced from ffmpeg-manuals
            presets.py
            job.py                # builds media_core.ffmpeg FFmpeg command graph, runs the batch
        media_extractor/          # was extractor_ui.py (§1.2 below)
            __init__.py
            ui.py
        thumbnail_generator/      # was thumbnail_generator_ui.py (§1.3, minor tweaks only)
            __init__.py
            ui.py
    m4b_tools/                    # §2, reserved/stub only for now
        __init__.py
    subtitles/                    # §3 — was subtitle_converter_ui.py + subtitle_editor_ui.py + subtitle_handler.py
        __init__.py
        converter_ui.py
        editor_ui.py
        handler.py
    tag_editor/                   # §4.1 — was tag_editor_ui.py
        __init__.py
        ui.py
    speech_converter/             # §4.2 — new tool, modeled on tts_demo.py
        __init__.py
        ui.py
        engine.py                 # QTextToSpeech wrapper: state machine, voice/rate/pitch/volume
        parameters_dialog.py      # volume/pitch/speed dialog + Windows pitch-XML checkbox
    debug_console_dock.py         # stays where it is (not a user-facing "tool")
    logs_viewer_dialog.py         # stays where it is
    utils.py                     # shared helpers, stays at src/tools/ root unless a move is warranted later
```

`tool_window_manager.py` import lines get updated one file at a time (each import
switch is its own commit) as each tool is actually moved — not in one big-bang
sweep, so `git log` on this branch shows the migration file by file.

## 2. Sequencing (each numbered step = its own PR-sized chunk, commits within a step are per-file)

### Phase A — shared groundwork
1. **Vendor python-ffmpeg into `media_core.ffmpeg`.** Copy `archive/python-ffmpeg/ffmpeg/*`
   into `src/media_core/ffmpeg/`, strip anything asyncio-example/test-only, keep
   the package import surface identical (`FFmpeg`, `asyncio.FFmpeg`, `Progress`,
   errors) so call-site changes are pure import rewrites.
2. **Repoint the 6 existing import sites** (`ffmpeg_handler.py`, `batch_converter_ui.py`,
   `extractor_ui.py`, `thumbnail_generator_ui.py`, `player/__init__.py`,
   `utilities/chapter_probe.py`) from `import ffmpeg` / `from ffmpeg import FFmpeg`
   to `from media_core.ffmpeg import FFmpeg`. One file per commit, matching the
   pattern already used for the pyradios repoint (`9d15f01`).
3. **Drop `python-ffmpeg` from `requirements-runtime.txt`** once nothing imports
   the pip package anymore (mirrors `de55ebf` dropping `radios`).
4. **Build a shared `PathTreeWidget`** (new file, e.g. `src/gui_controls/path_tree_widget.py`)
   implementing the file/folder source tree described in §1.1 and reused by §1.1's
   Source tab and §1.1's Processing tab (edits/filters tree). Right-click menu
   (add file/add folder submenu, delete/remove/clear), duplicate-path rejection,
   collapsed-by-default folders with lazy subfolder expansion, per-folder format
   filter storage. Built once, consumed twice — avoids writing two divergent tree
   widgets.
5. **Build `format_capabilities.py`**: a static table mapping each target audio
   format (mp3, ogg, flac, wav, m4a/aac, aiff, opus, wma, wavpack, amr-nb/wb, …)
   to its FFmpeg encoder name(s), and the sample-rate/bit-rate/bit-depth/codec-specific
   option ranges pulled from `archive/docs/ffmpeg-manuals/ffmpeg-codecs/8-audio-encoders/*.md`
   and `ffmpeg-formats/`. This table drives the Convert tab's combo/list widgets
   directly — new formats are added by adding table rows, not new UI code.

### Phase B — `tools/ffmpeg/` group
6. **Batch Converter rewrite** (§1.1) — the big one, broken into its own sub-steps
   so each tab lands as a reviewable/commitable unit:
   - 6a. Module skeleton + tab shell (`ui.py`, empty tabs wired into a `QTabWidget`)
   - 6b. Source tab (consumes `PathTreeWidget` from Phase A step 4, add-file dialog,
     add-folder dialog with subfolder-checkbox + audio/video/all/custom format radio)
   - 6c. Convert tab — audio branch (format combo + sample rate/bit rate/bit depth/codec
     combos driven by `format_capabilities.py`)
   - 6d. Convert tab — video branch (format + video-specific settings, only enabled
     when the audio/video radio is set to video)
   - 6e. Processing tab — Edits branch (Loudness/Volume/Silence/Fade/Trim/Reverse)
   - 6f. Processing tab — Filters branch (EQ, Dynamics, Pitch/Speed, Time-based incl.
     convolution reverb), add/edit/remove effect buttons
   - 6g. Destination tab (in-place vs target-folder radio, preserve-subfolders,
     overwrite/delete-original/log-file checkboxes, log file picker)
   - 6h. Preset combo (save/edit/load — persists Convert+Processing tab state only,
     per spec)
   - 6i. Job runner (`job.py`) wiring the assembled tab state into
     `media_core.ffmpeg` `FFmpeg` command graphs, Begin/Cancel wiring, progress
   - 6j. Swap `tool_window_manager.py`'s `batch_converter_ui` import to the new
     module, delete the old `batch_converter_ui.py`
7. **Media Extractor rewrite** (§1.2) — smaller: keep existing image/audio/video
   mode switch, extend per-mode format options using the same
   `format_capabilities.py` table from Phase A instead of ad-hoc format lists.
8. **Thumbnail Generator move** (§1.3) — mechanical: move file into
   `tools/ffmpeg/thumbnail_generator/`, no behavior change beyond what's already there.

### Phase C — remaining tool groups
9. **Subtitle Tools module** (§3 in the task, "move into its own module") — relocate
   `subtitle_converter_ui.py`, `subtitle_editor_ui.py`, `subtitle_handler.py` into
   `tools/subtitles/`, update the 3 import sites in `tool_window_manager.py`. Pure
   move, no functional change per spec.
10. **Tag Editor move** (§4.1) — relocate `tag_editor_ui.py` into `tools/tag_editor/ui.py`,
    update its one import site. Pure move.
11. **Speech Converter, new tool** (§4.2) — modeled on `tts_demo.py`:
    - 11a. `engine.py`: wrap `QTextToSpeech` with pause/resume/stop state, matching
      `tts_demo.py`'s engine-priority picking
    - 11b. `ui.py`: text editor with context-menu Open/Save-as, pause/resume/stop/save
      toolbar buttons
    - 11c. `parameters_dialog.py`: volume/pitch/speed sliders gated on
      `QTextToSpeech`'s actual engine capabilities; shortcuts F7 (speak/pause), F8
      (stop), Ctrl+S / Ctrl+O, Ctrl+F (open parameters dialog)
    - 11d. Windows-only pitch-via-SSML-tag checkbox: when checked, shows a pitch
      slider mapped from -10..10 to a `<pitch middle="N">...</pitch>` wrap applied
      around the spoken text (guarded by `os.name == 'nt'`, matches the `platform`
      condition in the spec)
    - 11e. Wire into `tool_window_manager.py`
12. **M4B Tools** — stub module only (`tools/m4b_tools/__init__.py` placeholder +
    menu entry that's disabled/"coming soon"), full scope deferred until you drop
    in the manuals as agreed.

### Phase D — cleanup
13. Delete now-unused `src/tools/__pycache__` stale entries implicitly (build artifact,
    not tracked — no action needed, noted for completeness).
14. Update `.claude/CLAUDE.md`'s "Known in-progress / stale things" section to
    describe the new `tools/` layout instead of the flat-file one, once the moves
    land — otherwise the doc goes stale the moment Phase B/C finish.

## 3. Open items / explicit non-goals for this pass

- M4B Tools (§2 of the task) is **out of scope for this plan's implementation
  steps** — revisit once you provide the resources/manuals, per your answer.
- No decision yet on whether `format_capabilities.py`'s table should also drive
  §1.2 Media Extractor's image-format options (PNG/JPEG/etc. aren't FFmpeg audio
  encoders) — will scope a second, smaller table for image output when doing step 7.
- This plan assumes the existing `FFmpegHandler.get_ffmpeg_binary()` binary-resolution
  logic (bin dir → Utility Download Center) is unaffected by the vendoring — only
  the Python wrapper's import path changes, not how the ffmpeg/ffprobe executables
  are located.

## 4. Suggested order to actually execute in

Phase A (steps 1-5) unblocks everything else and is low-risk/mechanical — do it
first. Then Phase B step 6 (Batch Converter) is the largest deliverable and the
one the rest of the spec's detail is about, so it's the main event. Steps 7-11
are comparatively mechanical moves/small new tools and can be done in any order
once Phase A lands. M4B stays parked.

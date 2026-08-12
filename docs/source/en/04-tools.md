[← 3. Customization and Options](03-customization-options.md) | [Table of Contents](documentation.md#table-of-contents) | [5. Legal →](05-legal.md)

---

# 4. Tools

PlayForm includes a suite of built-in tools accessible from the **Tools** menu (see [Section 2.1.1](02-interface-tour.md#211-menubar) for the exact menu layout). Each tool opens in its own dialog window, and only one tool can be open at a time — trying to open a second tool while one is already open shows a "Tool Already Open" message until the first is closed.

Tool dialogs have no native close (X) button; instead they offer **Hide** and **Close**:
- **Hide** leaves the tool running in the background and adds a "Show *Tool Name*" restore button to the menu-bar corner (see [Section 2.1.1](02-interface-tour.md#211-menubar)).
- **Close** (or clicking Hide/Close's window-close equivalent) is blocked with a "Tool Active" warning while a job is still running in that tool — wait for it to finish or cancel it first.

Most tools depend on FFmpeg (minimum version 6 required). If FFmpeg is not found, the tool will not open and a message directs you to **Options > Get/Update Utilities** to download it. Tag Editor, Subtitle Converter, Subtitle Editor, and Speech Converter do not require FFmpeg to open — Speech Converter only calls on it when saving speech to a compressed audio format.

---

## 4.1. FFmpeg Tools

Reached via **Tools > FFmpeg Tools**.

### 4.1.1. Batch Converter

**Access:** Tools > FFmpeg Tools > Batch Converter

**Purpose:** Convert multiple audio or video files between formats in a single batch operation, with an optional chain of audio edits/filters and a saveable preset system.

The dialog has a **Preset** row at the top (an editable name combo plus **Save** and **Delete** buttons) above four tabs — **Source**, **Convert**, **Processing**, **Destination** — and a **Begin** button.

**Source tab:**
- **Add Files...** — multi-select file dialog filtered to PlayForm's known audio/video extensions.
- **Add Folder...** — adds a folder, with **Include all subfolders** and a format-scope choice (**Audio formats** [default], **Video formats**, **All formats**, or a **Custom format**); only files matching the chosen scope are picked up per folder when the job runs.
- **Remove Selected** / **Clear All**, plus the same actions via right-click and the Delete key.

**Convert tab** — a mode switch between **Audio** (default) and **Video**:
- **Audio:** **Format** (MP3, Ogg Vorbis, Opus, AAC, M4A, M4B, FLAC, WAV, AIFF, WMA, AC-3, WavPack, MP2, AMR-NB, ALAC), **Sample Rate** ("Keep Original" or a rate ladder appropriate to the format), **Bit Rate** ("Keep Original" or a kbps ladder — hidden for lossless-only formats), **Use Variable Bit Rate (Quality)** (where the format supports VBR), **Bit Depth** (for FLAC/WAV/AIFF/WavPack/ALAC), and a **Codec Options** panel that rebuilds itself per format (e.g. MP3's encoder quality and joint-stereo toggle, Opus's VBR mode/complexity/application/frame duration, FLAC's compression level, AC-3's dialogue normalization, and so on).
- **Video:** **Format** (MP4/H.264, MKV/H.264, WebM/VP9, AVI/MPEG-4, MOV/H.264), **Resolution** ("Keep Original" or 3840×2160/1920×1080/1280×720/854×480), **Video Bit Rate** ("Keep Original" or 500k–12000k), **Frame Rate** ("Keep Original" or 24/25/30/50/60).

**Processing tab** — builds an ordered effects chain applied during conversion:
- Shows the list of **applied** effects in order, with **Add Edit...**, **Add Filter...**, **Edit Selected...**, and **Remove Selected** (double-click also edits).
- **Add Edit...** / **Add Filter...** open a categorized picker over the built-in effects catalog:
  - **Edits:** Loudness (Normalize Peak, Normalize RMS, EBU R128/loudnorm, ReplayGain), Volume (increase/decrease/multiply), Silence (remove leading/trailing/all silence, trim below threshold), Fade (in/out), Trim (start/end/duration), Reverse.
  - **Filters:** EQ (10-band, 3-band parametric, high/low/band-pass, notch), Dynamics (compressor, limiter, expander, noise gate), Pitch (speed without pitch, pitch without speed), Time-Based (delay, echo, algorithmic reverb, chorus, flanger, phaser, and convolution reverb — the one effect that needs a secondary Impulse Response File plus dry/wet gain).
  - Each effect has its own parameter form (ranges and defaults shown per field) that appears when it's selected.

**Destination tab:**
- **Store all files in their original folders** (default) or **Store all files in this folder:** (with a **Preserve subfolder structure** option for recursively-added folders).
- **Overwrite existing files**, **Delete original files**, and **Create log file** (with a log path picker) options.
- Output files keep the original base filename with the new format's extension. If a resolved output path would be identical to an input file, or an output file already exists and Overwrite is off, that file is skipped and noted in the log/progress rather than being touched.

**Presets:** **Save** stores the current Convert tab settings and Processing effects chain under a name (prompting for one if the combo is empty); selecting a saved preset loads both back; **Delete** removes the currently named preset. Presets do not capture Source or Destination tab state.

**Running a job:** Click **Begin**. A progress dialog shows an overall progress bar plus **Progress** (per-file OK/Skipped/FAILED results) and **Live Log** (raw FFmpeg output) tabs, a **When finished:** notification choice (system tray notification or stay silent), and **Pause**/**Cancel** buttons — Pause holds the job between files, Cancel finishes the current file then stops; both buttons give way to a **Close** button once the run ends.

### 4.1.2. Media Extractor

**Access:** Tools > FFmpeg Tools > Media Extractor

**Purpose:** Extract an audio track, a video track, or image frames from a single source file. Audio and video extraction share the exact same format/quality controls as the Batch Converter's Convert tab.

**How to use:**

1. Browse to or type the path of a source file.
2. Choose a mode: **Audio**, **Video**, or **Images**.
3. **Audio mode** — pick a target format and quality settings (same options as Batch Converter's Audio panel). Optionally set a **Start Time** (`HH:MM:SS`) and an **End Time / Duration** (a value with a colon is treated as an absolute end time; a plain number is treated as a duration in seconds). Output is saved as `{filename}_audio.{extension}`.
4. **Video mode** — pick a target format/resolution/bitrate/frame rate (same options as Batch Converter's Video panel), or check **Copy video stream without re-encoding (fast, no quality loss)** (checked by default) to remux the source's video without recompressing it. Output is saved as `{filename}_video{extension}`.
5. **Images mode** — choose an **Extraction Mode**:
   - **Extract All Frames** — every frame, named `frame-0001.png`, `frame-0002.png`, …
   - **Extract Range** — frames within a Start Time + Duration window.
   - **Extract N Images Per Second** — a configurable frames-per-second rate (1–60, default 1).
   - **Extract Single Frame** — one frame at the Start Time, saved as `frame.{ext}`.
   
   Also choose an **Image Format** (PNG, JPEG, BMP, WebP, TIFF) and, for JPEG/WebP, a **Quality** value (1–100, default 90).
6. Click **Extract** and choose an output directory. Progress is shown with elapsed time and speed; errors are reported in a message box on completion.

### 4.1.3. Thumbnail Generator

**Access:** Tools > Thumbnail Generator

**Purpose:** Generate thumbnail images from a video file using three different methods. All output is PNG.

**How to use:**

1. Browse to or type the path of a video file.
2. Choose a generation mode:

| Mode | Description | Output |
|---|---|---|
| **Manual Frame Selection** | Specify a timestamp (`HH:MM:SS`, default `00:00:15`). Extracts a single frame at that position. | `thumbnail.png` |
| **Automatic Thumbnail Filter** | Uses FFmpeg's `thumbnail` filter to automatically pick the most representative frame. | `thumbnail_auto.png` |
| **Select from Scene Changes** | Detects scene transitions and extracts a frame from each. Configurable number of images (default 5) and scene-change threshold (0.0–1.0, default 0.4). | `scene-01.png`, `scene-02.png`, … |

3. Click **Generate Thumbnail(s)** and choose an output directory.

---

## 4.2. M4B Tools

Reached via **Tools > M4B Tools**. Two tools, grouped by workflow rather than one-per-operation: **Audiobook Tools** for single-book operations, and **Audiobook Combiner** for multi-book, CSV/glob-driven batch operations.

### 4.2.1. Audiobook Tools (Bind / Split / Slide / Labels / Cover)

**Access:** Tools > M4B Tools > Audiobook Tools (Bind/Split/Slide/Labels/Cover)

**Purpose:** Create and manage a single `.m4b` audiobook, one book at a time, across five tabs.

**Bind tab** — combine multiple audio files into one chaptered `.m4b`:
- Source: **From Folder** (one chapter per file, sorted — default) or **From File List** (manually add/remove/reorder files to control chapter order).
- Options: **Use filenames as chapter titles**, **Decode durations (slower, more accurate)**, **Keep temporary files (debugging)**.
- Metadata: **Author**, **Title**, **Date**, **Bitrate** (32k–320k, default 128k), and a **Cover Image**.
- Choose an output `.m4b` path and click **Bind Audiobook**.

**Split tab** — split an existing audiobook into per-chapter/per-segment files:
- Split by **Embedded Chapters** (default) or **Detected Silence** (with a minimum silence duration, silence threshold in dB, and an option to trim silence from segment edges).
- Optional **Start Time**/**End Time** window, a minimum segment length, and end padding.
- Output format uses the same Format/Sample Rate/Bit Rate/VBR/Bit Depth/Codec Options controls as Batch Converter's Convert tab.
- A **Naming Template** field controls output filenames (default `{book_title}/{chapter_num:02d} - {chapter_title}.{ext}`), with placeholders for book title, chapter number/title, author, narrator, genre, year, extension, original filename, and duration. **Include cover art in each segment** is checked by default.
- Choose an output folder and click **Split Audiobook**.

**Slide tab** — shift an existing audiobook's chapter markers in time, **rewriting the file in place** (a confirmation prompt is shown before this happens):
- **Slide Duration** (positive delays chapters, negative pulls them earlier), an optional **Trim Start** amount, and a re-encode bitrate.
- Click **Apply Slide**.

**Labels tab** — exchange chapter markers with an Audacity label-track text file:
- **Export Chapters → Labels** writes the audiobook's current chapters to a label file you can edit in Audacity.
- **Import Labels → Chapters** reads an edited label file back and re-applies it as the book's new chapters, rewriting the audiobook file in place (confirmation prompt shown).

**Cover tab** — extract or apply cover art:
- **Extract Cover Image** saves the audiobook's embedded cover to an image file.
- **Apply Cover Image** embeds a chosen image into a new copy of the audiobook (the output must be a different file from the source).

Bind and Split show progress in a pausable/cancelable job dialog like Batch Converter's; Slide, Labels, and Cover run as single-outcome jobs without a pause option.

### 4.2.2. Audiobook Combiner (Combine / Metadata Dump)

**Access:** Tools > M4B Tools > Audiobook Combiner (Combine/Metadata Dump)

**Purpose:** Multi-book, batch-driven operations across two tabs.

**Combine tab** — merge several audiobooks/audio files into one `.m4b`:
- Source: a **CSV File** (default), a **Glob Pattern** (e.g. `C:\Books\*.m4b`), or a manually ordered **File List**.
- **Combined Audiobook Metadata** fields (Title, Author, Narrator, Genre, Year, Description, Cover — a local path or an `http(s)://` URL) override anything specified in the CSV.
- Options: **Preserve each source file's existing chapters**, a combine **Bitrate** (32k–256k, default 64k), and **Keep temporary files (debugging)**.
- The **CSV format** supports optional `#key,value` metadata header lines (`title`, `author`, `narrator`, `genre`, `year`, `description`, `output_path`, `cover_path`) followed by a data table with a `file` column and an optional per-file `title` column; relative file paths resolve against the CSV's own folder.
- Choose (or let the CSV specify) an output path and click **Combine Audiobooks**.

**Metadata Dump tab** — probe a batch of audio/audiobook files and export one CSV row per chapter:
- Add files/folders the same way as Batch Converter's Source tab.
- Choose an output CSV path and click **Dump Metadata to CSV**.

---

## 4.3. Subtitle Tools

Reached via **Tools > Subtitle Tools**.

### 4.3.1. Subtitle Converter

**Access:** Tools > Subtitle Tools > Subtitle Converter

**Purpose:** Batch convert subtitle files between different formats with encoding control.

**Supported input formats:** ASS, JSON, SAMI, SMI, SRT, SSA, SUB, TTML, TXT, VTT.

**Supported output formats:** SRT, ASS, SSA, MicroDVD, JSON, MPL2, TMP, VTT.

**How to use:**

1. Click **Add Files** to load one or more subtitle files. Each file's encoding is auto-detected; the first file's detected encoding seeds the Input Encoding field.
2. Set the **Output Format** from the dropdown.
3. Optionally adjust **Input Encoding** and **Output Encoding** (default UTF-8; a set of common encodings is offered).
4. Optionally check **Remove miscellaneous events** to strip non-dialogue subtitle events.
5. Expand **Advanced Format Options** for format-specific settings — SRT: keep unknown/all HTML tags on input, keep SSA tags on output; MicroDVD: omit the FPS declaration on output.
6. Click **Convert** and choose an output directory. Each file is written as `{original_basename}.{output_format}`.

### 4.3.2. Subtitle Editor

**Access:** Tools > Subtitle Tools > Subtitle Editor

**Purpose:** Edit a single subtitle file's timing and text with a live preview. Unlike the Converter, the Editor never changes the file's format — output keeps the same filename and extension as the input.

**How to use:**

1. Click **Load File** to open a single subtitle file (same format list as the Converter). Encoding is auto-detected and shown in an editable **Input File Encoding** field.
2. The right-hand panel shows a live preview table with four columns: **No.**, **Start**, **End**, **Text**.
3. Use the **Timing Editor** tab:
   - **Shift Time:** enter an offset such as `1.5s` or `-1m10s` to shift every event by that amount.
   - **Enable Framerate Transformation:** convert timing between a **From FPS** and **To FPS** value (defaults 23.976 → 25.000).
4. Use the **Text Editor** tab — pick a **Text Operation**: **None**, **Find and Replace** (with a Case Sensitive option), **Add Prefix/Suffix**, or **Change Case** (UPPERCASE / lowercase / Title Case). Text-operation changes are reflected live in the preview table.
5. Click **Apply Changes** and choose an output directory — because the output filename matches the input, choose a different folder than the source to avoid overwriting the original file.

---

## 4.4. Tag Editor

**Access:** Tools > Tag Editor

**Purpose:** View and edit metadata tags on audio files.

**Supported file formats:** MP3, FLAC, M4A, AAC, AIFF, DSF, OGG, Opus, WAV, WavPack.

**How to use:**

1. Click **Add Files** to load one or more audio files. Files appear in a list on the left.
2. Select a file to display its current metadata in the right panel.
3. Edit any of the following fields:
   - **Track Title**, **Artist**, **Album**, **Album Artist**, **Composer**
   - **Track Number**, **Total Tracks**, **Disc Number**, **Total Discs**
   - **Genre**, **Year**, **Comment**, **Lyrics**
4. Changes are tracked per-field. Use **Save Current File** to save changes for the selected file, or **Save All Files** to bulk-save all modified files.
5. **Remove File** removes a file from the editing session (does not delete the file from disk).

---

## 4.5. Speech Converter

**Access:** Tools > Speech Converter

**Purpose:** Text-to-speech — type or load text, speak it aloud through the operating system's TTS engine, and optionally render it to an audio file.

**How to use:**

1. Type or paste text into the main text box, or use **Open Text File...** (Ctrl+O) to load a `.txt` file.
2. Click **Speak** (or press F7) to have the text read aloud. **Pause**/**Resume** (F7 while speaking) and **Stop** (F8) are available while speaking, when the active engine supports pausing.
3. Click **Parameters...** (Ctrl+F) to adjust:
   - **Volume** (0–100%, default 100)
   - **Speed** (-100 to 100, default 0)
   - **Pitch** (-100 to 100, default 0)
   - On Windows, an additional **Use pitch parameter through XML tags** option routes speech through SAPI5's own `<pitch>` markup, which gives more reliable pitch control than the normalized Pitch slider (SAPI5 otherwise ignores it).
4. Click **Save...** (Ctrl+S) to render the current text to an audio file (**MP3**, **WAV**, **OGG**, or **FLAC**). This requires the **Windows SAPI5 engine** — on other platforms, or if SAPI5 isn't available, saving to a file is disabled and speaking aloud is the only option. Non-WAV formats are transcoded from a temporary WAV via FFmpeg after SAPI renders it.

The TTS engine itself (SAPI5 on Windows, the platform's native engine on macOS/Linux) is selected automatically — there is no manual engine picker.

---

## 4.6. Multi Device Capture

**Access:** Tools > Multi Device Capture

**Purpose:** Record from several cameras, monitors, windows, and audio devices at the same time, each source saved to its own output file, with pause/resume and live per-source status. Like every other tool, it opens as a single dialog (Hide/Close, one-tool-at-a-time) — it is not a dock panel, so a capture keeps running if you Hide the dialog, but the dialog's own Close is blocked while a capture is active.

### Sessions and Sources

- A **Session** is a named group of sources that share one output folder and container format (MKV, MP4, or MOV).
- A **Source** is one capturable device — a camera, monitor, window, audio input, or audio output — that belongs to one or more sessions. Sources are managed per-session: the Sources list always shows only the sources in the currently selected session.
- Opening the tool with no sessions yet auto-creates and selects an in-memory "Untitled session"; it's only saved for real (as "Session N") once you add its first source, so you never have to create a session before adding a source. Use **New session...** (right-click the Sessions list) to create and name a session explicitly at any time.

### Configuring a session

The **Sessions** list (left) and the session-scoped **Sources** list (right) sit side by side:

- Right-click a session for **Edit**, **Duplicate**, **Delete**, or (for the pending "Untitled" session) **Save session...**.
- Each source row shows its status (e.g. "48000 Hz - 2 ch" for audio, "1920x1080 @ 30fps" for a camera); a checkbox enables or disables it for the next capture without removing it from the session.
- **Add source** opens the source wizard (below). **Refresh status** re-checks whether each source's device is still connected — a source whose device has disappeared is flagged in red.
- **Settings** opens the settings dialog (below); **Start capture** begins recording using every enabled source in the selected session.

### Adding or editing a source

The Add/Edit Source wizard walks through up to three pages:

1. **Type and device** — pick a **Source type** (**Audio input**, **Audio output**, **Camera**, **Monitor**, or **Window**) and a **Device** from a background-probed list (with a **Refresh** button). Likely system-audio-loopback devices (VB-Cable, Stereo Mix, VoiceMeeter, etc.) are labeled "(likely loopback)". Give the source a **Friendly name**.
2. **Settings** — shown only if the type has configurable options:
   - **Audio** (input/output): **Sample rate** (44100/48000/96000/192000 Hz), **Channels** (Mono/Stereo), **Volume** (0–300%, where over 100% applies real gain).
   - **Camera**: **Resolution** and **Frame rate**, populated from the device's actual supported capture formats.
   - **Monitor**/**Window**: **Frame rate** (1–240, default 30) and **Capture mouse cursor**.
3. **Preview** — an opt-in **Enable live preview** checkbox:
   - Camera/Monitor/Window show a live video feed.
   - Audio input plays the microphone back through your speakers so you can actually hear it, plus a level meter.
   - Audio output (loopback) shows a level meter only — it deliberately doesn't play the audio back, to avoid feedback.

### Settings dialog

Opened via the **Settings** button on the Configure view:
- **General**: default output directory, default container format (MKV/MP4/MOV), a **Notify when a capture finishes** toggle (via the system tray), and **Keep intermediate segment files after a paused session** (off by default — see "How pause/resume works" below).
- **Audio defaults** / **Video defaults**: pre-fill values (sample rate/channels/volume for new audio sources; frame rate/cursor-capture for new monitor/window sources) used when you create a new source.

### Recording

Click **Start capture** to switch to the Capture view, which shows a status label (**Idle** / **Starting...** / **Recording** / **Paused** / **Stopping...**), a live per-source status list (waiting → recording, with elapsed time → stopped, or an error message if a device fails mid-capture), and **Pause**/**Cancel** buttons.

- **Pause** (toggles to **Resume**) pauses every source together; the elapsed time shown keeps counting through a pause rather than resetting.
- **Cancel** actually means **Stop and finalize** — despite the label, anything already captured is kept, not discarded.
- When the capture stops, the view automatically switches back to the Configure view.

Three transport hotkeys are active only while the tool's dialog has focus (remappable in **Options > Manage Hotkeys**, under a "Multi Device Capture" section — see [Section 3.1](03-customization-options.md#31-shortcuts)):

| Action | Default Key |
|---|---|
| Start capture | Ctrl+Alt+R |
| Pause/Resume capture | Ctrl+Alt+P |
| Stop capture | Ctrl+Alt+S |

### How pause/resume works, and output files

Each enabled source records through its own capture process. Pausing gracefully finalizes each source's current segment; resuming starts a new segment for the same device. When you stop, a source's segment(s) are losslessly joined into one final file named `{source name}_{date}_{time}.{container}` in the session's output folder. The intermediate segment files created by a pause/resume cycle are deleted after joining, unless **Keep intermediate segment files after a paused session** is enabled in Settings.

### Platform notes

- **Windows**: camera and microphone capture use DirectShow; monitor/window capture uses GDI. There is **no system-audio-output loopback** — capture a virtual audio device instead (VB-Audio Cable, VoiceMeeter, Stereo Mix) added as an **Audio input** source; PlayForm flags such devices as likely loopback automatically.
- **macOS**: camera, screen, and microphone all go through AVFoundation. There is no per-window capture (whole-screen only) and no system-audio loopback — as on Windows, install a virtual audio device (e.g. BlackHole) and add it as an Audio input.
- **Linux**: camera capture uses Video4Linux2, monitor/window capture uses X11 (window capture needs the `wmctrl` utility installed). Audio uses PulseAudio/PipeWire with an ALSA fallback — Linux is the one platform with genuine "Audio output" loopback support out of the box.

---

## 4.7. Other Tools

### Logs Viewer

**Access:** Tools > Debug > View Logs…

The Logs Viewer opens a dialog showing all log files in the `logs/` directory. The left panel lists every log file; selecting one displays its contents in the right panel. Useful for troubleshooting or reviewing application activity.

### Debug Console Dock

**Access:** Tools > Debug > Show Console Dock

The Debug Console is a dockable panel that displays real-time application output, including logging messages and system output. It can be docked anywhere in the main window or floated as a separate window. This tool is intended for developers and advanced troubleshooting.

---

**Previous:** [← 3. Customization and Options](03-customization-options.md) | **Next:** [5. Legal →](05-legal.md)

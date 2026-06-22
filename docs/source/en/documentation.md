# PlayForm Documentation

---

# 1. Software Overview

## 1.1 Introduction

**PlayForm** is a free, modern media player for Windows, designed to be straightforward to use while offering a wide range of features for everyday listening and viewing. Whether you want to play a song from your music folder, catch up on a podcast, watch a video file, or tune into an internet radio station, PlayForm brings it all together in one application.

PlayForm is built around accessibility and ease of use. The interface is organized into dockable panels — Recents & Favorites (always visible), a Player, a File Explorer, Playlists, Podcasts, and Internet Radio — each of which can be shown, hidden, or rearranged to suit the way you work. Everything is keyboard-accessible, and most actions are available through the menu bar, toolbar buttons, or configurable keyboard shortcuts. A Debug Console panel is also available for troubleshooting via **Tools > Debug > Show Console Dock**.

PlayForm is published by **Joybytes**, authored by **Still Standing**, and is licensed under the **GPL-3.0** open-source license. The application's source code and updates are available on [GitHub](https://github.com/still-standing88/playform).

---

## 1.2. Features

PlayForm includes the following capabilities:

**Playback**
- Play local audio and video files from your computer.
- Open individual files, entire folders, or type in a web address (URL) to stream media directly.
- Full playback controls: play, pause, stop, rewind, fast-forward, previous track, and next track.
- Adjustable playback speed: 1×, 1.5×, 2×, 2.5×, and 3×.
- Volume control with mute toggle.
- Seek bar (Segment Timeline) for jumping to any point in the current file.
- Three-state repeat mode: Off, Repeat One (current track), and Repeat All (entire playlist).
- Shuffle playback order with on/off toggle.
- Jump to the beginning (`Home`) or end (`End`) of a track with a single key press.

**Video**
- Dedicated video display area with full-screen support (`F11`, exit with `Esc`).
- Adjustable aspect ratio: 16:9, 4:3, 1:1, 16:10, 5:4, 21:9, 32:9, 2.35:1, 2.39:1.
- Video scale options from 0.25× to 5×.
- Take snapshots (screenshots) from video in JPG, PNG, or TIFF format (`Ctrl+S`).
- Automatic subtitle loading — if a subtitle file with the same name as your video is in the same folder, PlayForm loads it automatically. Language selection is configurable.

**Subtitles**
- Subtitles are displayed in a collapsible list panel below the video, with the current line auto-highlighted during playback.
- Supported external subtitle formats: SRT, VTT, SMI, SAMI, SCC, DFXP, TTML, SUB, ASS.
- Optionally, subtitles can be spoken aloud via text-to-speech (configurable in Preferences).

**Bookmarks & Repeat Loops**
- Add bookmarks at any playback position and jump back to them anytime.
- Up to 10 numbered bookmarks per file are accessible via quick-jump keys (they jump to the 1st through 10th bookmark, sorted by position).
- View and manage all bookmarks via the Bookmarks dialog.
- Set one or more A-B repeat loops (start and end points), causing a section to play on repeat. Multiple non-overlapping loops per file are supported.
- Bookmarks and loop segments are saved per-file and restored between sessions.
- See [Section 3.1](#31-shortcuts) for the full list of bookmark and repeat loop keyboard shortcuts.

**Playlists**
- Create, name, and manage multiple playlists.
- Add files and folders to any playlist.
- Import and export playlists in JSON, M3U, M3U8, PLS, and XSPF formats.
- Playlists are automatically saved and restored each time you open the app.

**File Explorer**
- Built-in file browser panel with tree-view navigation, path bar, and image preview support.
- Filter items by media type and search for files by name (`F3`).
- Double-click or press `Space` to play any file directly from the explorer.
- Includes its own audio preview player (separate from the main player) for quick in-panel listening.

**Recents & Favorites**
- Automatically tracks recently played files so you can quickly return to them.
- Mark any file as a favorite for fast access from the dedicated panel.

**Internet Radio**
- Browse and search thousands of live internet radio stations, powered by the RadioBrowser community directory.
- Filter stations by country, language, or tag (genre).
- Search results are locally cached for faster repeated access.
- Save favorite stations for quick access.

**Podcasts**
- Subscribe to podcast RSS or Atom feeds by adding their URL.
- Browse and search episodes within each feed, sorted chronologically.
- Feeds are refreshed with ETag/conditional GET support for efficiency.
- Play any episode directly from within the app.

**Online Media / YouTube**
- Paste any YouTube URL (or other yt-dlp-supported stream URL) into **File > Open URL** (`Ctrl+U`) to play it without downloading first.
- Direct media URLs (ending in `.mp4`, `.mp3`, `.m3u8`, etc.) are played directly via VLC without involving yt-dlp.
- YouTube playlist URLs are resolved lazily — tracks are fetched in the background as needed.
- Uses `yt-dlp` under the hood, with optional Deno runtime integration and YouTube cookie file support.

**Downloading**
- Built-in Download Center (accessed via **Tools > Download Manager**) handles HTTP downloads with pause, resume, cancel, and automatic retry (up to 3 attempts).
- External utilities (FFmpeg and yt-dlp) can be downloaded and installed from within the app via a dedicated utility download dialog.

**Tools**
- **Batch Converter** — Convert multiple media files to different audio/video formats at once using FFmpeg.
- **Extractor** — Extract audio from video files.
- **Tag Editor** — View and edit metadata (title, artist, album, genre, etc.) on your audio files.
- **Thumbnail Generator** — Generate thumbnail images from video files.
- **Subtitle Converter** — Convert subtitle files between formats (supports SRT, ASS, SSA, MicroDVD, JSON, MPL2, TMP, VTT, and more).
- **Subtitle Editor** — Edit subtitle content and timing with time shifting, framerate transformation, and text operations.
- **Logs Viewer** — Inspect application logs from within the app (**Tools > Debug > View Logs**).

**Interface & Accessibility**
- Fully keyboard-navigable interface with configurable shortcuts across four categories: Global, Main Interface, Explorer, and Player. Shortcuts are suppressed automatically in text input fields, list views, and sliders to avoid conflicts.
- System tray icon for quick access (show/hide toggle and exit).
- Customizable toolbar — add, remove, and reorder toolbar buttons from **Options > Customize Toolbar**.
- Dockable panels that remember their position between sessions. Panels can be toggled and focused via keyboard shortcuts (see [Section 2.1.4](#214-docking-panels) and [Section 3.1](#31-shortcuts)).
- TTS (text-to-speech) for accessibility feedback and subtitle reading via SAPI5 on Windows, configurable in Preferences.
- Color theme support (system, light, and custom themes) managed in Preferences.

---

## 1.3. Supported Media Formats

PlayForm can open a wide range of audio and video file types. The list below covers the most common formats; PlayForm's underlying media engine (VLC) supports many additional formats beyond those shown here.

**Audio Formats**

| Format | File Extension |
|--------|---------------|
| MPEG Audio | `.mp1`, `.mp2`, `.mp3` |
| FLAC (Lossless) | `.flac` |
| WAV | `.wav` |
| Ogg Vorbis | `.ogg` |
| AAC | `.aac` |
| AC-3 / E-AC-3 | `.ac3`, `.eac3` |
| DTS | `.dts` |
| MPEG-4 Audio | `.m4a` |
| Windows Media Audio | `.wma` |
| Opus | `.opus` |
| AIFF | `.aiff`, `.aif` |
| WavPack | `.wv` |
| Monkey's Audio | `.ape` |
| True Audio | `.tta` |
| Matroska Audio | `.mka` |
| Musepack | `.mpc` |
| RealAudio | `.ra` |
| AMR | `.amr` |
| Core Audio Format | `.caf` |
| Module/Tracker | `.s3m`, `.xm`, `.mod`, `.it` |
| Speex | `.spx` |

**Video Formats**

| Format | File Extension |
|--------|---------------|
| MPEG-4 | `.mp4` |
| Matroska | `.mkv` |
| AVI | `.avi`, `.divx` |
| QuickTime | `.mov` |
| Windows Media Video | `.wmv`, `.asf` |
| Flash Video | `.flv`, `.f4v` |
| RealMedia | `.rm`, `.rmvb` |
| WebM | `.webm` |
| MPEG-4 Video | `.m4v` |
| MPEG | `.mpeg`, `.mpg`, `.m2v` |
| MPEG Transport Stream | `.ts`, `.m2ts`, `.mts` |
| 3GPP | `.3gp` |
| Ogg Video | `.ogv` |
| DVD Video Object | `.vob` |
| Digital Video | `.dv` |

> **Tip:** When opening files through **File > Open File**, the file browser automatically filters to show only supported media files. You can switch the filter to "All Files (\*.\*)" if you need to open something not listed above.

---

## 1.4. Online Media Playback

PlayForm can play media that is not stored on your computer. There are three ways to do this:

### Playing a URL

To play an internet stream or an online video:

1. Go to **File > Open URL** (or press `Ctrl+U`).
2. In the dialog that appears, type or paste the web address of the media you want to play.
3. Click **Open** (or press `Enter`).

PlayForm accepts:
- **Direct media URLs** — links that point directly to an audio or video file (e.g., `.mp3`, `.m3u8`, `.mp4` hosted online). These are played directly via VLC without any intermediate processing.
- **YouTube URLs** — paste a YouTube video or playlist link and PlayForm will resolve and play it using yt-dlp. No separate download is required.
- **Other streaming URLs** — most URLs supported by yt-dlp work, including many video-sharing platforms.

> **Note:** Playing YouTube and other online content requires an active internet connection. The first time you use this feature, PlayForm may prompt you to download `yt-dlp` if it is not already present.

### Internet Radio

The **Radio** panel (toggle with `Ctrl+3`) connects to the RadioBrowser public directory, which lists thousands of free, live internet radio stations from around the world. You can search by station name, or filter by country, language, or genre tag. Double-click any station to start listening. Favorites are saved locally. See [Section 2.6.2](./documentation.md) for a full walkthrough.

### Podcasts

The **Podcasts** panel (toggle with `Ctrl+2`) allows you to follow podcast shows by adding their RSS or Atom feed URL. Episodes are listed in chronological order and can be played directly within PlayForm. Feeds are refreshed efficiently using conditional HTTP requests. See [Section 2.6.1](./documentation.md) for a full walkthrough.

---



# 2. A Tour In the Program's User Interface

---

## 2.1. Main UI

When you first launch PlayForm, the main window displays the **Recents & Favorites** panel docked on the left and the **Player** panel docked across the bottom. All other panels — Explorer, Playlists, Radio Browser, and Podcasts — start hidden and can be toggled on when needed via the **View** menu or keyboard shortcuts.

The window is divided into dockable panels (see [Section 2.1.4](#214-docking-panels)), each of which can be repositioned by dragging its title bar. The main window also contains a **menubar** at the top, a **toolbar** below it, and a **status bar** at the bottom.

---

### 2.1.1. Menubar

The menubar contains five menus: **File**, **Media**, **View**, **Tools**, and **Options**. Each is detailed below.

#### File Menu

| Menu Item | Shortcut | Description |
|---|---|---|
| **Open File…** | `Ctrl+O` | Opens a system file dialog filtered to supported media files. |
| **Open Folder…** | `Ctrl+Shift+O` | Opens a folder and loads all playable media files within it. |
| **Open Playlist…** | — | Opens a saved playlist file (`.json`, `.m3u`, `.m3u8`, `.pls`, `.xspf`). |
| **Open URL…** | `Ctrl+U` | Opens a dialog to paste a media URL for streaming. |
| *separator* | | |
| **Close Media** | `Ctrl+W` | Stops and unloads the currently playing media. |
| *separator* | | |
| **Recent Files** ▶ | — | A submenu listing up to 10 recently played files. Hovering over an entry shows its full path as a tooltip. Selecting one plays it immediately. Shows "No recent files" (disabled) when the list is empty. |
| *separator* | | |
| **Minimize to Taskbar** | `Alt+H` | Hides the main window to the system tray. |
| **Exit** | `Alt+X` | Closes the application entirely. |

#### Media Menu

| Menu Item | Shortcut | Description |
|---|---|---|
| **Play/Pause** | `Space` | Toggles between playing and pausing the current track. |
| **Stop** | `Ctrl+Space` | Stops playback completely. |
| *separator* | | |
| **Mute/Unmute** | `M` | Toggles audio mute on or off. |
| *separator* | | |
| **Forward** | `Right` | Seeks forward by the amount configured in Preferences (default 5 seconds). |
| **Backward** | `Left` | Seeks backward by the configured offset amount. |
| *separator* | | |
| **Previous** | `Page Up` | Jumps to the previous track in the playlist. |
| **Next** | `Page Down` | Jumps to the next track in the playlist. |
| *separator* | | |
| **Toggle Repeat** | `Ctrl+R` | Cycles the repeat mode through three states. The menu label updates to show the current state: **Toggle Repeat: Off**, **Toggle Repeat: All**, or **Toggle Repeat: One**. |

#### View Menu

All View menu items are checkable, reflecting whether the corresponding panel is currently visible.

| Menu Item | Shortcut | Default | Description |
|---|---|---|---|
| **Show Recents/Favorites** | `Ctrl+4` | ✓ (on) | Shows or hides the Recents & Favorites dock panel. |
| **Show Explorer** | `Ctrl+E` | (off) | Shows or hides the File Explorer dock panel. |
| **Minimize Player** | `Ctrl+H` | (off) | When checked, the Player panel is hidden. |
| **Show Playlists** | `Ctrl+L` | (off) | Shows or hides the Playlists dock panel. |
| *separator* | | | |
| **Show Radio Browser** | `Ctrl+3` | (off) | Shows or hides the Radio Browser dock panel. |
| **Show Podcasts** | `Ctrl+2` | (off) | Shows or hides the Podcasts dock panel. |

#### Tools Menu

| Menu Item | Description |
|---|---|
| **Batch Converter** | Opens the Batch Converter tool for converting audio/video files. |
| **Media Extractor** | Opens the Extractor tool for extracting audio from video files. |
| **Tag Editor** | Opens the Tag Editor for viewing and editing audio metadata. |
| **Thumbnail Generator** | Opens the Thumbnail Generator tool. |
| *separator* | |
| **Download Manager** | Opens or restores the Download Manager dialog. |
| **Subtitle Tools** ▶ | Submenu with two entries: **Subtitle Converter** and **Subtitle Editor**. |
| **Debug** ▶ | Submenu with two entries: **View Logs…** (opens the log viewer dialog) and **Show Console Dock** (toggles a developer console panel for troubleshooting). |

#### Options Menu

| Menu Item | Shortcut | Description |
|---|---|---|
| **Manage Preferences** | `Ctrl+P` | Opens the Preferences dialog. |
| **Customize Toolbar…** | — | Opens the Toolbar Customization dialog (see below). |
| **Manage Hotkeys** | `F4` | Opens the Hotkeys configuration dialog where all keyboard shortcuts can be remapped. |
| *separator* | | |
| **Check for Updates…** | — | Checks for a newer version of PlayForm. |
| **Get/Update Utilities…** | — | Opens the utility download dialog (for downloading or updating FFmpeg and yt-dlp). |
| **Documentation** | `F1` | Opens this documentation. |
| *separator* | | |
| **About PlayForm…** | — | Opens the About dialog with version and license information. |

---

### 2.1.2. Tool Bar

The toolbar sits directly below the menubar and provides quick, icon-based access to the most common actions. By default, the toolbar contains the following buttons (in order):

| Button | Icon | Action |
|---|---|---|
| **Open File** | (action icon) | Opens the file dialog. |
| **Open Folder** | Explorer icon | Opens the folder dialog. |
| **Open Playlist** | (action icon) | Opens a saved playlist. |
| **Open URL** | (action icon) | Opens the URL dialog. |
| *separator* | | |
| **Play/Pause** | Play/Pause icon | Toggles playback. Icon switches between play and pause. |
| **Stop** | Stop icon | Stops playback. |
| **Mute** | Volume icon | Toggles mute on or off. |
| *separator* | | |
| **Previous** | Previous icon | Previous track. |
| **Next** | Next icon | Next track. |
| *separator* | | |

The toolbar can optionally include buttons for each of the six tools (Batch Converter, Extractor, Tag Editor, Thumbnail Generator, Subtitle Converter, and Subtitle Editor). These are user-configurable via the Toolbar Customization dialog.

#### Toolbar Customization

Right-clicking anywhere on the toolbar shows a context menu with the **Customize Toolbar…** entry. This opens a dialog with two side-by-side lists:

- **Available Tools** (left) — Tools not currently on the toolbar.
- **Toolbar Tools** (right) — Tools currently assigned to the toolbar, in their display order.

Between the two lists, four buttons allow you to:

| Button | Description |
|---|---|
| **Add** | Moves the selected tool(s) from Available to Toolbar. |
| **Remove** | Moves the selected tool(s) from Toolbar back to Available. |
| **Move Up** | Moves the selected toolbar tool one position up. |
| **Move Down** | Moves the selected toolbar tool one position down. |

Both lists support multi-selection (Ctrl+Click or Shift+Click), allowing you to add, remove, or reorder multiple tools at once. The **Reset to Default** button clears all tools from the toolbar. Click **OK** to save your changes, or **Cancel** to discard them. The configuration is persisted between sessions.

---

### 2.1.3. Status Bar

The status bar runs along the bottom of the main window and displays context-sensitive information through three widgets:

| Position | Widget | Purpose |
|---|---|---|
| Left | **Status message** (label) | Displays the current application state, e.g. "Ready", "Playing", "Paused", "Stopped", "Loading: *filename*", "Screenshot saved: *path*", or "No media loaded". |
| Right | **Media info** (label) | Displays media-specific metadata (track title, artist, bitrate, etc.) when available. |
| Right | **Show Tool** (button) | Hidden by default. Appears when a tool window has been minimized; clicking it restores that tool. |
| Right | **Show Downloader** (button) | Hidden by default. Appears when the Download Manager has been minimized; clicking it restores the downloader dialog. |

A resize grip (small triangular handle) is also present at the far-right corner of the status bar.

---

### 2.1.4. Docking Panels

PlayForm uses Qt's dockable panel system to let you arrange the workspace to your liking. Every panel is a `QDockWidget` — you can drag a panel by its title bar to undock it, move it to a different edge of the window, or stack it on top of another panel. Panels can also be resized by dragging their borders.

All docks have the `DockWidgetMovable` feature enabled, meaning they can be repositioned freely. They cannot be closed via the title bar "X" button — panels are toggled on and off exclusively through the **View** menu or their keyboard shortcuts.

#### Panel Reference

| Panel | Default Position | Default Visible | Toggle Shortcut |
|---|---|---|---|
| **Recents & Favorites** | Left | Yes | `Ctrl+4` |
| **Explorer** | Left | No | `Ctrl+E` |
| **Playlists** | Right | No | `Ctrl+L` |
| **Player** | Bottom | Yes | `Ctrl+H` (minimize) |
| **Radio Browser** | Right | No | `Ctrl+3` |
| **Podcasts** | Right | No | `Ctrl+2` |
| **Debug Console** | Bottom | No | (Tools menu) |

> **Note:** The Radio Browser and Podcasts panels are created only when you first toggle them on — they do not consume resources until needed.

#### Player Panel Minimization

The Player panel behaves slightly differently from the others. The **View > Minimize Player** menu item (`Ctrl+H`) collapses the player to show only the Play/Pause button and the minimize toggle. Pressing `Ctrl+H` again or clicking the toggle button restores the full player controls. This is useful when you want to listen to audio without the full player taking up screen space.

Keyboard shortcuts are available for toggling each panel's visibility and for moving keyboard focus directly to a panel. See [Section 3.1](#31-shortcuts) for the complete shortcut reference.

The dock layout (positions and visibility state) is saved automatically and restored the next time you open PlayForm.

---

## 2.2. Player

The Player panel is the heart of PlayForm. It is divided vertically into the following areas, from top to bottom:

1. **Video Display** — The area where video content is rendered. For audio-only files, this area remains black. A loading overlay ("Extracting URL…") appears while online media is being resolved.
2. **Segment Timeline** — A visual timeline bar that shows the current playback progress, loop segments (repeat regions as highlighted blocks), and bookmark markers (as vertical lines). You can click and drag on this bar to add or move loop segments and bookmarks directly.
3. **Player Controls** — The main transport bar with all playback buttons, the seek slider, volume controls, and more.
4. **Subtitles Panel** — A collapsible list that displays subtitle text with the current line highlighted in yellow. It begins hidden and can be toggled via the **Show Subtitles** / **Hide Subtitles** button in its header.
5. **Filters Panel** — Audio and video filter controls (equalizer and adjustment options).

### Player Controls (Transport Bar)

The transport bar is organized into two rows:

**Row 1 — Track Info:** The current track's filename is displayed on the left. Right-clicking it opens a context menu with options to copy the file path, open the file location in Windows Explorer (for local files), or view YouTube video metadata (for YouTube URLs).

**Row 2 — Controls** (left to right):

| Control | Size | Description |
|---|---|---|
| **Previous** | 120×40 | Jumps to the previous track. |
| **Rewind** | 110×40 | Seeks backward by the configured offset. |
| **Play/Pause** | 100×50 | Toggles playback. Icon and label switch between play and pause. |
| **Forward** | 110×40 | Seeks forward by the configured offset. |
| **Next** | 100×40 | Jumps to the next track. |
| **Repeat** | 90×40 | Cycles repeat mode: **Off** → **Repeat: All** → **Repeat: One** → **Off**. |
| **Shuffle** | 110×40 | Toggles shuffle mode: **Shuffle: Off** ↔ **Shuffle: On**. |
| **Bookmarks** | 130×40 | Opens the Bookmarks dialog for the current file. |
| **Screenshot** | 130×40 | Takes a screenshot of the current video frame. |
| *separator* | | Vertical divider line. |
| **Seek icon** | — | A seek icon label. |
| **Seek slider** | (stretch) | Draggable slider showing playback position. Drag to seek to any point. |
| *separator* | | Vertical divider line. |
| **Mute** | 35×35 | Toggles mute (icon shows muted/unmuted state). |
| **Volume icon** | — | A volume icon label. |
| **Volume slider** | 80px wide | Horizontal slider from 0 to 200. |
| **Time display** | min 100px | Shows current position and total length as `MM:SS / MM:SS`. |
| **More (…)** | 35×35 | Opens a popup menu with additional options (see below). |
| **Minimize** | 30×30 | Toggles the minimize-controls mode. |

#### The "More" (…) Menu

Clicking the **…** button opens a popup with the following submenus and actions:

| Submenu / Action | Options |
|---|---|
| **Speed** ▶ | 1.0×, 1.5×, 2.0×, 2.5×, 3.0× (1.0× is default) |
| **Aspect Ratio** ▶ | 16:9, 4:3, 1:1, 16:10, 5:4, 21:9, 32:9, 2.35:1, 2.39:1 |
| **Scale** ▶ | 0.25, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5 |
| **Fullscreen** | Toggle checkable — enters or exits fullscreen mode. |

#### Fullscreen

Press `F11` or use the More menu to enter fullscreen. Press `Esc` to exit. In fullscreen mode, the video fills the entire screen.

#### Screenshots

Click the **Screenshot** button or press `Ctrl+S` to capture the current video frame. Screenshots are saved to the `Screenshots/` folder inside the PlayForm data directory, with filenames like `screenshot-YY-DD-MM-HH-MM-SS-AMPM.png`. The image format (JPG, PNG, or TIFF) is configurable in Preferences (default: PNG).

### Bookmarks & Repeat Loops

The Player supports two powerful navigation features that help you mark and revisit positions in a track.

#### Bookmarks

A bookmark is a saved position within a file. You can add as many bookmarks as you want per file. Add a bookmark at the current position, navigate between bookmarks, delete them, and jump to the 1st through 10th bookmark — all via keyboard shortcuts listed in [Section 3.1](#31-shortcuts). The Bookmarks dialog (also opened via shortcut) lists all bookmarks by timestamp. Right-click a bookmark to delete it individually, or choose to clear all bookmarks for the current file. Bookmarks are also displayed as vertical markers on the Segment Timeline.

#### A-B Repeat Loops

An A-B repeat loop lets you define a section of a track to play on repeat. Multiple non-overlapping loops per file are supported. Set loop start and end points, clear loops, and navigate between loops using keyboard shortcuts listed in [Section 3.1](#31-shortcuts). When both a start and end point are set, playback automatically jumps back to the start when it reaches the end, creating a seamless repeat. Loops appear as highlighted segments on the Segment Timeline, where you can also create, resize, and remove them with the mouse.

Loop segments and bookmarks are saved per-file and restored automatically when you reopen that file in a future session.

### Subtitles

When a video file is loaded, PlayForm automatically searches the same folder for a subtitle file with a matching filename. Supported subtitle formats loaded during playback include: `.srt`, `.vtt`, `.smi`, `.sami`, `.scc`, `.dfxp`, `.ttml`, `.sub`, and `.ass`.

Subtitle text appears in the collapsible **Subtitles** panel below the player controls. The currently active subtitle line is highlighted in yellow. The panel can be shown or hidden with the toggle button in its header.

**Subtitle language** is configurable in Preferences. If text-to-speech is enabled (also in Preferences), PlayForm will read each subtitle aloud using the Windows SAPI5 engine.

The Player has a comprehensive set of keyboard shortcuts covering playback control, seeking, volume, fullscreen, bookmarks, repeat loops, and screenshots. All shortcuts are configurable and can be remapped via **Options > Manage Hotkeys** (`F4`). See [Section 3.1](#31-shortcuts) for the complete Player shortcut reference.

---

## 2.3. Explorer

The Explorer panel is a full-featured file browser integrated into PlayForm. Toggle it with `Ctrl+E` or **View > Show Explorer**.

### Layout

The Explorer panel is split into two main sections:

**Left section — Library:** A list of saved folder paths that serve as quick-access bookmarks to your media directories. Right-click a folder in the file view and choose **Add to library** to save it here.

**Right section — File Browser:**

| Sub-panel | Description |
|---|---|
| **Path bar** | Displays the current directory path. You can type or paste a new path and press `Enter` to navigate there directly. The **Parent Directory** button moves up one folder level. |
| **Files list** | Lists all folders first, then all supported media files. Double-click a folder to enter it; double-click a file to play it in the main player. Press `Space` to play/pause a selected file, and `Backspace` to navigate up one directory. |
| **Image preview** | When a file with an image extension (`.png`, `.jpg`, `.bmp`, etc.) is selected, a scaled preview is shown to the right. Hidden when a non-image file is selected. |
| **Media preview** | A small preview player with a custom Player Bar that can play audio and video files directly within the Explorer panel without affecting the main player. This preview player uses its own independent VLC instance. |

### Navigation

- **Enter a folder:** Double-click it in the file list, or type its path in the path bar and press `Enter`.
- **Go up one level:** Press `Backspace` or click the **Parent Directory** button.
- **Drive root:** On Windows, navigating above a drive root (e.g., `C:\`) shows a list of all available drives.
- **Last path:** The last browsed path is remembered and restored between sessions.

### File Operations and Context Menu

Right-clicking a file or folder opens a context menu:

**For files:**
- **Open** — Plays the file in the main player.
- **Copy Path** — Copies the full file path to the clipboard.
- **Add to playlist** — Adds the file to the currently active playlist.
- **Add to favorites** — Marks the file as a favorite.

**For folders:**
- **Navigate to folder** — Enters the folder.
- **Add to library** — Saves the folder in the Library panel for quick access.
- **Create playlist from folder** — Creates a new playlist containing all media files from that folder.

**Sort options:** Files can be sorted by **Name (A-Z / Z-A)** or by **Date (Newest first / Oldest first)**.

### File Info

When a file is selected, the Explorer displays its type extension, date modified, and size (e.g., "4.2 MB").

### Preview Player Bar

The Player Bar at the bottom of the Explorer is a compact transport control for the in-panel preview player. It is 28 pixels tall with a dark background and a blue progress indicator at the bottom:

- **Click center area:** Play/Pause toggle.
- **Click left of center:** Seek backward.
- **Click right of center:** Seek forward.
- **Click the bottom bar:** Seek to that position (percentage-based).

An **Auto Play** checkbox (on by default) controls whether selecting a file automatically starts preview playback. A **Volume** spinbox (0–100%) controls the preview player's volume independently of the main player.

---

## 2.4. Playlists

The Playlists panel lets you create, manage, and switch between multiple playlists. Toggle it with `Ctrl+L` or **View > Show Playlists**.

### Layout

The panel is split horizontally:
- **Left side — Playlist list:** Shows all your playlists by name. Double-click a playlist name to rename it.
- **Right side — Track view:** Displays the tracks in the currently selected playlist as a table with four columns: **File Name**, **Title**, **Artist**, and **Album**.

### Managing Playlists

| Action | How |
|---|---|
| **Create a new playlist** | Click the **Create Playlist** button, enter a name, and click OK. |
| **Rename a playlist** | Double-click its name in the playlist list. |
| **Import a playlist** | Click the **Import Playlist** button and select a `.json`, `.m3u`, `.m3u8`, `.pls`, or `.xspf` file. |
| **Delete a playlist** | Right-click the playlist name and choose the remove option. |

If a playlist file is missing on disk at startup, you will be prompted to confirm its removal from the list.

### Managing Tracks

Right-click anywhere in the track view to access the context menu:

| Action | Description |
|---|---|
| **Add Tracks** | Opens a multi-file selection dialog. Choose individual audio or video files to append to the playlist. |
| **Delete Selected** | Removes the selected track(s) from the playlist after confirmation. Multi-selection is supported. |
| **Clear Tracks** | Removes all tracks from the playlist after confirmation. |

**Reordering tracks:**
- Drag and drop tracks within the list to change their order.
- Use `Shift+Up` and `Shift+Down` to move the selected track(s) up or down.

**Sorting tracks:** Right-click > **Sort By** offers sorting by File Name, Title, Artist, or Album, each in ascending or descending order.

**Playing a track:** Double-click a track row or press `Enter` on a selected track to start playing the playlist from that position.

### Storage

Playlists are saved as JSON files in the `data/playlists/` directory. An index file (`data/playlists.json`) maps playlist names to their file paths. Playlists are automatically saved when you switch between them and when the application closes.

---

## 2.5. Recents and Favorites

The Recents & Favorites panel is docked on the left by default and provides quick access to your most frequently used media. It contains two tabs:

### Favorites Tab

Lists all files you have explicitly marked as favorites. Items are displayed by filename, and alternating row colors improve readability. Tooltip text is shown on hover: "Double-click or press Enter on a file to open it."

**Adding favorites:** From the Explorer, right-click a file and choose **Add to favorites**.

**Managing favorites:**
- Right-click a favorite and choose **Remove from Favorites** to remove that single item.
- Right-click anywhere and choose **Clear All Favorites** to remove everything (after confirmation).

### Recents Tab

Maintains a list of up to 50 recently played files, with the most recent at the top. This list is updated automatically whenever you play a file.

**Managing recents:**
- Right-click anywhere in the Recents tab and choose **Clear All Recent Files** to empty the list (after confirmation).

The same recent files (up to 10) also appear in the **File > Recent Files** submenu in the menubar.

### Playing from the Panel

Double-click or press `Enter` on any file in either tab to play it immediately in the main player. Both Favorites and Recents are stored in PlayForm's database and persist across application restarts.

---

## 2.6. Media Providers

PlayForm includes two built-in online media sources: Podcasts and Internet Radio.

### 2.6.1. Podcasts

The Podcasts panel lets you subscribe to podcast RSS or Atom feeds and browse their episodes within PlayForm. Toggle it with `Ctrl+2` or **View > Show Podcasts**.

#### Layout

| Section | Description |
|---|---|
| **Search row** | A text input with **Search** and **Clear** buttons. Use this to filter episodes by keyword (searches across title, summary, description, and author fields). |
| **Feeds list** (left) | Lists all subscribed podcast feeds by their title. |
| **Entries tree** (right) | Shows episodes for the selected feed in three columns: **Title**, **Published**, and **Link**. |
| **Summary panel** | Displays the full summary/description of the selected episode in HTML-rendered text. External links are clickable. |

#### Managing Feeds

Right-click in the Feeds list area to access these actions:

| Action | Description |
|---|---|
| **Add Feed** | Prompts for a podcast RSS or Atom URL. The URL is validated before the feed is added. |
| **Refresh Feed** | Reloads the selected feed from its source URL. A progress dialog is shown while fetching. |
| **Update Feed URL** | Changes the URL of the selected feed. Useful if a podcast changes its feed address. |
| **Remove Feed** | Removes the selected feed after confirmation. |
| **Refresh All Feeds** | Refreshes every subscribed feed. Cancelable via the progress dialog. |
| **Clear All Feeds** | Removes all feeds and cached data after confirmation. |

#### Browsing and Playing Episodes

Select a feed to see its episodes in the entries tree. Episodes are sorted chronologically by default. Right-click an episode to:

| Action | Description |
|---|---|
| **Play Entry** | Extracts the media URL from the episode's enclosure or media link and plays it in the main player. |
| **View Full Entry Dump** | Opens a dialog showing all raw metadata fields for the episode. |
| **Open Link in Browser** | Opens the episode's webpage link in your system web browser. |
| **Copy > Title / Page Link / Direct Media Link** | Copies the corresponding value to the clipboard. |
| **Sort By** ▶ | Sort episodes by Title (A–Z / Z–A) or Date (Newest first / Oldest first). |

Keyboard shortcuts for navigating the entries tree (select, page, jump to first/last, play) are listed in [Section 3.1](#31-shortcuts).

#### Feed Caching and Updates

Feeds are cached locally after the first fetch. On subsequent refreshes, PlayForm uses **ETag** and **Last-Modified** HTTP headers to perform conditional requests — if the feed has not changed, the cached data is reused, saving bandwidth and speeding up refresh. HTTP redirects (301, 302, 307, 308) are followed automatically.

---

### 2.6.2. Radio

The Radio Browser panel connects to the [Radio Browser](https://www.radio-browser.info/) community directory, which catalogs thousands of free internet radio stations worldwide. Toggle it with `Ctrl+3` or **View > Show Radio Browser**.

#### Layout

| Section | Description |
|---|---|
| **Search and Filter** (top) | A filter panel for narrowing down station results. |
| **Results** (center) | A 5-column tree view showing matching stations. |
| **Status bar** (bottom) | Shows search progress and result counts ("Found 42 stations", "No results found", etc.). |

#### Search and Filter Panel

| Control | Description |
|---|---|
| **Station Name** | Type a station name and press `Enter` or click **Search**. This performs a full-text name search across the Radio Browser directory. |
| **Filter By** dropdown | Choose a filter dimension: **None**, **Country**, **Language**, **Tag** (genre), or **Codec**. |
| **Value** dropdown | Once a filter dimension is selected, this combo is populated with available values fetched from the Radio Browser API. For **Codec**, you can type any codec name freely. |
| **Sort By** dropdown | Determines the order of results: **Name**, **Votes**, **Country**, **Language**, **Bitrate**, or **Click Count**. Higher-voted and higher-bitrate stations appear first when sorting by Votes, Click Count, or Bitrate (reverse order). |
| **Apply Filters** button | Fetches stations matching all active criteria and the selected sort order. Up to 500 stations are returned per query. Stations reported as broken are hidden automatically. |
| **Show Favorites** | Displays only your locally saved favorite stations. |
| **Clear Cache** | Clears all locally cached radio data (country/language/tag lists). Useful if the Radio Browser directory has changed. |

#### Results Table

The results tree displays stations in five columns:

| Column | Description |
|---|---|
| **Name** | Station name. |
| **Country** | Country where the station is based. |
| **Language(s)** | Comma-separated list of broadcast languages. |
| **Codec** | Audio codec (e.g., MP3, AAC, Ogg). |
| **Bitrate** | Bitrate in kbps. |

**Right-click a station** for these options:

| Action | Description |
|---|---|
| **Play Station** | Resolves the station's stream URL and starts playback in the main player. |
| **Register Click** | Sends a click count to the Radio Browser API, which boosts the station's ranking in the directory. |
| **Add to / Remove from Favorites** | Saves or removes the station from your local favorites list. |
| **Station Information** | Shows a dialog with full details: name, country, languages, tags, codec, bitrate, votes, and homepage. |
| **Copy Stream URL** | Copies the resolved stream URL to the clipboard. |

**Double-clicking** a station row immediately plays it.

All API calls (searches, filtering, favorites, and metadata loading) run on background threads, so the interface remains responsive during network operations. The status bar provides real-time feedback on what is happening (e.g., "Searching for 'jazz'…", "Loading languages…", "Found 128 stations").

---

# 3. Customization and Options

## 3.1. Shortcuts

PlayForm has **72 configurable keyboard shortcuts** organized into four categories: **Global**, **Main Interface**, **Explorer**, and **Player**. All shortcuts can be remapped via the Hotkeys dialog (**Options > Manage Hotkeys**, `F4`).

### How Shortcuts Work

Shortcuts are implemented as Qt application-level event filters. They are assigned one of three scope levels that determine when they fire:

| Scope | Behavior |
|---|---|
| **Global** | Always fires regardless of which widget has focus. |
| **Context-Aware** | Fires only when the focused widget is "safe" — i.e., not a text input, list view, slider, or other widget where the key would conflict with normal typing or navigation. |
| **Widget-Local** | Fires only when a specific widget (e.g., the Player panel) has focus. |

Context-aware scope suppression automatically prevents shortcut conflicts with:

- **Text inputs** (QLineEdit, QTextEdit, QComboBox): Space, Home, End, Left, Right, Backspace, Delete
- **List/tree/table widgets**: Up, Down, Left, Right, Home, End, Page Up, Page Down
- **Sliders and spin boxes**: Up, Down, Left, Right, Home, End, Page Up, Page Down, Plus, Minus
- **Buttons and checkboxes**: Space, Enter

Key combinations are normalized internally to `Ctrl+Alt+Shift+Win+Key` format. Acceptable modifier aliases include `Control` (→ `Ctrl`), and `Meta`/`Cmd`/`Super` (→ `Win`).

### Managing Shortcuts

Open the Hotkeys dialog via **Options > Manage Hotkeys** or press `F4`. The dialog shows a tree view with the four shortcut categories at the top level and individual actions underneath. Each row displays the action name and its current key binding.

| Action | How |
|---|---|
| **Change a shortcut** | Single-click or double-click the Shortcut column for an action, then press the desired key combination. Press Enter or move focus to accept. |
| **Reset to Default** | Click the **Reset to Default** button. All shortcuts revert to their factory defaults after confirmation. |
| **Apply** | Click **Apply** to save changes and activate them immediately without closing the dialog. |
| **OK** | Saves changes and closes the dialog. |
| **Cancel** | Discards any uncommitted edits and closes the dialog. |

Shortcut settings are saved to `data/key_config.cfg`. If this file is corrupted or missing, PlayForm automatically restores the factory defaults.

---

### Default Shortcut Reference

#### Global Shortcuts

These shortcuts work regardless of which panel or widget has focus.

| Action | Default Key |
|---|---|
| Play/Pause | `Ctrl+Win+P` |
| Mute/Unmute | `Ctrl+Win+M` |
| Volume Down | `Ctrl+Win+F7` |
| Volume Up | `Ctrl+Win+F8` |
| Previous | `Ctrl+Win+F9` |
| Next | `Ctrl+Win+F10` |

> **Note:** Global shortcuts currently work only when PlayForm has application focus (they are Qt-level, not OS-level system-wide hotkeys).

#### Main Interface Shortcuts

These shortcuts control the main window, menus, and panel visibility.

| Action | Default Key |
|---|---|
| Open file | `Ctrl+O` |
| Open folder | `Ctrl+Shift+O` |
| Open URL | `Ctrl+U` |
| Close Currently playing Media | `Ctrl+W` |
| Show/Hide explorer | `Ctrl+E` |
| Show/Hide player controls | `Ctrl+H` |
| Show/Hide playlists | `Ctrl+L` |
| Toggle playlists | `Ctrl+1` |
| Toggle podcasts | `Ctrl+2` |
| Toggle radio | `Ctrl+3` |
| Toggle recents/favorites | `Ctrl+4` |
| Focus playlists | `Alt+1` |
| Focus podcasts | `Alt+2` |
| Focus radio | `Alt+3` |
| Focus recents/favorites | `Alt+4` |
| Hide window | `Alt+H` |
| Exit | `Alt+X` |
| Focus explorer | `Alt+E` |
| Focus player | `Alt+P` |
| Documentation | `F1` |
| Hotkeys dialog | `F4` |
| Preferences Dialog | `Ctrl+P` |

#### Explorer Shortcuts

These shortcuts are active when the Explorer panel has focus.

| Action | Default Key |
|---|---|
| Play/Pause | `Space` |
| Backward | `Left` |
| Forward | `Right` |
| Stop | `Ctrl+Space` |
| Search files/folders | `F3` |

#### Player Shortcuts

These shortcuts are active when the Player panel has focus.

| Action | Default Key |
|---|---|
| Play/Pause | `Space` |
| Backward (seek) | `Left` |
| Forward (seek) | `Right` |
| Stop | `Ctrl+Space` |
| Mute/Unmute | `M` |
| Previous track | `Page Up` |
| Next track | `Page Down` |
| Jump to beginning | `Home` |
| Jump to the end | `End` |
| Toggle repeat mode | `Ctrl+R` |
| Volume up | `Up` |
| Volume down | `Down` |
| Fullscreen | `F11` |
| Exit fullscreen | `Esc` |
| Take snapshot | `Ctrl+S` |
| Bookmarks list | `Ctrl+B` |
| New mark at current position | `K` |
| Repeat loop start | `[` |
| Repeat loop end | `]` |
| Clear repeat loop | `Backspace` |
| Previous repeat loop | `Ctrl+[` |
| Next repeat loop | `Ctrl+]` |
| Delete current bookmark | `Delete` |
| Previous bookmark | `Ctrl+Left` |
| Next bookmark | `Ctrl+Right` |
| Mark 1 position | `Ctrl+1` |
| Mark 2 position | `Ctrl+2` |
| Mark 3 position | `Ctrl+3` |
| Mark 4 position | `Ctrl+4` |
| Mark 5 position | `Ctrl+5` |
| Mark 6 position | `Ctrl+6` |
| Mark 7 position | `Ctrl+7` |
| Mark 8 position | `Ctrl+8` |
| Mark 9 position | `Ctrl+9` |
| Mark 10 position | `Ctrl+0` |
| Close media | `Ctrl+W` |

---

## 3.2. Preferences

The Preferences dialog (**Options > Manage Preferences**, `Ctrl+P`) allows you to configure PlayForm's behavior. Settings are organized into four tabs: **General**, **Media**, **Accessibility**, and **Advanced**.

Preferences are stored in `data/prefs.json`. If the file is missing or corrupted, PlayForm automatically restores the factory defaults. Changes to certain settings (language, VLC logging, VLC arguments, or debug level) require an application restart, which PlayForm will prompt you to perform.

### General Tab

| Setting | Options | Default | Description |
|---|---|---|---|
| **Language** | EN, FR, AR, ES | `EN` | User interface language. Requires restart to apply. |
| **Screenshot Format** | JPG, PNG, TIFF | `PNG` | File format for screenshots taken with `Ctrl+S`. |
| **Color Theme** | System, Light, Dark | `System` | UI color scheme. Changes apply immediately without restart. |
| **Auto Check for Updates** | On / Off | `On` | Automatically checks for newer versions of PlayForm at startup. |
| **Save URLs** | On / Off | `Off` | Saves entered URLs across sessions for quick re-access. |

### Media Tab

| Setting | Range | Default | Description |
|---|---|---|---|
| **Volume Offset** | 1–20 | `5` | Amount by which volume changes per step (via shortcuts or menu). |
| **Seek Offset** | 1–60 seconds | `5` | Amount by which forward/backward seeking jumps per step. |
| **Audio Device** | (list) | `0` | Output audio device. Populated with all available devices on your system. |

### Accessibility Tab

| Setting | Options | Default | Description |
|---|---|---|---|
| **Enable Speech Feedback** | On / Off | `Off` | Master toggle for text-to-speech accessibility. When enabled, status bar messages and subtitle text are spoken aloud via SAPI5 on Windows. |
| **Interrupt Previous Speech** | On / Off | `On` | When enabled, a new utterance stops the currently playing one. When disabled, speech is queued. |
| **Voice** | (list) | (system default) | TTS voice selection (available on non-Windows platforms; Windows uses SAPI). |
| **Volume** | 0.0–100.0 | `80.0` | Speech volume. |
| **Rate** | 0.1–10.0 | `1.0` | Speech rate, where 1.0 is normal speed. |

### Advanced Tab

**VLC Settings:**

| Setting | Options | Default | Description |
|---|---|---|---|
| **Enable VLC Logging** | On / Off | `On` | Enables debug logging from the VLC/libmpv media engine. |
| **Debug Level** | 0–2 | `0` | VLC debug verbosity (0 = minimal, 2 = most verbose). Only shown when logging is enabled. |
| **VLC Arguments** | (text) | *(empty)* | Custom command-line arguments passed to the VLC/libmpv backend. Validated on input. |

**yt-dlp Settings:**

| Setting | Description |
|---|---|
| **Cookies File** | Path to a `cookies.txt` file exported from your browser, used for accessing authenticated content on YouTube and other sites. Browse to select the file. |
| **yt-dlp Path** | Directory where yt-dlp binary is located. Normally managed automatically via the utility downloader, but can be set manually. |
| **Enable yt-dlp Logging** | Toggle to enable debug output from yt-dlp. When on, a **Verbose Output** checkbox appears for full detail. |
| **FFmpeg Path** | Directory where FFmpeg binary is located. Normally managed automatically, but can be set manually if you have a custom FFmpeg installation. |

---

# 4. Tools

PlayForm includes a suite of built-in tools accessible from the **Tools** menu. Tools open in a modal dialog window (800×600 default) that can be minimized to the status bar while a task runs. Only one tool can be open at a time — opening a different tool will prompt you to close the current one first.

Most tools depend on FFmpeg. If FFmpeg is not found (minimum version 6 required), the tool will not open and a message will direct you to **Options > Get/Update Utilities** to download it.

---

## 4.1. FFmpeg Tools

### 4.1.1. Batch Converter

**Purpose:** Convert multiple audio or video files between formats in a single batch operation.

**How to use:**

1. Click **Add Files** to select one or more media files.
2. Use **Remove Selected** to remove files from the list.
3. Choose the **Conversion Type**: *Audio* or *Video*.
4. Select the **Target Format**:
   - **Audio:** MP3, AAC, FLAC, WAV, Opus, Vorbis
   - **Video:** MP4 (H.264), MKV (H.264), WebM (VP9), AVI (MPEG-4), MOV (H.264)
5. Configure additional options:
   - **Sample Rate** (audio only): 8000 Hz to 96000 Hz (default: 44100).
   - **Bitrate:** Common presets from 64k to 320k (audio) or 500k to 8000k (video).
6. Click **Start Batch Conversion** and choose an output directory.
7. Progress is displayed per file ("*n* of *total*") with time and speed details. Errors on individual files are reported but do not stop the remaining conversions.

### 4.1.2. Media Extractor

**Purpose:** Extract audio tracks or image frames from video files.

**How to use:**

1. Browse to or type the path of a video file.
2. Choose an extraction mode:

**Audio Extraction:**
- Select an **Output Format** (MP3, AAC, FLAC, WAV, Opus, Vorbis).
- Optionally set a **Start Time** in `HH:MM:SS` format and an **End Time or Duration** (either absolute time or seconds).
- Click **Extract Audio**. The output file is saved as `extracted_audio.{extension}`.

**Image Extraction:**
- Choose an **Extraction Mode**:
  - **Extract All Frames** — outputs every frame (`frame-0001.png`, `frame-0002.png`, …).
  - **Extract Range** — extracts frames within a time range using a start time and duration.
  - **Extract 1 Image Per Second** — uses FFmpeg's `fps=1` filter.
- Optionally set a **Start Time** and **Duration**.
- Click **Extract Images** and choose an output directory.

### 4.1.3. Tag Editor

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

### 4.1.4. Thumbnail Generator

**Purpose:** Generate thumbnail images from video files using three different methods.

**How to use:**

1. Browse to or type the path of a video file.
2. Choose a generation mode:

| Mode | Description | Output |
|---|---|---|
| **Manual Frame Selection** | Specify a timestamp (`HH:MM:SS`, default `00:00:15`). Extracts a single frame at that position. | `thumbnail.png` |
| **Automatic Thumbnail Filter** | Uses FFmpeg's `thumbnail` filter to intelligently select the most representative frame of the video. | `thumbnail_auto.png` |
| **Select from Scene Changes** | Detects scene transitions and extracts frames from each. Configurable number of images (default 5) and scene change threshold (0.0–1.0, default 0.4). | `scene-01.png`, `scene-02.png`, … |

3. Click the corresponding **Generate** button and choose an output directory.

---

## 4.2. Subtitle Tools

### 4.2.1. Subtitle Converter

**Purpose:** Batch convert subtitle files between different formats with encoding control.

**Supported input formats:** ASS, JSON, SAMI, SMI, SRT, SSA, SUB, TTML, TXT, VTT.

**Supported output formats:** SRT, ASS, SSA, MicroDVD, JSON, MPL2, TMP, VTT.

**How to use:**

1. Click **Add Files** to load one or more subtitle files. File encodings are auto-detected.
2. Set the **Output Format** from the dropdown.
3. Optionally adjust **Input Encoding** and **Output Encoding** (default: `UTF-8`).
4. Expand the **Advanced Options** section for format-specific settings:
   - **SRT:** Keep unknown HTML tags (input), keep all HTML tags (input), keep SSA tags (output).
   - **MicroDVD:** Omit FPS declaration (output).
   - **Clean:** Remove miscellaneous events (applies to all formats).
5. Click **Convert** and choose an output directory. Files are processed using the `pysubs2` library.

### 4.2.2. Subtitle Editor

**Purpose:** Edit subtitle content and timing with live preview.

**How to use:**

1. Click **Load File** to open a single subtitle file. Encoding is auto-detected.
2. The right panel shows a live preview table with four columns: **No.**, **Start**, **End**, **Text**.
3. Use the editor tabs on the left:

**Timing Editor:**
- **Shift Time:** Enter an offset value like `1.5s` or `-1m10s` (supports hours, minutes, and seconds suffixes). All events are shifted by this amount.
- **Framerate Transformation:** Convert subtitle timing between frame rates (e.g., 23.976 fps → 25.000 fps).

**Text Editor:**
- **None:** No text modification (preview only).
- **Find and Replace:** Standard search-and-replace with case sensitivity option.
- **Add Prefix/Suffix:** Prepend or append text to every subtitle event.
- **Change Case:** Convert all text to UPPERCASE, lowercase, or Title Case.

All text operations are previewed live as you modify options. Click **Apply Changes** and choose an output directory to save the edited file.

---

## 4.3. Other Tools

### Logs Viewer

**Access:** **Tools > Debug > View Logs**

The Logs Viewer opens a dialog (900×600) showing all log files in the `logs/` directory. The left panel lists every log file; selecting one displays its contents in the right panel. This is useful for troubleshooting or reviewing application activity.

### Debug Console Dock

**Access:** **Tools > Debug > Show Console Dock**

The Debug Console is a dockable panel that displays real-time application output, including redirected `stdout` and `stderr` streams and Python logging messages. It can be docked anywhere in the main window or floated as a separate window. Closing the console restores normal terminal output routing. This tool is intended for developers and advanced troubleshooting.

---

# 5. Download Center

PlayForm includes a built-in Download Manager for downloading files over HTTP, and a separate Utility Download Center for acquiring external binaries (FFmpeg and yt-dlp).

## Download Manager

**Access:** **Tools > Download Manager**

The Download Manager dialog (860×560) handles general-purpose HTTP downloads.

### Adding a Download

Downloads are typically initiated by features within the app (e.g., a tool that requires downloading a resource). The Download Manager shows each download as a list item with:

- **Filename** and current **status** (color-coded: queued, downloading, paused, completed, failed, cancelled).
- **Progress bar** and **size/speed** information.
- The list refreshes every second during active downloads.

Select a download to see detailed information in the right panel: filename, status, progress percentage, speed, and any error message. Toggle **More Info** to reveal the full URL, destination path, retry count, and error details.

### Managing Downloads

| Action | How |
|---|---|
| **Cancel** | Right-click a downloading item and choose **Cancel Download**. |
| **Retry** | Right-click a failed item and choose **Retry Download**. |
| **Copy URL / Destination** | Right-click an item and choose the copy option. |

**Automatic retry:** Failed downloads are automatically retried up to 3 times with a 2-second delay between attempts. Up to 5 HTTP redirects are followed automatically.

**Closing the dialog:** If downloads are in progress, a confirmation dialog warns you and offers to abort all downloads before closing.

The Download Manager dialog can be minimized to the status bar — a **Show Downloader** button will appear there, letting you restore it later.

## Utility Download Center

**Access:** **Options > Get/Update Utilities**

The Utility Download Center is a specialized sub-system for downloading and installing the external binaries that PlayForm depends on:

| Utility | Purpose | Source |
|---|---|---|
| **yt-dlp** | Resolves YouTube and other streaming URLs | GitHub releases (`yt-dlp/yt-dlp`) |
| **Deno** | JavaScript runtime used by yt-dlp integration | GitHub releases (`denoland/deno`) |
| **FFmpeg** | Audio/video encoding, decoding, and conversion (required by most tools) | Platform-specific pre-built binaries |

**How to use:**

1. Open **Options > Get/Update Utilities**.
2. Check the utilities you want to download or update.
3. Click **Download**. The system fetches the latest version information from the respective sources, downloads the files, extracts archives as needed, and installs the binaries to PlayForm's `bin/` directory.
4. Progress for each utility is shown during download and installation. On completion, the temporary files are cleaned up automatically.

FFmpeg installation is platform-aware — it fetches the appropriate build for Windows (GyanD builds), Linux (johnvansickle static builds), or macOS (evermeet builds).

---

# 6. Legal

## 6.1. Software License

**PlayForm** version 1.0.0 is copyright (c) 2024 Still Standing, published by Joybytes, and released under the **GPL-3.0** open-source license.

The full license text is available at: [https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html)

Source code and updates are available on GitHub: [https://github.com/still-standing88/playform](https://github.com/still-standing88/playform)

For support inquiries, contact: support@joybytes.dev

## 6.2. Third-Party Components

PlayForm builds upon and includes the following major third-party libraries and frameworks. Each is used under its respective open-source license.

| Library | Usage Context |
|---|---|
| **PySide6** (Qt 6) | Cross-platform GUI framework
| **VLC ** | Media playback engine providing audio/video decoding, rendering, and streaming for all supported formats. |
| **FFmpeg** | Audio/video transcoding, extraction, thumbnail generation, and format conversion used by the Batch Converter, Extractor, and Thumbnail Generator tools. |
| **Deno** | JavaScript/TypeScript runtime used internally by yt-dlp for resolving streaming URLs. |
| **yt-dlp** | YouTube and streaming platform URL resolver for online media playback. |

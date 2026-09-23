[← 1. Software Overview](documentation.md) | [Table of Contents](documentation.md#table-of-contents) | [3. Customization and Options →](03-customization-options.md)

---

# 2. A Tour of the Program's User Interface

---

## 2.1. Main UI

When you first launch PlayForm, the main window displays the **Recents & Favorites** panel docked on the left and the **Player** panel docked across the bottom. All other panels — Explorer, Playlists, Radio Browser, and Podcasts — start hidden and can be toggled on when needed via the **View** menu or keyboard shortcuts.

The window is divided into dockable panels (see [Section 2.1.4](#214-docking-panels)), each of which can be repositioned by dragging its title bar. The main window also contains a **menubar** at the top, a **toolbar** below it, and a **status bar** at the bottom.

---

### 2.1.1. Menubar

The menubar contains six menus: **File**, **Media**, **View**, **Tools**, **Downloads**, and **Options**. Each is detailed below.

#### File Menu

| Menu Item | Description |
|---|---|
| **Open ▶** | Submenu containing Open File, Open Folder, Open Playlist, and Open URL. |
| *separator* | |
| **Close Media** | Stops and unloads the currently playing media. |
| *separator* | |
| **Recent Files ▶** | A submenu listing up to 10 recently played files. Hovering over an entry shows its full path as a tooltip. Selecting one plays it immediately. Shows "No recent files" (disabled) when the list is empty. |
| *separator* | |
| **Minimize to Taskbar** | Hides the main window to the system tray. |
| **Exit** | Closes the application entirely. |

#### Media Menu

| Menu Item | Description |
|---|---|
| **Play/Pause** | Toggles between playing and pausing the current track. |
| **Stop** | Stops playback completely. |
| *separator* | |
| **Mute/Unmute** | Toggles audio mute on or off. |
| *separator* | |
| **Forward** | Seeks forward by the amount configured in Preferences (default 5 seconds). |
| **Backward** | Seeks backward by the configured offset amount. |
| *separator* | |
| **Previous** | Jumps to the previous track in the playlist. |
| **Next** | Jumps to the next track in the playlist. |
| *separator* | |
| **Toggle Repeat** | Cycles the repeat mode through three states. The menu label updates to show the current state: **Toggle Repeat: Off**, **Toggle Repeat: All**, or **Toggle Repeat: One**. |
| **Bookmarks…** | Opens the Bookmarks dialog for the current file (see [Bookmarks](#bookmarks)). |
| **Go to Time…** | Jumps to a specific playback position; opens a small dialog where you enter a timestamp. |

#### View Menu

| Menu Item | Description |
|---|---|
| **Zoom In** | Scales the entire user interface up. The zoom level is remembered between sessions. |
| **Zoom Out** | Scales the entire user interface down. |
| *separator* | |
| **Minimize Player** | Checkable — hides the Player panel entirely (see [Player Panel Minimization](#player-panel-minimization)). |
| *separator* | |
| **Panels ▶** | Checkable toggles for each panel: **Show Recents/Favorites**, **Show Explorer**, **Show Playlists**, **Show Radio Browser**, and **Show Podcasts**. |
| *separator* | |
| **Window ▶** | Checkable toggles for the **Toolbar**, **Status Bar**, and **Panels Bar**. All three are remembered between sessions. |

#### Tools Menu

| Menu Item | Description |
|---|---|
| **FFmpeg Tools ▶** | Submenu with two entries: **Batch Converter** and **Media Extractor**. |
| **M4B Tools ▶** | Submenu with two entries: **Audiobook Tools (Bind/Split/Slide/Labels/Cover)** and **Audiobook Combiner (Combine/Metadata Dump)**. |
| **Subtitle Tools ▶** | Submenu with two entries: **Subtitle Converter** and **Subtitle Editor**. |
| *separator* | |
| **Tag Editor** | Opens the Tag Editor for viewing and editing audio metadata. |
| **Thumbnail Generator** | Opens the Thumbnail Generator tool. |
| **Speech Converter** | Opens the Speech Converter text-to-speech tool. |
| **Multi Device Capture** | Opens the Multi Device Capture tool for recording several cameras, screens, and audio devices at once. |
| *separator* | |
| **Debug ▶** | Submenu with **View Logs…** (opens the log viewer dialog), **Show Console Dock** (checkable — toggles a developer console panel for troubleshooting), **Restart Application**, and **Restart in Debug Mode…** (restarts PlayForm in debug mode). |

#### Downloads Menu

| Menu Item | Description |
|---|---|
| **Add Download…** | Opens the Add Download dialog: enter a direct http(s) link, a destination folder, and an optional filename. A link whose filename doesn't end in a media extension PlayForm recognizes is routed to the yt-dlp Download Manager automatically. |
| **Download From Link File…** | Imports every link found in a text file into the yt-dlp Download Manager, after a review step. |
| *separator* | |
| **Download Center…** | Opens the Download Manager (see [Section 2.7.1](#271-download-manager)). |
| **yt-dlp Download Manager…** | Opens the yt-dlp Download Manager (see [Section 2.7.2](#272-yt-dlp-download-manager)). |

#### Options Menu

| Menu Item | Description |
|---|---|
| **Manage Preferences** | Opens the Preferences dialog. |
| **Manage Database…** | Opens the Manage Database dialog (see [Section 3.3](03-customization-options.md#33-manage-database)). |
| **Manage Hotkeys** | Opens the Hotkeys configuration dialog where all keyboard shortcuts can be remapped. |
| **Customize Toolbar…** | Opens the Toolbar Customization dialog (see below). |
| **About PlayForm…** | Opens the About dialog with version and license information. |
| *separator* | |
| **Check for Updates…** | Checks for a newer version of PlayForm. |
| **Get/Update Utilities…** | Opens the utility download dialog (for downloading or updating FFmpeg and yt-dlp). |
| *separator* | |
| **Documentation…** | Opens this documentation in your web browser. |

See [Section 4](04-tools.md) for a full walkthrough of every tool.

---

### 2.1.2. Toolbar

The toolbar sits directly below the menubar and provides quick, icon-based access to the most common actions. By default, the toolbar contains buttons for Open File, Open Folder, Open Playlist, Open URL, Play/Pause, Stop, Mute, Previous, and Next.

The toolbar can optionally include buttons for any of the built-in tools. These are user-configurable via the Toolbar Customization dialog.

#### Toolbar Customization

Right-clicking anywhere on the toolbar shows a context menu with the **Customize Toolbar…** entry. This opens a dialog with two side-by-side lists:

- **Available Tools** (left) — Tools not currently on the toolbar.
- **Toolbar Tools** (right) — Tools currently assigned to the toolbar, in their display order.

Between the two lists, four buttons allow you to add, remove, move up, and move down tools. Both lists support multi-selection (Ctrl+Click or Shift+Click). The **Reset to Default** button clears all tools from the toolbar. Click **OK** to save your changes, or **Cancel** to discard them. The configuration is kept between sessions.

> **Note:** The top-right corner of the menu bar shows restore buttons — Show Tool, Show Downloader, Show yt-dlp Downloader, Show Cataloging, Show Manage Database — whenever the corresponding window has been minimized.

---

### 2.1.3. Status Bar

The status bar runs along the bottom of the main window and displays context-sensitive information:

- **Status message (left)** — Displays the current application state, e.g. "Ready", "Playing", "Paused", "Stopped", "Loading: *filename*", or "No media loaded".
- **Media info (right)** — Displays media-specific metadata (track title, artist, bitrate, etc.) when available.

---

### 2.1.4. Docking Panels

PlayForm uses a dockable panel system that lets you arrange the workspace to your liking. You can drag a panel by its title bar to undock it, move it to a different edge of the window, or stack it on top of another panel. Panels can also be resized by dragging their borders.

Panels cannot be closed — they can only be toggled on and off through the **View** menu, the Panels toolbar, or their keyboard shortcuts. Closing a *floated* panel redocks and hides it rather than removing it.

#### Panel Reference

| Panel | Default Position | Toggle Shortcut |
|---|---|---|
| **Recents & Favorites** | Left | Ctrl+4 |
| **Explorer** | Left | Ctrl+E |
| **Playlists** | Left, tabbed with Recents & Favorites | Ctrl+L |
| **Player** | Bottom | Ctrl+H |
| **Radio Browser** | Left, tabbed with Recents & Favorites | Ctrl+3 |
| **Podcasts** | Left, tabbed with Recents & Favorites | Ctrl+2 |
| **Debug Console** | Bottom, tabbed with the Player | Tools > Debug > Show Console Dock |

> **Note:** The Radio Browser and Podcasts panels are created only when you first toggle them on — they do not consume resources until needed.

#### Panels Toolbar

A dedicated toolbar below the main toolbar lists every panel — Player, Recents/Favorites, Explorer, Playlists, Radio, Podcasts, and Console. Each entry has a Show button (labeled **Minimize** for the Player) and a **Float** checkbox. Checking **Float** detaches the panel into its own window; the checkbox is only enabled while the panel is visible.

#### Player Panel Minimization

The Player panel behaves slightly differently from the others. The **View > Minimize Player** menu item (Ctrl+H) hides the entire Player panel, leaving more room for the video. Pressing Ctrl+H again or unchecking the menu item brings the full player back. This is useful when you want to listen to audio without the player taking up screen space.

Keyboard shortcuts are available for toggling each panel's visibility and for moving keyboard focus directly to a panel. See [Section 3.1](03-customization-options.md#31-shortcuts) for the complete shortcut reference.

The dock layout (positions and visibility state) is saved automatically and restored the next time you open PlayForm.

---

## 2.2. Player

The Player panel is the heart of PlayForm. It is divided into these areas, from top to bottom:

1. **Video Display** — The area where video content is rendered. For audio-only files, this area remains black. A loading overlay appears while online media is being resolved.
2. **Segment Timeline** — A bar for managing loop segments and bookmarks. It shows no playback position: click a segment to select it, drag a segment's edge to resize it, or drag a bookmark marker left or right to move it. Clicking an empty spot creates a new loop segment around that point, while Shift- or Ctrl-clicking adds a bookmark instead. See [Bookmarks & Repeat Loops](#bookmarks--repeat-loops).
3. **Player Controls** — The main transport bar with all playback buttons, the seek slider, volume controls, and more.
4. **Side Panel** — A collapsible accordion of seven sections, toggled with the **Show/Hide Side Panel** button. Click a section's header to open it; only one is open at a time.

| Section | Contents |
|---|---|
| **Chapters** | Lists chapters embedded in the current media; click one to jump to it. |
| **Subtitles** | Subtitle track choice, the current subtitle text, and on-video rendering settings (see [Subtitles](#subtitles)). |
| **Equalizer** | Enable toggle, presets, preamp, and per-band gain sliders. |
| **Color Adjustments** | Brightness, Contrast, Gamma, Hue, and Saturation sliders. |
| **Video Effects** | Deinterlace and Deband toggles. |
| **Audio Filters** | Build a chain of mpv audio effects, each with its own parameters. |
| **Audio Sync** | Audio delay plus ReplayGain settings. |

**Audio Filters** works as a list you build up: click **Add Effect…** to append an effect from the available catalog, then double-click any entry in the "Added audio effects" list to edit its parameters. Right-click the list for **Add Effect…**, **Edit Parameters…**, **Delete**, and **Clear All**. The parameter dialog has a **Preset** row: keep **Custom** for your own values, save the current ones under a name with **New…**, or load and delete previously saved presets for that effect.

**Audio Sync** holds timing and loudness fixes: **Audio Delay (seconds)** (from –10 to 10, with a Reset button) shifts the soundtrack against the video, and **ReplayGain** can be switched between **Off**, **Track**, and **Album** with a preamp in dB (–15 to 15) and an **Allow ReplayGain clipping** checkbox.

### Player Controls (Transport Bar)

The transport bar is organized into three rows:

**Row 1 — Track Info:** The current track's filename is displayed on the left. Right-clicking it — or the video display — opens a context menu: **Copy Path** and **Open in Explorer** (local files only); for YouTube sources **Show YouTube Info**, **Download Subtitle…**, and **View Comments…**; and for local files or supported URLs, **View Media Metadata ▶** with **From File (ffprobe)…** for on-disk metadata or **From Playback (MPV)…** for what the player knows about the stream.

**Row 2 — Seek bar:** A full-width slider showing the playback position. Drag it to seek anywhere in the track.

**Row 3 — Buttons:** A wrapping row of icon-only buttons, each with a tooltip. They include: minimize/restore the control area; previous track, backward, play/pause, forward, next track; the repeat-mode and shuffle toggles; show playlist and show queue; bookmarks, go to time, and screenshot; and finally mute/unmute followed by a volume slider (0–300), the time display, and the **⋯** button that opens the More Options menu.

**Show playlist** opens a window listing the current playlist with a "Now playing" header; **Show queue** opens the playback queue, where tracks added through the various **Add to Queue** actions wait their turn — queued tracks play before the playlist order resumes. Double-click any entry to jump to it.

PlayForm remembers where you stopped: reopening a file resumes from its last playback position.

#### The "More" (…) Menu

Clicking the **⋯** button opens a popup with the following submenus and actions:

| Submenu / Action | Options |
|---|---|
| **Speed ▶** | 0.25×, 0.50×, 0.75×, 1.0×, 1.25×, 1.5×, 1.75×, 2.0×, 2.5×, 3.0× (1.0× is default) |
| **Aspect Ratio ▶** | 16:9, 4:3, 1:1, 16:10, 5:4, 21:9, 32:9, 2.35:1, 2.39:1 |
| **Scale ▶** | 0.25, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5 |
| **Rotate ▶** | 0° (Normal), 90°, 180°, 270° |
| **Flip Horizontal** | Checkable — mirrors the video horizontally. |
| **Flip Vertical** | Checkable — mirrors the video vertically. |
| **Video Quality ▶** | Eight per-option submenus for tuning the video pipeline: **Hardware Decoding** (takes effect on the next loaded file), **Upscaler**, **Downscaler**, **Chroma Scaler**, **Interpolation Scaler**, **Frame Dropping**, **HDR Tone Mapping**, and **Video Sync**. Below them sit a **Motion Interpolation** toggle and a **Sharpen** submenu (**Off**, 0.2, 0.4, 0.6, 0.8, 1.0). |
| **Fullscreen** | Toggle checkable — enters or exits fullscreen mode. |
| **Reverse Playback** | Checkable — plays audio in reverse. Only available for audio-only media. |

Aspect Ratio, Scale, Rotate, the two flips, and Video Quality are disabled while the current media has no video track.

#### Fullscreen

Press F11 or use the More menu to enter fullscreen. Press Esc to exit. In fullscreen mode, the video fills the entire screen.

#### Screenshots

Click the **Screenshot** button or press Ctrl+S to capture the current video frame. Screenshots are saved to the `Screenshots/` folder inside the PlayForm data directory. The image format (JPG, PNG, or TIFF) is configurable in Preferences (default: PNG).

### Bookmarks & Repeat Loops

The Player supports two navigation features that help you mark and revisit positions in a track.

#### Bookmarks

A bookmark is a saved position within a file. You can add as many bookmarks as you want per file; up to ten of them can be captured as numbered marks (Ctrl+1 … Ctrl+0) for quick access. Add and navigate between bookmarks, delete them, and jump between them using the keyboard shortcuts listed in [Section 3.1](03-customization-options.md#31-shortcuts). The Bookmarks dialog (Ctrl+B) lists all bookmarks by timestamp. Right-click a bookmark to delete it individually, or choose to clear all bookmarks for the current file. Bookmarks are also displayed as markers on the [Segment Timeline](#22-player).

#### A-B Repeat Loops

An A-B repeat loop lets you define a section of a track to play on repeat. Multiple non-overlapping loops per file are supported. Set loop start and end points, clear loops, and navigate between loops using keyboard shortcuts listed in [Section 3.1](03-customization-options.md#31-shortcuts). When both a start and end point are set, playback automatically jumps back to the start when it reaches the end. Loops appear as highlighted segments on the Segment Timeline, where you can also create, resize, and remove them with the mouse.

Loop segments and bookmarks are saved per-file and restored automatically when you reopen that file in a future session.

### Subtitles

When media is loaded, PlayForm looks for a subtitle file next to it with the same base name (for example `movie.srt` for `movie.mkv`). These formats are tried in order: .idx, .sub, .srt, .rt, .ssa, .ass, .mks, .vtt, .sup, .scc, .smi, .lrc, and .pgs.

The **Subtitles** section of the side panel contains:

- **Track list** — choose **Off**, an embedded subtitle track (listed as "Track N", with a language tag and a "[forced]" marker when applicable), or a yt-dlp-provided language for online media.
- **Subtitle text** — the running subtitle text, with the active line highlighted as it plays. The list stays available whether or not subtitles are drawn on the video; the **Previous Line** and **Next Line** buttons jump to the previous or next subtitle line.
- **Subtitle Delay (seconds)** — shifts subtitle timing earlier or later (–60 to 60).
- **Show subtitles on video** — whether subtitles are rendered over the video.

Font, colors, outline, and positioning of on-video subtitles are configured in the Subtitles tab of Preferences (see [Section 3.2](03-customization-options.md#32-preferences)).

The Player has a comprehensive set of keyboard shortcuts covering playback control, seeking, volume, fullscreen, bookmarks, repeat loops, and screenshots. All shortcuts are configurable and can be remapped via **Options > Manage Hotkeys** (F4). See [Section 3.1](03-customization-options.md#31-shortcuts) for the complete Player shortcut reference.

---

## 2.3. Explorer

The Explorer panel is a full-featured file browser integrated into PlayForm. Toggle it with Ctrl+E or **View > Panels > Show Explorer**.

### Layout

The Explorer panel is split into two main sections:

**Left section — Library:** A list of saved folder paths that serve as quick-access bookmarks to your media directories. Right-click a folder in the file view and choose **Add to library** to save it here.

**Right section — File Browser:**

| Sub-panel | Description |
|---|---|
| **Path bar** | Displays the current directory path. You can type or paste a new path and press Enter to navigate there directly. The **Parent Directory** button moves up one folder level. |
| **Search box** | Searches the current folder (and its subfolders) for matching files; if the folder has been cataloged, the database is used for the search (see [Section 3.3](03-customization-options.md#33-manage-database)). |
| **Files list** | Lists all folders first, then all supported media files. Double-click a folder to enter it; double-click a media file to play it in the main player, or an image to open it in an image preview dialog (titled "Image Preview"). Press Space to play/pause a selected file, and Backspace to navigate up one directory. |
| **Image preview** | When a file with an image extension (.png, .jpg, .bmp, etc.) is selected, a scaled preview is shown to the right. Hidden when a non-image file is selected. |
| **Media preview** | A small preview player that can play audio and video files directly within the Explorer panel without affecting the main player. |

The panel's toolbar offers **List View** and **Icon View** buttons, a **Refresh** action (F5), and **Add Current Folder to Database**, which queues the currently open folder for cataloging so its files become searchable (see [Section 3.3](03-customization-options.md#33-manage-database)).

### Navigation

- **Enter a folder:** Double-click it in the file list, or type its path in the path bar and press Enter.
- **Go up one level:** Press Backspace or click the **Parent Directory** button.
- **Drive root:** On Windows, navigating above a drive root (e.g., `C:\`) shows a list of all available drives.
- **Last path:** The last browsed path is remembered and restored between sessions.

### File Operations and Context Menu

Right-clicking a file or folder opens a context menu:

**For files:** **Open**, **Copy Path**, **Add to playlist**, **Add to Queue** (media files only), **Open in Explorer**, and **Add to favorites**.

**For folders:** **Navigate to folder**, **Add to library**, **Create playlist from folder**, and **Add to Database** — which is shown disabled as "Already in Database" if the folder is already cataloged.

Both menus continue with **View ▶** (**Detail View** / **Icon View**), **Sort by ▶** (**Name (A–Z)**, **Name (Z–A)**, **Newest first**, **Oldest first**), **Filter ▶** (**All Files**, **Audio**, **Video**, **Images**, or **Custom Format…** — which prompts for an extension to show only files of that format), and **Refresh**. Search results use the same menu, except that Sort by is not offered there.

### File Info

When a file is selected, the Explorer displays its type extension, date modified, and size.

### Preview Player Bar

The Player Bar at the bottom of the Explorer is a compact transport control for the in-panel preview player:

- **Click center area:** Play/Pause toggle.
- **Click left of center:** Seek backward.
- **Click right of center:** Seek forward.
- **Click the bottom bar:** Seek to that position (percentage-based).

An **Auto Play** checkbox (on by default) controls whether selecting a file automatically starts preview playback, a **Loop** checkbox repeats it, and a **Volume** spinbox (0–300%) controls the preview player's volume independently of the main player.

---

## 2.4. Playlists

The Playlists panel lets you create, manage, and switch between multiple playlists. Toggle it with Ctrl+L or **View > Panels > Show Playlists**.

### Layout

The panel is split horizontally:

- **Left side — Playlist list:** Shows all your playlists by name. Double-click a playlist name to rename it.
- **Right side — Track view:** Displays the tracks in the currently selected playlist as a table with five columns: **#**, **File Name**, **Title**, **Artist**, and **Album**.

### Managing Playlists

Right-click a playlist in the left list for **Rename**, **Delete**, **Split Playlist…** (splits its tracks into two playlists via a dialog), and **Merge Playlists…** (combines it with another playlist of your choosing).

To create a playlist, click the **Create Playlist** button, enter a name, and click OK. To import one, click **Import Playlist** and select a .json, .m3u, .m3u8, .pls, or .xspf file. If a playlist file is missing on disk at startup, you will be prompted to confirm its removal from the list.

### Managing Tracks

Right-click anywhere in the track view to access the context menu:

| Action | Description |
|---|---|
| **Add Tracks** | Opens a multi-file selection dialog for audio files to append to the playlist. |
| **Move Up** / **Move Down** | Moves the selected track(s) one row up or down. |
| **Sort ▶** | Sorts the playlist by File Name, Title, Artist, or Album, ascending or descending. |
| **Delete Selected** | Removes the selected track(s) from the playlist after confirmation. Multi-selection is supported. |
| **Clear Tracks** | Removes all tracks from the playlist after confirmation. |

**Reordering tracks:** Drag and drop tracks within the list, press Shift+Up / Shift+Down, or use Move Up/Move Down from the context menu.

**Playing a track:** Double-click a track row or press Enter on a selected track to start playing the playlist from that position.

### Storage

Playlists are saved in the `data/playlists/` directory, one file per playlist; the registry that maps playlist names to their file paths is kept in the application database. Playlists are automatically saved when you switch between them and when the application closes.

---

## 2.5. Recents and Favorites

The Recents & Favorites panel is docked on the left by default and provides quick access to your most frequently used media. It contains two tabs:

### Favorites Tab

Lists all files you have explicitly marked as favorites. Items are displayed by filename, and alternating row colors improve readability.

**Adding favorites:** From the Explorer, right-click a file and choose **Add to favorites**.

**Managing favorites:**
- **Remove from Favorites** removes the single item you right-clicked.
- **Add to Queue** sends the file to the playback queue (see [Player Controls](#player-controls-transport-bar)).
- **Clear Nonexistent Tracks** removes entries whose files can no longer be found.
- **Clear All Favorites** removes everything (after confirmation).

### Recents Tab

Maintains a list of up to 50 recently played files, with the most recent at the top. This list is updated automatically whenever you play a file.

**Managing recents:**
- **Remove This Track** removes the single entry you right-clicked.
- **Add to Queue** sends the file to the playback queue.
- **Clear Nonexistent Tracks** removes entries whose files can no longer be found.
- **Clear All Recent Files** empties the list (after confirmation).

The same recent files (up to 10) also appear in the **File > Recent Files** submenu in the menubar.

### Playing from the Panel

Double-click or press Enter on any file in either tab to play it immediately in the main player. Both Favorites and Recents are stored in PlayForm's database and persist across application restarts.

---

## 2.6. Media Providers

PlayForm includes two built-in online media sources: Podcasts and Internet Radio.

### 2.6.1. Podcasts

The Podcasts panel lets you subscribe to podcast RSS or Atom feeds and browse their episodes within PlayForm. Toggle it with Ctrl+2 or **View > Panels > Show Podcasts**.

#### Layout

| Section | Description |
|---|---|
| **Search row** | A text input with **Search** and **Clear** buttons. Use this to filter episodes by keyword (searches across title, summary, description, and author fields). |
| **Feeds list** (left) | Lists all subscribed podcast feeds by their title. |
| **Entries tree** (right) | Shows episodes for the selected feed in three columns: **Title**, **Published**, and **Link**. |
| **Summary panel** | Displays the full summary/description of the selected episode. External links are clickable. |

#### Managing Feeds

Right-click in the Feeds list area to access these actions:

| Action | Description |
|---|---|
| **Add Feed** | Prompts for a podcast RSS or Atom URL. The URL is validated before the feed is added. |
| **Refresh Feed** | Reloads the selected feed from its source URL. A progress dialog is shown while fetching. |
| **Update Feed URL** | Changes the URL of the selected feed. Useful if a podcast changes its feed address. |
| **Remove Feed** | Removes the selected feed after confirmation. |
| **Download All Episodes** | Queues every episode of the selected feed for download in the Download Manager (see [Section 2.7](#27-downloads)). |
| **Refresh All Feeds** | Refreshes every subscribed feed. Cancelable via the progress dialog. |
| **Clear All Feeds** | Removes all feeds and cached data after confirmation. |

#### Browsing and Playing Episodes

Select a feed to see its episodes in the entries tree, listed with the newest first by default. Right-click an episode to:

| Action | Description |
|---|---|
| **Sort By ▶** | Sort episodes by Title (A–Z / Z–A) or Date (Newest first / Oldest first). |
| **Copy ▶** | Copies the **Title**, **Page Link**, or **Direct Media Link** to the clipboard. |
| **Play Entry** | Extracts the media URL from the episode's enclosure or media link and plays it in the main player. |
| **Download Episode** | Sends the episode to the Download Manager for download. |
| **View Full Entry Dump** | Opens a dialog showing all raw metadata fields for the episode. |
| **Open Link in Browser** | Opens the episode's webpage link in your system web browser. |

Downloaded episodes are saved to the Podcasts Folder (each feed gets its own subfolder) — see the [Downloads preferences](03-customization-options.md#downloads-tab).

Keyboard shortcuts for navigating the entries tree (select, page, jump to first/last, play) are listed in [Section 3.1](03-customization-options.md#31-shortcuts).

---

### 2.6.2. Radio

The Radio Browser panel connects to the [Radio Browser](https://www.radio-browser.info/) community directory, which catalogs thousands of free internet radio stations worldwide. Toggle it with Ctrl+3 or **View > Panels > Show Radio Browser**.

#### Layout

| Section | Description |
|---|---|
| **Search and Filter** (top) | A filter panel for narrowing down station results. |
| **Results** (center) | A 5-column tree view showing matching stations. |
| **Status bar** (bottom) | Shows search progress and result counts. |

#### Search and Filter Panel

| Control | Description |
|---|---|
| **Station Name** | Type a station name and press Enter or click **Search**. This performs a full-text name search across the Radio Browser directory. |
| **Filter By** dropdown | Choose a filter dimension: **None**, **Country**, **Language**, **Tag** (genre), or **Codec**. |
| **Value** dropdown | Once a filter dimension is selected, this combo is populated with available values fetched from the Radio Browser API. |
| **Sort By** dropdown | Determines the order of results: **Name**, **Votes**, **Country**, **Language**, **Bitrate**, or **Click Count**. Higher-voted and higher-bitrate stations appear first when sorting by Votes, Click Count, or Bitrate. |
| **Apply Filters** button | Fetches stations matching all active criteria and the selected sort order. Up to 500 stations are returned per query. Stations reported as broken are hidden automatically. |
| **Show Favorites** | Displays only your locally saved favorite stations. |
| **Clear Cache** | Clears all locally cached radio data. Useful if the Radio Browser directory has changed. |

#### Results Table

The results tree displays stations in five columns: **Name**, **Country**, **Language(s)**, **Codec**, and **Bitrate**.

**Right-click a station** for these options:

| Action | Description |
|---|---|
| **Play Station** | Resolves the station's stream URL and starts playback in the main player. |
| **Register Click** | Sends a click count to the Radio Browser API, which boosts the station's ranking in the directory. |
| **Add to / Remove from Favorites** | Saves or removes the station from your local favorites list. |
| **Station Information** | Shows a dialog with full details: name, country, languages, tags, codec, bitrate, votes, and homepage. |
| **Copy Stream URL** | Copies the resolved stream URL to the clipboard. |

**Double-clicking** a station row immediately plays it.

---

## 2.7. Downloads

PlayForm manages its downloads through two windows, both reachable from the **Downloads** menu.

### 2.7.1. Download Manager

The Download Manager (**Downloads > Download Center…**) handles file downloads: podcast episodes, direct links added via **Downloads > Add Download…**, and anything else sent to it. It has no window close button — instead it offers **Minimize** (tucks the window away and leaves a **Show Downloader** restore button in the menu-bar corner) and **Close**. Closing while downloads are still in progress shows a "Downloads in Progress" warning, where you can abort the downloads or cancel the close.

A category list on the left filters the table: **All**, **Queued**, **Downloading**, **Paused**, **Completed**, **Failed**, and **Podcast Queue**. The table shows each download's **Filename**, **Size**, and **Status**, and a **Download Info** area below offers ("Show more info") additional detail about the selected download.

Right-click a download for **Play**, **Add to Player Queue**, **Open File Location**, **Properties…**, **Remove**, **Copy URL**, and **Copy Destination**, plus the state-dependent **Pause Download**, **Cancel Download**, **Resume Download**, and **Retry Download** actions.

### 2.7.2. yt-dlp Download Manager

The yt-dlp Download Manager (**Downloads > yt-dlp Download Manager…**) queues downloads from YouTube and other yt-dlp-supported sites. It can also be reached automatically: a link added through **Add Download…** whose filename lacks a recognized media extension is routed here.

The left pane groups downloads by category — **YouTube Videos**, **YouTube Playlists**, **YouTube Channels**, and **Other Videos** — with per-category counts; playlists and channels expand to show their individual videos. Each entry shows its title and status, including download percentage, speed, and time remaining; double-click a completed video to play it. A **Pause** button and a status line sit at the bottom, above a log pane.

There are two ways to add work:

- **Add Download…** — enter a URL. If the link could be either a single video or a playlist, the manager asks which one you meant. Channel links additionally ask whether you want **Videos**, **Shorts**, or **Both**.
- **Add From Link File…** — pick a text file of links.

Playlists, channels, and link files first open a review dialog where you can select exactly which videos to download.

Closing the window while downloads are running offers to keep them going minimized — the queue is preserved.

---

**Previous:** [1. Software Overview](documentation.md) | **Next:** [3. Customization and Options →](03-customization-options.md)

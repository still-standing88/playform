[← 1. Software Overview](documentation.md) | [Table of Contents](documentation.md#table-of-contents) | [3. Customization and Options →](03-customization-options.md)

---

# 2. A Tour of the Program's User Interface

---

## 2.1. Main UI

When you first launch PlayForm, the main window displays the **Recents & Favorites** panel docked on the left and the **Player** panel docked across the bottom. All other panels — Explorer, Playlists, Radio Browser, and Podcasts — start hidden and can be toggled on when needed via the **View** menu or keyboard shortcuts.

The window is divided into dockable panels (see [Section 2.1.4](#214-docking-panels)), each of which can be repositioned by dragging its title bar. The main window also contains a **menubar** at the top, a **toolbar** below it, and a **status bar** at the bottom.

---

### 2.1.1. Menubar

The menubar contains five menus: **File**, **Media**, **View**, **Tools**, and **Options**. Each is detailed below.

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

#### View Menu

All View menu items are checkable, reflecting whether the corresponding panel is currently visible.

| Menu Item | Description |
|---|---|
| **Show Recents/Favorites** | Shows or hides the Recents & Favorites dock panel. |
| **Show Explorer** | Shows or hides the File Explorer dock panel. |
| **Minimize Player** | When checked, the Player panel is hidden. |
| **Show Playlists** | Shows or hides the Playlists dock panel. |
| *separator* | |
| **Show Radio Browser** | Shows or hides the Radio Browser dock panel. |
| **Show Podcasts** | Shows or hides the Podcasts dock panel. |

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
| **Download Manager** | Opens or restores the Download Manager dialog. |
| **Debug ▶** | Submenu with two entries: **View Logs…** (opens the log viewer dialog) and **Show Console Dock** (toggles a developer console panel for troubleshooting). |

See [Section 4](04-tools.md) for a full walkthrough of every tool.

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

---

### 2.1.2. Toolbar

The toolbar sits directly below the menubar and provides quick, icon-based access to the most common actions. By default, the toolbar contains buttons for Open File, Open Folder, Open Playlist, Open URL, Play/Pause, Stop, Mute, Previous, and Next.

The toolbar can optionally include buttons for any of the built-in tools. These are user-configurable via the Toolbar Customization dialog.

#### Toolbar Customization

Right-clicking anywhere on the toolbar shows a context menu with the **Customize Toolbar…** entry. This opens a dialog with two side-by-side lists:

- **Available Tools** (left) — Tools not currently on the toolbar.
- **Toolbar Tools** (right) — Tools currently assigned to the toolbar, in their display order.

Between the two lists, four buttons allow you to add, remove, move up, and move down tools. Both lists support multi-selection (Ctrl+Click or Shift+Click). The **Reset to Default** button clears all tools from the toolbar. Click **OK** to save your changes, or **Cancel** to discard them. The configuration is kept between sessions.

> **Note:** The top-right corner of the menu bar shows restore buttons — Show Tool, Show Downloader, Show Cataloging, Show Manage Database — whenever the corresponding window has been minimized.

---

### 2.1.3. Status Bar

The status bar runs along the bottom of the main window and displays context-sensitive information:

- **Status message (left)** — Displays the current application state, e.g. "Ready", "Playing", "Paused", "Stopped", "Loading: *filename*", or "No media loaded".
- **Media info (right)** — Displays media-specific metadata (track title, artist, bitrate, etc.) when available.

---

### 2.1.4. Docking Panels

PlayForm uses a dockable panel system that lets you arrange the workspace to your liking. You can drag a panel by its title bar to undock it, move it to a different edge of the window, or stack it on top of another panel. Panels can also be resized by dragging their borders.

Panels cannot be closed — they can only be toggled on and off through the **View** menu or their keyboard shortcuts.

#### Panel Reference

| Panel | Default Position | Toggle Shortcut |
|---|---|---|
| **Recents & Favorites** | Left | Ctrl+4 |
| **Explorer** | Left | Ctrl+E |
| **Playlists** | Right | Ctrl+L |
| **Player** | Bottom | Ctrl+H (minimize) |
| **Radio Browser** | Right | Ctrl+3 |
| **Podcasts** | Right | Ctrl+2 |
| **Debug Console** | Bottom | (Tools menu) |

> **Note:** The Radio Browser and Podcasts panels are created only when you first toggle them on — they do not consume resources until needed.

#### Panels Toolbar

A dedicated toolbar below the main toolbar gives each panel — Player, Recents/Favorites, Explorer, Playlists, Radio, Podcasts, and Console — a **Show/Hide** button and a **Float** button. Float detaches the panel into its own window; toggle it again to redock. Float is only available while the panel is visible.

#### Player Panel Minimization

The Player panel behaves slightly differently from the others. The **View > Minimize Player** menu item (Ctrl+H) collapses the player to show only the Play/Pause button and the minimize toggle. Pressing Ctrl+H again or clicking the toggle button restores the full player controls. This is useful when you want to listen to audio without the full player taking up screen space.

Keyboard shortcuts are available for toggling each panel's visibility and for moving keyboard focus directly to a panel. See [Section 3.1](03-customization-options.md#31-shortcuts) for the complete shortcut reference.

The dock layout (positions and visibility state) is saved automatically and restored the next time you open PlayForm.

---

## 2.2. Player

The Player panel is the heart of PlayForm. It is divided into these areas, from top to bottom:

1. **Video Display** — The area where video content is rendered. For audio-only files, this area remains black. A loading overlay appears while online media is being resolved.
2. **Segment Timeline** — A visual timeline bar that shows the current playback progress, loop segments (as highlighted blocks), and bookmark markers (as vertical lines). You can click and drag to add or move loop segments and bookmarks directly.
3. **Player Controls** — The main transport bar with all playback buttons, the seek slider, volume controls, and more.
4. **Side Panel** — A collapsible accordion of six sections, toggled with the **Show/Hide Side Panel** button. Click a section's header to open it; only one is open at a time.

| Section | Contents |
|---|---|
| **Chapters** | Lists chapters for the current media; click one to jump to it. |
| **Subtitles** | Current subtitle text, with the active line highlighted. |
| **Equalizer** | Enable toggle, presets, preamp, and per-band gain sliders. |
| **Color Adjustments** | Brightness, Contrast, Gamma, Hue, and Saturation sliders. |
| **Video Effects** | Deinterlace and Deband toggles. |
| **Audio Filters** | Enable and configure available mpv audio filters, each with its own parameters. |

- **Chapters** — Populated from the file's embedded chapter markers, if any. Click an entry to jump to it; the current chapter is highlighted.
- **Color Adjustments** — Brightness, Contrast, Gamma, Hue, and Saturation sliders for video playback.
- **Video Effects** — **Deinterlace** and **Deband** toggles.
- **Audio Filters** — Twelve mpv filters, each enabled and configured independently: Echo, Reverb, Low Pass, High Pass, Band Pass, Compressor, Limiter, Gate, Flanger, Chorus, Pitch Shift, Tempo Scale.

### Player Controls (Transport Bar)

The transport bar is organized into two rows:

**Row 1 — Track Info:** The current track's filename is displayed on the left. Right-clicking it — or the video display — opens a context menu: **Copy Path**, **Open in Explorer** (local files), and for YouTube sources **Show YouTube Info**, **Download Subtitle…**, and **View Comments…**; **View Media Metadata…** is available for local files and other supported sources.

**Row 2 — Controls** (left to right):

- **Previous** — Jumps to the previous track.
- **Rewind** — Seeks backward by the configured offset.
- **Play/Pause** — Toggles playback. Icon and label switch between play and pause.
- **Forward** — Seeks forward by the configured offset.
- **Next** — Jumps to the next track.
- **Repeat** — Cycles repeat mode: **Off** → **Repeat: All** → **Repeat: One** → **Off**.
- **Shuffle** — Toggles shuffle mode: **Shuffle: Off** ↔ **Shuffle: On**.
- **Bookmarks** — Opens the Bookmarks dialog for the current file.
- **Screenshot** — Takes a screenshot of the current video frame.
- **Seek slider** — Draggable slider showing playback position. Drag to seek to any point.
- **Mute button** — Toggles mute (icon shows muted/unmuted state).
- **Volume slider** — Horizontal slider from 0 to 200.
- **Time display** — Shows current position and total length as MM:SS / MM:SS.
- **More (…)** — Opens a popup menu with additional options (see below).
- **Minimize** — Toggles the minimize-controls mode.

#### The "More" (…) Menu

Clicking the **…** button opens a popup with the following submenus and actions:

| Submenu / Action | Options |
|---|---|
| **Speed** ▶ | 0.25×, 0.50×, 0.75×, 1.0×, 1.25×, 1.5×, 1.75×, 2.0×, 2.5×, 3.0× (1.0× is default) |
| **Aspect Ratio** ▶ | 16:9, 4:3, 1:1, 16:10, 5:4, 21:9, 32:9, 2.35:1, 2.39:1 |
| **Scale** ▶ | 0.25, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5 |
| **Rotate** ▶ | 0°, 90°, 180°, 270° |
| **Flip Horizontal** | Checkable — mirrors the video horizontally. |
| **Flip Vertical** | Checkable — mirrors the video vertically. |
| **Fullscreen** | Toggle checkable — enters or exits fullscreen mode. |
| **Reverse Playback** | Checkable — plays audio in reverse. Only available for audio-only media. |

#### Fullscreen

Press F11 or use the More menu to enter fullscreen. Press Esc to exit. In fullscreen mode, the video fills the entire screen.

#### Screenshots

Click the **Screenshot** button or press Ctrl+S to capture the current video frame. Screenshots are saved to the `Screenshots/` folder inside the PlayForm data directory. The image format (JPG, PNG, or TIFF) is configurable in Preferences (default: PNG).

### Bookmarks & Repeat Loops

The Player supports two navigation features that help you mark and revisit positions in a track.

#### Bookmarks

A bookmark is a saved position within a file. You can add as many bookmarks as you want per file. Add a bookmark at the current position, navigate between bookmarks, delete them, and jump to the 1st through 10th bookmark — all via keyboard shortcuts listed in [Section 3.1](03-customization-options.md#31-shortcuts). The Bookmarks dialog (also opened via shortcut) lists all bookmarks by timestamp. Right-click a bookmark to delete it individually, or choose to clear all bookmarks for the current file. Bookmarks are also displayed as vertical markers on the Segment Timeline.

#### A-B Repeat Loops

An A-B repeat loop lets you define a section of a track to play on repeat. Multiple non-overlapping loops per file are supported. Set loop start and end points, clear loops, and navigate between loops using keyboard shortcuts listed in [Section 3.1](03-customization-options.md#31-shortcuts). When both a start and end point are set, playback automatically jumps back to the start when it reaches the end. Loops appear as highlighted segments on the Segment Timeline, where you can also create, resize, and remove them with the mouse.

Loop segments and bookmarks are saved per-file and restored automatically when you reopen that file in a future session.

### Subtitles

When a video file is loaded, PlayForm automatically searches the same folder for a subtitle file with a matching filename. Supported subtitle formats loaded during playback include: .srt, .vtt, .smi, .sami, .scc, .dfxp, .ttml, .sub, and .ass.

Subtitle text appears in the **Subtitles** section of the side panel, with the currently active line highlighted in yellow.

**Subtitle language** is configurable in Preferences. If text-to-speech is enabled (also in Preferences), PlayForm will read each subtitle aloud using the Windows SAPI5 engine.

The Player has a comprehensive set of keyboard shortcuts covering playback control, seeking, volume, fullscreen, bookmarks, repeat loops, and screenshots. All shortcuts are configurable and can be remapped via **Options > Manage Hotkeys** (F4). See [Section 3.1](03-customization-options.md#31-shortcuts) for the complete Player shortcut reference.

---

## 2.3. Explorer

The Explorer panel is a full-featured file browser integrated into PlayForm. Toggle it with Ctrl+E or **View > Show Explorer**.

### Layout

The Explorer panel is split into two main sections:

**Left section — Library:** A list of saved folder paths that serve as quick-access bookmarks to your media directories. Right-click a folder in the file view and choose **Add to library** to save it here.

**Right section — File Browser:**

| Sub-panel | Description |
|---|---|
| **Path bar** | Displays the current directory path. You can type or paste a new path and press Enter to navigate there directly. The **Parent Directory** button moves up one folder level. |
| **Search box** | Searches cataloged folders (see [Section 3.3](03-customization-options.md#33-manage-database)) for matching files. |
| **Files list** | Lists all folders first, then all supported media files. Double-click a folder to enter it; double-click a file to play it in the main player. Press Space to play/pause a selected file, and Backspace to navigate up one directory. |
| **Image preview** | When a file with an image extension (.png, .jpg, .bmp, etc.) is selected, a scaled preview is shown to the right. Hidden when a non-image file is selected. |
| **Media preview** | A small preview player that can play audio and video files directly within the Explorer panel without affecting the main player. |

### Navigation

- **Enter a folder:** Double-click it in the file list, or type its path in the path bar and press Enter.
- **Go up one level:** Press Backspace or click the **Parent Directory** button.
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
- **Add Current Folder to Database** (toolbar) — Queues the currently open folder for cataloging, so its files become searchable (see [Section 3.3](03-customization-options.md#33-manage-database)).

**Sort options:** Files can be sorted by **Name (A–Z / Z–A)** or by **Date (Newest first / Oldest first)**.

### File Info

When a file is selected, the Explorer displays its type extension, date modified, and size.

### Preview Player Bar

The Player Bar at the bottom of the Explorer is a compact transport control for the in-panel preview player:

- **Click center area:** Play/Pause toggle.
- **Click left of center:** Seek backward.
- **Click right of center:** Seek forward.
- **Click the bottom bar:** Seek to that position (percentage-based).

An **Auto Play** checkbox (on by default) controls whether selecting a file automatically starts preview playback. A **Volume** spinbox (0–100%) controls the preview player's volume independently of the main player.

---

## 2.4. Playlists

The Playlists panel lets you create, manage, and switch between multiple playlists. Toggle it with Ctrl+L or **View > Show Playlists**.

### Layout

The panel is split horizontally:
- **Left side — Playlist list:** Shows all your playlists by name. Double-click a playlist name to rename it.
- **Right side — Track view:** Displays the tracks in the currently selected playlist as a table with four columns: **File Name**, **Title**, **Artist**, and **Album**.

### Managing Playlists

| Action | How |
|---|---|
| **Create a new playlist** | Click the **Create Playlist** button, enter a name, and click OK. |
| **Rename a playlist** | Double-click its name in the playlist list. |
| **Import a playlist** | Click the **Import Playlist** button and select a .json, .m3u, .m3u8, .pls, or .xspf file. |
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
- Use Shift+Up and Shift+Down to move the selected track(s) up or down.

**Sorting tracks:** Right-click > **Sort By** offers sorting by File Name, Title, Artist, or Album, each in ascending or descending order.

**Playing a track:** Double-click a track row or press Enter on a selected track to start playing the playlist from that position.

### Storage

Playlists are saved in the `data/playlists/` directory. An index file maps playlist names to their file paths. Playlists are automatically saved when you switch between them and when the application closes.

---

## 2.5. Recents and Favorites

The Recents & Favorites panel is docked on the left by default and provides quick access to your most frequently used media. It contains two tabs:

### Favorites Tab

Lists all files you have explicitly marked as favorites. Items are displayed by filename, and alternating row colors improve readability.

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

Double-click or press Enter on any file in either tab to play it immediately in the main player. Both Favorites and Recents are stored in PlayForm's database and persist across application restarts.

---

## 2.6. Media Providers

PlayForm includes two built-in online media sources: Podcasts and Internet Radio.

### 2.6.1. Podcasts

The Podcasts panel lets you subscribe to podcast RSS or Atom feeds and browse their episodes within PlayForm. Toggle it with Ctrl+2 or **View > Show Podcasts**.

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

Keyboard shortcuts for navigating the entries tree (select, page, jump to first/last, play) are listed in [Section 3.1](03-customization-options.md#31-shortcuts).

---

### 2.6.2. Radio

The Radio Browser panel connects to the [Radio Browser](https://www.radio-browser.info/) community directory, which catalogs thousands of free internet radio stations worldwide. Toggle it with Ctrl+3 or **View > Show Radio Browser**.

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

**Previous:** [1. Software Overview](documentation.md) | **Next:** [3. Customization and Options →](03-customization-options.md)

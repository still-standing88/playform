[← 2. A Tour of the Program's User Interface](02-interface-tour.md) | [Table of Contents](documentation.md#table-of-contents) | [4. Tools →](04-tools.md)

---

# 3. Customization and Options

## 3.1. Shortcuts

PlayForm has **99 configurable keyboard shortcuts** organized into six categories: **Global**, **Main interface**, **Explorer**, **Player**, **Multi Device Capture**, and **Speech Converter**. All shortcuts can be remapped via the Hotkeys dialog (**Options > Manage Hotkeys**, F4).

> **Note:** The Multi Device Capture and Speech Converter shortcuts are dialog-scoped: they only work while that tool's window has focus, unlike the Global shortcuts.

### Managing Shortcuts

Open the Hotkeys dialog via **Options > Manage Hotkeys** or press F4. Use the **Search hotkeys** box at the top to filter the tree down to matching actions.

The tree lists the six categories with their actions underneath, each showing its current key in the **Shortcut** column. The checkbox on an action row enables or disables that shortcut. To change a shortcut:

1. Click its Shortcut cell (double-clicking, or selecting the row and pressing Enter, works too) — an editing panel opens below the tree.
2. Type the combination you want (for example `Ctrl+Shift+P`), or click **Capture key** and press the keys; press Esc while capturing to cancel. Clearing the field unbinds the shortcut.
3. Press Enter or click elsewhere to accept.

You can also right-click an action for **Disable**/**Enable**, **Unbind shortcut**, and **Reset hotkey**.

The buttons along the bottom behave as follows:

| Button | Effect |
|---|---|
| **Reset to Default** | Restores every shortcut to its factory default, after a confirmation. |
| **Apply** | Saves your changes and activates them immediately, without closing the dialog. |
| **OK** | Saves your changes and closes the dialog. |
| **Cancel** | Discards changes made since the last Apply and closes the dialog. |

Shortcut settings are saved to `data/key_config.cfg`. If this file is missing or corrupted, PlayForm automatically restores the factory defaults.

---

### Default Shortcut Reference

#### Global Shortcuts

These shortcuts are registered with the operating system, so they work even when PlayForm is not the active window.

| Action | Default Key |
|---|---|
| Play/Pause | Ctrl+Win+P |
| Mute/Unmute | Ctrl+Win+M |
| Volume Down | Ctrl+Win+F7 |
| Volume Up | Ctrl+Win+F8 |
| Previous | Ctrl+Win+F9 |
| Next | Ctrl+Win+F10 |

#### Main Interface Shortcuts

These shortcuts control the main window, menus, and panel visibility.

| Action | Default Key |
|---|---|
| Open file | Ctrl+O |
| Open folder | Ctrl+Shift+O |
| Open URL | Ctrl+U |
| Close Currently playing Media | Ctrl+W |
| Show/Hide explorer | Ctrl+E |
| Show/Hide player controls | Ctrl+H |
| Show/Hide playlists | Ctrl+L |
| Toggle playlists | Ctrl+1 |
| Toggle podcasts | Ctrl+2 |
| Toggle radio | Ctrl+3 |
| Toggle recents/favorites | Ctrl+4 |
| Focus playlists | Alt+1 |
| Focus podcasts | Alt+2 |
| Focus radio | Alt+3 |
| Focus recents/favorites | Alt+4 |
| Hide window | Alt+H |
| Exit | Alt+X |
| Focus explorer | Alt+E |
| Focus player | Alt+P |
| Documentation | F1 |
| Hotkeys dialog | F4 |
| Preferences dialog | Ctrl+P |
| Restart application | Ctrl+Shift+R |

#### Explorer Shortcuts

These shortcuts are active when the Explorer panel has focus.

| Action | Default Key |
|---|---|
| Play/Pause | Space |
| Backward | Left |
| Forward | Right |
| Stop | Ctrl+Space |
| Volume up | Ctrl+Up |
| Volume down | Ctrl+Down |
| Search files/folders | F3 |

#### Player Shortcuts

These shortcuts are active when the Player panel has focus.

| Action | Default Key |
|---|---|
| Play/Pause | Space |
| Backward (seek) | Left |
| Forward (seek) | Right |
| Stop | Ctrl+Space |
| Mute/Unmute | M |
| Previous track | Page Up |
| Next track | Page Down |
| Jump to beginning | Home |
| Jump to the end | End |
| Jump to 10% / 30% / 50% / 70% / 90% | 1 / 2 / 3 / 4 / 5 |
| Show playlist dialog | Ctrl+Shift+P |
| Show queue dialog | Ctrl+Shift+L |
| Toggle repeat mode | Ctrl+R |
| Volume up | Up |
| Volume down | Down |
| Fullscreen | F11 |
| Exit fullscreen | Esc |
| Take snapshot | Ctrl+S |
| Bookmarks list | Ctrl+B |
| Go to time | Ctrl+G |
| New mark at current position | K |
| Repeat loop start | [ |
| Repeat loop end | ] |
| Clear repeat loop | Backspace |
| Previous repeat loop | Ctrl+[ |
| Next repeat loop | Ctrl+] |
| Delete current bookmark | Delete |
| Previous bookmark | Ctrl+Left |
| Next bookmark | Ctrl+Right |
| Mark 1–10 position | Ctrl+1 … Ctrl+9, Ctrl+0 (mark 10) |
| Pan up / down / left / right | Shift+Up / Shift+Down / Shift+Left / Shift+Right |
| Rotate video | T |
| Flip horizontal | H |
| Flip vertical | V |
| Speed up | F |
| Speed down | D |
| Reverse playback | R |
| Previous subtitle line | Alt+Left |
| Next subtitle line | Alt+Right |

#### Multi Device Capture Shortcuts

These shortcuts only work while the Multi Device Capture window has focus. See [Section 4.6](04-tools.md#46-multi-device-capture).

| Action | Default Key |
|---|---|
| Start capture | Ctrl+Alt+R |
| Pause/Resume capture | Ctrl+Alt+P |
| Stop capture | Ctrl+Alt+S |

#### Speech Converter Shortcuts

These shortcuts only work while the Speech Converter window has focus. See [Section 4.5](04-tools.md#45-speech-converter).

| Action | Default Key |
|---|---|
| Speak / Pause | F7 |
| Stop speaking | F8 |
| Open text file | Ctrl+O |
| Save as audio | Ctrl+S |
| Parameters | Ctrl+F |

---

## 3.2. Preferences

The Preferences dialog (**Options > Manage Preferences**, Ctrl+P) allows you to configure PlayForm's behavior. Settings are organized into seven tabs: **General**, **Media**, **Subtitles**, **Accessibility**, **Advanced**, **Database**, and **Downloads**.

Preferences are stored in `data/prefs.json`. If the file is missing or corrupted, PlayForm automatically restores the factory defaults. Changes to certain settings (language, MPV logging, extra MPV options, or debug level) require an application restart, which PlayForm will prompt you to perform.

### General Tab

- **Language** — the user interface language (English, French, Arabic, Spanish). Requires a restart.
- **Screenshot Format** — JPG, PNG, or TIFF (PNG by default) for screenshots taken with Ctrl+S.
- **Theme** — System, Light, or Dark. Changes apply immediately, without a restart.
- **Auto Check for Updates** — automatically checks for newer versions of PlayForm at startup (on by default).
- **Save URLs** — keeps URLs you enter across sessions for quick re-access (off by default).

### Media Tab

- **Volume Offset** — how much the volume changes per step when adjusted via shortcuts or the menu (1–20, default 5).
- **Seek Offset** — how far seeking forward/backward jumps per step, in seconds (1–60, default 5).
- **Audio Device** — the output audio device, populated with all available devices on your system.

### Subtitles Tab

**Source:**
- **Preferred Language** — the subtitle language to prefer for online (yt-dlp) sources.

**On-Video Rendering:**
- **Draw subtitles on the video** — master switch for rendering subtitles over the video. The Subtitles section of the player's side panel shows its text list either way. Every other setting in this group is only enabled while this is on.
- **Font** (any installed font; generic families such as `sans-serif` are accepted), **Font Size** (8–200, default 38), **Bold**, and **Scale** (a multiplier applied on top of the font size).
- **Text Colour**, **Background Colour**, and **Outline Colour**.
- **Outline Thickness** and **Shadow Offset**, both 0–20.
- **Vertical Position** — 0 is the top of the video, 100 (the default) the bottom.
- **ASS/SSA Styling** — whether the settings above override the styling embedded in ASS/SSA subtitle files (they usually carry their own styling).

### Accessibility Tab

- **Enable speech accessibility feedback** — master toggle for spoken announcements (off by default). Status-bar messages that carry an announcement category are also read aloud when their category is enabled; the status-bar text itself always shows regardless of this setting.
- **Interrupt previous speech** — when on (default), a new announcement stops the one currently being spoken instead of queueing behind it.
- **Spoken Events: Announcements…** — opens a dialog with a checkable list of event categories (Playback, File Explorer, Playlists, Tools, Dialogs & Windows, Downloads, Database & Cataloging, Podcasts & Radio, Subtitles, Multi Device Capture, General), plus **Enable All** and **Disable All** buttons.
- On macOS and Linux, **Configure Voice: Voice Settings…** opens a dialog for choosing the **Voice** and adjusting its **Volume** and **Rate**. This row isn't shown on Windows.

### Advanced Tab

**MPV Settings:**
- **MPV Logging** — enables debug logging from the media engine (on by default). While it's on, a **Debug Level** field (0–2, where 2 is the most verbose) appears.
- **Extra MPV Options** — custom command-line options passed to the media backend; the syntax is checked when you leave the field.

**yt-dlp Settings:**
- **Path Setting** — a list of the three configurable paths; select one to edit it in the **Path** field below, filled in with **Browse** (a file picker for the cookies file, a folder picker for the two paths):
  - **YouTube Cookies File** — a `cookies.txt` file exported from your browser, used for accessing authenticated content on YouTube and other sites. The file is copied into the app's data folder, and each yt-dlp run is given a throwaway copy of that — your own file is never modified.
  - **yt-dlp Path** — the yt-dlp binary's folder. Normally managed automatically via the utility downloader, but can be set manually.
  - **FFmpeg Path** — the FFmpeg binary's folder. Normally managed automatically, but can be set manually if you have a custom FFmpeg installation.
- **yt-dlp Logging** — enables debug output from yt-dlp. While it's on, a **Verbose Output** checkbox appears for full detail.

### Database Tab

- **Catalog audio files** / **Catalog video files** — which file types are indexed when a folder is cataloged for search (both on by default).
- **Remember Explorer search history** — keeps a history of Explorer search terms across sessions (on by default).
- **Clear Search History** — clears the stored Explorer search history immediately.

### Downloads Tab

**Transfers:**
- **Max Parallel Downloads** — how many downloads run at once (1–10, default 2).
- **Speed Limit** — a cap in KB/s, where 0 shows "Unlimited" (the default).
- **Retry Count** (0–20, default 3) and **Retry Delay** (250–60000 ms, default 2000) — how many times a failed download is retried, and how long to wait between attempts.

**Notifications:**
- **Notify when a download finishes** — shows a system tray notification when a download completes or fails (on by default).

**Locations:**
- **Default Download Folder** — where new downloads are saved. Leave empty to use the application's own downloads folder.
- **Podcasts Folder** — where podcast episodes are saved, each feed in its own subfolder. Leave empty to use the application's own podcasts folder.

**Network:**
- **Proxy Settings…** — opens the network proxy dialog; the current proxy is summarized next to the button ("No proxy" while disabled).

---

## 3.3. Manage Database

The Manage Database dialog (**Options > Manage Database…**) lists every folder cataloged for Explorer search, with its file count and last-scanned time. Folders are added here or via Explorer's **Add Current Folder to Database** action.

| Action | Description |
|---|---|
| **Add Folder…** | Browse for a folder and catalog it. |
| **Rescan Selected** | Re-scans the selected folder(s) for changes. |
| **Remove Selected…** | Removes the selected folder(s) and their indexed entries (confirmation required; files on disk are untouched). |
| **Clear & Rebuild Catalog…** | Wipes the entire index and re-scans every cataloged folder (confirmation required). |

**Index Statistics** shows the total number of indexed files and how many had errors during cataloging.

A cataloging scan runs in the background; progress is shown in a dialog on top of Manage Database, where it can be paused or the whole scan canceled. Minimizing either dialog leaves a restore button in the menu-bar corner (see [Section 2.1.1](02-interface-tour.md#211-menubar)).

---

**Previous:** [← 2. A Tour of the Program's User Interface](02-interface-tour.md) | **Next:** [4. Tools →](04-tools.md)

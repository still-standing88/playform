[← 2. A Tour of the Program's User Interface](02-interface-tour.md) | [Table of Contents](documentation.md#table-of-contents) | [4. Tools →](04-tools.md)

---

# 3. Customization and Options

## 3.1. Shortcuts

PlayForm has **72 configurable keyboard shortcuts** organized into four categories: **Global**, **Main Interface**, **Explorer**, and **Player**. All shortcuts can be remapped via the Hotkeys dialog (**Options > Manage Hotkeys**, F4).

> **Note:** Multi Device Capture's three transport hotkeys (Start/Pause-Resume/Stop capture) are dialog-scoped rather than global, and are configured separately in the same Hotkeys dialog under a **Multi Device Capture** section. See [Section 4.6](04-tools.md#46-multi-device-capture).

### Managing Shortcuts

Open the Hotkeys dialog via **Options > Manage Hotkeys** or press F4. The dialog shows a tree view with the four shortcut categories at the top level and individual actions underneath. Each row displays the action name and its current key binding.

| Action | How |
|---|---|
| **Change a shortcut** | Click the Shortcut column for an action, then press the desired key combination. Press Enter or move focus to accept. |
| **Reset to Default** | Click the **Reset to Default** button. All shortcuts revert to their factory defaults after confirmation. |
| **Apply** | Click **Apply** to save changes and activate them immediately without closing the dialog. |
| **OK** | Saves changes and closes the dialog. |
| **Cancel** | Discards any uncommitted edits and closes the dialog. |

Shortcut settings are saved to `data/key_config.cfg`. If this file is missing or corrupted, PlayForm automatically restores the factory defaults.

---

### Default Shortcut Reference

#### Global Shortcuts

These shortcuts work regardless of which panel has focus.

| Action | Default Key |
|---|---|
| Play/Pause | Ctrl+Win+P |
| Mute/Unmute | Ctrl+Win+M |
| Volume Down | Ctrl+Win+F7 |
| Volume Up | Ctrl+Win+F8 |
| Previous | Ctrl+Win+F9 |
| Next | Ctrl+Win+F10 |

> **Note:** Global shortcuts work when PlayForm has the application focus.

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
| Preferences Dialog | Ctrl+P |

#### Explorer Shortcuts

These shortcuts are active when the Explorer panel has focus.

| Action | Default Key |
|---|---|
| Play/Pause | Space |
| Backward | Left |
| Forward | Right |
| Stop | Ctrl+Space |
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
| Toggle repeat mode | Ctrl+R |
| Volume up | Up |
| Volume down | Down |
| Fullscreen | F11 |
| Exit fullscreen | Esc |
| Take snapshot | Ctrl+S |
| Bookmarks list | Ctrl+B |
| New mark at current position | K |
| Repeat loop start | [ |
| Repeat loop end | ] |
| Clear repeat loop | Backspace |
| Previous repeat loop | Ctrl+[ |
| Next repeat loop | Ctrl+] |
| Delete current bookmark | Delete |
| Previous bookmark | Ctrl+Left |
| Next bookmark | Ctrl+Right |
| Mark 1 position | Ctrl+1 |
| Mark 2 position | Ctrl+2 |
| Mark 3 position | Ctrl+3 |
| Mark 4 position | Ctrl+4 |
| Mark 5 position | Ctrl+5 |
| Mark 6 position | Ctrl+6 |
| Mark 7 position | Ctrl+7 |
| Mark 8 position | Ctrl+8 |
| Mark 9 position | Ctrl+9 |
| Mark 10 position | Ctrl+0 |
| Close media | Ctrl+W |

---

## 3.2. Preferences

The Preferences dialog (**Options > Manage Preferences**, Ctrl+P) allows you to configure PlayForm's behavior. Settings are organized into five tabs: **General**, **Media**, **Accessibility**, **Advanced**, and **Database**.

Preferences are stored in `data/prefs.json`. If the file is missing or corrupted, PlayForm automatically restores the factory defaults. Changes to certain settings (language, MPV logging, MPV arguments, or debug level) require an application restart, which PlayForm will prompt you to perform.

### General Tab

| Setting | Options | Default | Description |
|---|---|---|---|
| **Language** | EN, FR, AR, ES | EN | User interface language. Requires restart to apply. |
| **Screenshot Format** | JPG, PNG, TIFF | PNG | File format for screenshots taken with Ctrl+S. |
| **Color Theme** | System, Light, Dark | System | UI color scheme. Changes apply immediately without restart. |
| **Auto Check for Updates** | On / Off | On | Automatically checks for newer versions of PlayForm at startup. |
| **Save URLs** | On / Off | Off | Saves entered URLs across sessions for quick re-access. |

### Media Tab

| Setting | Range | Default | Description |
|---|---|---|---|
| **Volume Offset** | 1–20 | 5 | Amount by which volume changes per step (via shortcuts or menu). |
| **Seek Offset** | 1–60 seconds | 5 | Amount by which forward/backward seeking jumps per step. |
| **Audio Device** | (list) | 0 | Output audio device. Populated with all available devices on your system. |

### Accessibility Tab

| Setting | Options | Default | Description |
|---|---|---|---|
| **Enable Speech Feedback** | On / Off | Off | Master toggle for text-to-speech accessibility. When enabled, status bar messages and subtitle text are spoken aloud. |
| **Interrupt Previous Speech** | On / Off | On | When enabled, a new utterance stops the currently playing one. When disabled, speech is queued. |
| **Voice** | (list) | (system default) | TTS voice selection. |
| **Volume** | 0.0–100.0 | 80.0 | Speech volume. |
| **Rate** | 0.1–10.0 | 1.0 | Speech rate, where 1.0 is normal speed. |

### Advanced Tab

**MPV Settings:**

| Setting | Options | Default | Description |
|---|---|---|---|
| **Enable MPV Logging** | On / Off | On | Enables debug logging from the media engine. |
| **Debug Level** | 0–2 | 0 | Debug verbosity (0 = minimal, 2 = most verbose). Only shown when logging is enabled. |
| **Extra MPV Options** | (text) | *(empty)* | Custom options passed to the media backend. |

**yt-dlp Settings:**

| Setting | Description |
|---|---|
| **Cookies File** | Path to a `cookies.txt` file exported from your browser, used for accessing authenticated content on YouTube and other sites. Browse to select the file. |
| **yt-dlp Path** | Directory where yt-dlp binary is located. Normally managed automatically via the utility downloader, but can be set manually. |
| **Enable yt-dlp Logging** | Toggle to enable debug output from yt-dlp. When on, a **Verbose Output** checkbox appears for full detail. |
| **FFmpeg Path** | Directory where FFmpeg binary is located. Normally managed automatically, but can be set manually if you have a custom FFmpeg installation. |

### Database Tab

| Setting | Options | Default | Description |
|---|---|---|---|
| **Catalog audio files** | On / Off | On | Include audio files when a folder is cataloged for search. |
| **Catalog video files** | On / Off | On | Include video files when a folder is cataloged for search. |
| **Remember Explorer search history** | On / Off | On | Keeps a history of Explorer search terms across sessions. |
| **Clear Search History** | button | — | Clears the stored Explorer search history immediately. |

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

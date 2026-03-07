# PlayForm Documentation

---

# 1. Software Overview

## 1.1 Introduction

**PlayForm** is a free, modern media player for Windows, designed to be straightforward to use while offering a wide range of features for everyday listening and viewing. Whether you want to play a song from your music folder, catch up on a podcast, watch a video file, or tune into an internet radio station, PlayForm brings it all together in one application.

PlayForm is built around accessibility and ease of use. The interface is organized into clearly separated panels — a file explorer, a media player, playlists, and media provider panels — each of which can be shown, hidden, docked, or rearranged to suit the way you work. Everything is keyboard-accessible, and most actions are available through the menu bar, toolbar buttons, or keyboard shortcuts.

PlayForm is published by **Still Standing** and is licensed under the MIT open-source license. The application's source code and updates are available on [GitHub](https://github.com/still-standing88/playform).

---

## 1.2. Features

PlayForm includes the following capabilities:

**Playback**
- Play local audio and video files from your computer.
- Open individual files, entire folders, or type in a web address (URL) to stream media directly.
- Full playback controls: play, pause, stop, rewind, fast-forward, previous track, and next track.
- Adjustable playback speed (1×, 1.5×, 2×, 2.5×, 3×).
- Volume control with mute toggle.
- Seek bar for jumping to any point in the current file.
- Repeat a single track or loop through a playlist.
- Shuffle playback order.
- Jump to the beginning or end of a track with a single key press.

**Video**
- Dedicated video display area with full-screen support (`F11`).
- Adjustable aspect ratio (16:9, 4:3, 1:1 and more).
- Video scale options (0.25× through 5×).
- Take snapshots (screenshots) from video in JPG, PNG, or TIFF format.
- Automatic subtitle loading — if a subtitle file with the same name as your video is in the same folder, PlayForm will load it automatically.

**Subtitles**
- Subtitles are displayed directly below the video as you watch.
- Supported subtitle formats: SRT, VTT, SMI/SAMI, SCC, DFXP/TTML, SUB, ASS.

**Bookmarks & Repeat Loops**
- Mark any position in a file as a bookmark and jump back to it any time.
- Save up to 10 quick-access marks (`Ctrl+1` through `Ctrl+0`) per file.
- Set a looping range (A-B repeat) with a start and end point, so a section plays on repeat.
- Multiple loops per file are remembered between sessions.

**Playlists**
- Create, name, and manage multiple playlists.
- Add files and folders to any playlist.
- Playlists are saved and restored each time you open the app.

**File Explorer**
- Built-in file browser panel to navigate your computer's folders.
- Filter and search for media files by name.
- Double-click or press Space to play any file directly from the explorer.

**Recents & Favorites**
- Automatically keeps track of recently played files so you can quickly return to them.
- Mark any file as a favorite for fast access.

**Internet Radio**
- Browse and search thousands of live internet radio stations, powered by the RadioBrowser community directory.
- Filter stations by country, language, or tag (genre).
- Save favorite stations for quick access.

**Podcasts**
- Add podcast RSS feed URLs to follow shows.
- Browse and search episodes within each feed.
- Play any episode directly from within the app.

**Online Media / YouTube**
- Paste any YouTube URL (or other supported stream URL) into PlayForm's URL dialog to play it without downloading first.
- Uses `yt-dlp` under the hood for broad URL compatibility.

**Downloading**
- Built-in Download Center to download audio or video from URLs to your computer.

**Tools**
- **Batch Converter** — Convert multiple media files to different formats at once using FFmpeg.
- **Extractor** — Extract audio from video files.
- **Tag Editor** — View and edit metadata (title, artist, album, etc.) on your audio files.
- **Thumbnail Generator** — Generate thumbnail images from video files.
- **Subtitle Converter** — Convert subtitle files between different formats.
- **Subtitle Editor** — Edit subtitle content and timing.

**Interface & Accessibility**
- Fully keyboard-navigable interface with customizable shortcuts.
- Global hotkeys let you control playback (play/pause, volume, skip) even when PlayForm is not the focused window or is minimized to the system tray.
- System tray icon for quick access and background playback.
- Customizable toolbar — add, remove, and reorder toolbar buttons.
- Dockable panels that remember their position between sessions.

---

## 1.3. Supported Media Formats

PlayForm can open a wide range of audio and video file types. The list below covers the most common formats.

**Audio Formats**

| Format | File Extension |
|--------|---------------|
| MP3 | `.mp3` |
| FLAC (Lossless) | `.flac` |
| WAV | `.wav` |
| Ogg Vorbis | `.ogg` |
| Advanced Audio Coding | `.aac` |
| MPEG-4 Audio | `.m4a` |
| Windows Media Audio | `.wma` |
| Opus | `.opus` |
| AIFF | `.aiff`, `.aif` |
| Monkey's Audio | `.ape` |
| Matroska Audio | `.mka` |
| MIDI | `.mid`, `.midi` |

**Video Formats**

| Format | File Extension |
|--------|---------------|
| MPEG-4 | `.mp4` |
| Matroska | `.mkv` |
| AVI | `.avi` |
| QuickTime | `.mov` |
| Windows Media Video | `.wmv` |
| Flash Video | `.flv` |
| WebM | `.webm` |
| MPEG-4 Video | `.m4v` |
| MPEG Transport Stream | `.ts`, `.m2ts` |
| 3GPP | `.3gp` |
| Ogg Video | `.ogv` |

> **Tip:** When opening files through **File > Open File**, the file browser will automatically filter to show only supported media files. You can switch the filter to "All Files" if you need to open something not listed above, as PlayForm's underlying media engine (VLC) supports many additional formats beyond those shown here.

---

## 1.4. Online Media Playback

PlayForm can play media that is not stored on your computer. There are three ways to do this:

### Playing a URL

To play an internet stream or an online video:

1. Go to **File > Open URL** (or press `Ctrl+U`).
2. In the dialog that appears, type or paste the web address of the media you want to play.
3. Click **Open** (or press `Enter`).

PlayForm accepts:
- **Direct media URLs** — links that point directly to an audio or video file (e.g., `.mp3`, `.m3u8`, `.mp4` hosted online).
- **YouTube URLs** — paste a YouTube video link and PlayForm will fetch and play it using yt-dlp. No separate download is required.
- **Other streaming URLs** — most URLs supported by yt-dlp work, including many video-sharing platforms.

> **Note:** Playing YouTube and other online content requires an active internet connection. The first time you use this feature, PlayForm may need to check for and download `yt-dlp` if it is not already present.

### Internet Radio

The **Radio** panel (toggle with `Ctrl+3`) connects to the RadioBrowser public directory, which lists thousands of free, live internet radio stations from around the world. You can search by station name, or filter by country, language, or genre tag. Double-click any station to start listening. See [Section 2.6.2](./documentation.md) for a full walkthrough.

### Podcasts

The **Podcasts** panel (toggle with `Ctrl+2`) allows you to follow podcast shows by adding their RSS feed URL. Episodes are listed in chronological order and can be played directly within PlayForm. See [Section 2.6.1](./documentation.md) for a full walkthrough.

---



\# 2. A Tour In the Program's User Interface 



\# 2.1. Main UI



\# 2.1.1. Menubar



\# 2.1.2. Tool Bar.



\# Tool bar Config



\# 2.1.3. Status Bar



\# 2.1.4. Docking panel



\# 2.2. Player



\# 2.3. Explorer.



\# 2.4. Playlists



\# 2.5. Recents and favorites



\# 2.6. Media Providers



\# 2.6.1. Podcasts



\# 2.6.2 Radio



\# 3. Customization and options:



\# 3.1 Shortcuts.



\#3.2. Preferences 



\# 4. Tools



\# 4.1. FFmpeg tools.



\# 4.2. Subtitle Tools.



\# 4.3. Other tools



\# 5. Download Center.



\# 6. Legal



\# Software License.



\# Third Party

PySide6, QT, VLC, FFmpeg, DEno, yt-dlp.



links and respective licenses per each, and usage context in software.




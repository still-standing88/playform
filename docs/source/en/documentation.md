# PlayForm Documentation

---

## Table of Contents

- [1. Software Overview](#1-software-overview)
  - [1.1. Introduction](#11-introduction)
  - [1.2. Features](#12-features)
  - [1.3. Supported Media Formats](#13-supported-media-formats)
  - [1.4. Online Media Playback](#14-online-media-playback)
- [2. A Tour of the Program's User Interface](02-interface-tour.md)
  - [2.1. Main UI](02-interface-tour.md#21-main-ui)
    - [2.1.1. Menubar](02-interface-tour.md#211-menubar)
    - [2.1.2. Toolbar](02-interface-tour.md#212-toolbar)
    - [2.1.3. Status Bar](02-interface-tour.md#213-status-bar)
    - [2.1.4. Docking Panels](02-interface-tour.md#214-docking-panels)
  - [2.2. Player](02-interface-tour.md#22-player)
  - [2.3. Explorer](02-interface-tour.md#23-explorer)
  - [2.4. Playlists](02-interface-tour.md#24-playlists)
  - [2.5. Recents and Favorites](02-interface-tour.md#25-recents-and-favorites)
  - [2.6. Media Providers](02-interface-tour.md#26-media-providers)
    - [2.6.1. Podcasts](02-interface-tour.md#261-podcasts)
    - [2.6.2. Radio](02-interface-tour.md#262-radio)
- [3. Customization and Options](03-customization-options.md)
  - [3.1. Shortcuts](03-customization-options.md#31-shortcuts)
  - [3.2. Preferences](03-customization-options.md#32-preferences)
  - [3.3. Manage Database](03-customization-options.md#33-manage-database)
- [4. Tools](04-tools.md)
  - [4.1. FFmpeg Tools](04-tools.md#41-ffmpeg-tools)
  - [4.2. M4B Tools](04-tools.md#42-m4b-tools)
  - [4.3. Subtitle Tools](04-tools.md#43-subtitle-tools)
  - [4.4. Tag Editor](04-tools.md#44-tag-editor)
  - [4.5. Speech Converter](04-tools.md#45-speech-converter)
  - [4.6. Multi Device Capture](04-tools.md#46-multi-device-capture)
  - [4.7. Other Tools](04-tools.md#47-other-tools)
- [5. Legal](05-legal.md)
  - [5.1. Software License](05-legal.md#51-software-license)
  - [5.2. Third-Party Components](05-legal.md#52-third-party-components)

---

# 1. Software Overview

## 1.1 Introduction

PlayForm is a cross-platform media player that lets you play audio and video files, stream online content from YouTube and other websites, listen to internet radio, and follow podcasts — all from a single application.

---

## 1.2. Features

- **Play any media format** — PlayForm supports every audio and video format that mpv can handle. See [Section 1.3](#13-supported-media-formats) for a list of the most common formats.
- **Play media from any source** — Open local files, folders, or paste URLs to stream from YouTube and hundreds of other websites via yt-dlp.
- **Subtitle integration** — Subtitles are automatically loaded if a matching file is found next to your video. Supports SRT, VTT, ASS, and more. Subtitles can also be read aloud via text-to-speech.
- **Bookmarks and repeat loops** — Mark any position in a track and jump back to it instantly. Set A-B repeat loops to play a section on repeat, with support for multiple loops per file.
- **Built-in media explorer with preview** — Browse your folders with a full file browser right inside the app. Preview audio and video files on the fly without needing to open them in the main player.
- **Media extraction, conversion, and audiobook tools** — Convert between audio and video formats, extract audio or images from videos, generate thumbnails, bind/split/retime M4B audiobooks, and more — all powered by FFmpeg.
- **Tag and subtitle editing** — Edit metadata tags on your audio files (title, artist, album, genre, etc.) and modify subtitle content and timing with built-in editors.
- **Text-to-speech and multi-device recording** — Speak or render text to an audio file with the Speech Converter, and record several cameras, screens, and microphones at once with Multi Device Capture. See [Section 4](04-tools.md).

---

## 1.3. Supported Media Formats

PlayForm can open a wide range of audio and video file types. The list below covers the most common formats; PlayForm's underlying media engine supports many additional formats beyond those shown here.

**Audio Formats**

| Format | File Extension |
|--------|---------------|
| MPEG Audio | .mp1, .mp2, .mp3 |
| FLAC (Lossless) | .flac |
| WAV | .wav |
| Ogg Vorbis | .ogg |
| AAC | .aac |
| AC-3 / E-AC-3 | .ac3, .eac3 |
| DTS | .dts |
| MPEG-4 Audio | .m4a |
| Windows Media Audio | .wma |
| Opus | .opus |
| AIFF | .aiff, .aif |
| WavPack | .wv |
| Monkey's Audio | .ape |
| True Audio | .tta |
| Matroska Audio | .mka |
| Musepack | .mpc |
| RealAudio | .ra |
| AMR | .amr |
| Core Audio Format | .caf |
| Module/Tracker | .s3m, .xm, .mod, .it |
| Speex | .spx |

**Video Formats**

| Format | File Extension |
|--------|---------------|
| MPEG-4 | .mp4 |
| Matroska | .mkv |
| AVI | .avi, .divx |
| QuickTime | .mov |
| Windows Media Video | .wmv, .asf |
| Flash Video | .flv, .f4v |
| RealMedia | .rm, .rmvb |
| WebM | .webm |
| MPEG-4 Video | .m4v |
| MPEG | .mpeg, .mpg, .m2v |
| MPEG Transport Stream | .ts, .m2ts, .mts |
| 3GPP | .3gp |
| Ogg Video | .ogv |
| DVD Video Object | .vob |
| Digital Video | .dv |

> **Tip:** When opening files through **File > Open File**, the file browser automatically filters to show only supported media files. You can switch the filter to "All Files (*.*)" if you need to open something not listed above.

---

## 1.4. Online Media Playback

PlayForm can play media that is not stored on your computer. There are three ways to do this:

### Playing a URL

To play an internet stream or an online video:

1. Go to **File > Open URL** (or press Ctrl+U).
2. In the dialog that appears, type or paste the web address of the media you want to play.
3. Click **Open** (or press Enter).

PlayForm accepts:
- **Direct media URLs** — links that point directly to an audio or video file (e.g., .mp3, .m3u8, .mp4 hosted online). These are played directly.
- **YouTube URLs** — paste a YouTube video or playlist link and PlayForm will resolve and play it. No separate download is required.
- **Other streaming URLs** — most URLs supported by yt-dlp work, including many video-sharing platforms.

### Internet Radio

The **Radio** panel connects to the [Radio Browser](https://www.radio-browser.info/) community directory, which lists thousands of free, live internet radio stations from around the world. You can search by station name, or filter by country, language, or genre tag. Double-click any station to start listening. See [Section 2.6.2](02-interface-tour.md#262-radio) for a full walkthrough.

### Podcasts

The **Podcasts** panel (toggle with Ctrl+2) allows you to follow podcast shows by adding their RSS or Atom feed URL. Episodes are listed in chronological order and can be played directly within PlayForm. See [Section 2.6.1](02-interface-tour.md#261-podcasts) for a full walkthrough.

---

**Next:** [2. A Tour of the Program's User Interface →](02-interface-tour.md)

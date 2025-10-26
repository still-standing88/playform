# 🎬 Media Player Project — Final To-Do List

**Note:** AI Edited and polished

The following outlines the final roadmap and features to be implemented before release. This list includes bug fixes, planned enhancements, build infrastructure, and release requirements.

## 🐞 Bug Fixes

* [ ] Fix Tag Editor bug where OK/Save buttons trigger success message even when no processing occurred.

## 🎥 Core Player Features

* [ ] Implement timeline system for bookmarks and repeat-loop navigation/marking.
* [ ] Add thumbnail generation per file using `ffmpeg`, with local caching.
   * [ ] Include preference toggle to enable/disable caching.
* [ ] Add subtitle tools via `pysubs2`.
* [ ] Add media data viewer (codec, bitrate, resolution, etc.) for both local files and URL streams.
* [ ] Show YouTube video/playlist info (via `yt-dlp` JSON output).
* [ ] Add YouTube video/playlist downloader using `yt-dlp`.
   * [ ] Option to hide the download dialog to the status bar.

## 🌐 Internet / Stream Features

* [ ] Integrate podcast and radio modules:
   * [ ] Either separate sub-windows
   * [ ] Or a single window with tabbed interface.
* [ ] Add check for `yt-dlp` presence in URL dialog.
   * [ ] Warn user or block unsupported URLs if missing.

## 🧰 Tools & Utilities

* [ ] Add view logging under Tools → Logs.
* [ ] Create downloader manager (single queue) for:
   * [ ] Updates
   * [ ] Tools
   * [ ] Add-ons
   * [ ] Option to minimize to status bar
* [ ] Create program downloader to fetch external packages (`yt-dlp`, `ffmpeg`) and updates.
* [ ] Implement CRC verification when downloading files from GitHub.

## 🧩 Configuration & Data Management

* [ ] Merge last positions, bookmarks, and repeat loops into a single JSON file.
* [ ] Implement Dark/Light theme toggle in Preferences.
* [ ] Add language translation system, with live-switching capability.
* [ ] Add file search and organization database for the Explorer view.
* [ ] Implement startup wizard:
   * [ ] Select language
   * [ ] Prompt to install missing tools (`yt-dlp`, `ffmpeg`, etc.)

## 🧑‍💻 Developer & Build Infrastructure

* [ ] Separate development/runtime dependencies using Invoke tasks.
* [ ] Create cross-platform build scripts for Linux, Windows, macOS.
* [ ] Compile external updater executable (PyInstaller/Nuitka one-file).
* [ ] Implement in-app updater with download progress and installation handling.
* [ ] Separate bundled tools (`yt-dlp`, `ffmpeg`) from core app — download them dynamically.
* [ ] Add optional binary signing (custom lightweight signing system, not CA-based).

## 📘 Documentation & Release

* [ ] Write user documentation (Markdown → HTML or in-app viewer).
* [ ] Add release notes generator for build automation.

## 🚀 Optional Quality-of-Life Enhancements

* [ ] UI polish (icons, tooltips, menus).
* [ ] Background threads for thumbnail and metadata generation.
* [ ] Optional system-tray controls (Play/Pause, Next, Stop).
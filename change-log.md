## v1.3.1 Release Notes

### Bug fixes

- App GUI: Various UI fixes and layout adjustments.
- App: Launching a second instance now focuses the existing instance's window and shows it if hidden.
- Explorer: Fixed inconsistent preservation of the media loop state.
- yt-dlp downloader: The progress buffer now reports the latest progress for the selected item without overflowing with information.
- App: Missing files now produce an error message, with an option to remove the entry when opened from Recents.
- App: Opening a file's location in Explorer works on Windows 11 again.

### Features

- yt-dlp downloader: Downloaded files can now be played directly from their right-click menu.
- Multi Device Capture: Sessions now save captured media under `Videos/captures` in the user's home folder by default. The path can be changed in the session's options.
- Multi Device Capture: Switched device capture from the FFmpeg CLI to MediaCap.
- Multi Device Capture: Updated the interface and media options, with a broader selection of capture sources and settings.
- Utilities: Added direct downloads of standalone MediaCap CLI binaries for Windows and Linux, on x64 and ARM64, through Options > Get/Update Utilities.
- Preferences: Added Deno and MediaCap paths alongside yt-dlp and FFmpeg, with validation and missing-tool guidance. MediaCap automatically uses a working global installation when available; Deno path changes apply to playback and downloads.

## v1.3.0 Release Notes

### Bug fixes

- App GUI: Fixed clipped button and label text in longer translations, along with control icon sizing.
- App GUI: Tool dialogs taller than the screen now scroll, and are clamped to the screen when opened.
- App GUI: A file opened from outside the app while the window is still starting is queued instead of being lost.
- App GUI: Main window hotkeys no longer reach the main window while any dialog is open.
- Explorer: Fixed image and video previews not sizing correctly when they appear, and they now shrink properly in a narrow dock.

### Features

- Media playback engine: Chapters and media metadata are now read straight from MPV instead of ffprobe.
- Media playback engine: Aspect ratio, video scaling and screenshot capture are now handled by MPV.

- Player: Added a playback queue that plays before the playlist, with its own view dialog.
- Player: The now-playing playlist and the queue can be opened as dialogs with Ctrl+Shift+P and Ctrl+Shift+L.
- Player: Keys 1-5 seek to 10/30/50/70/90% of the current file.
- Player: Subtitle tracks can be selected, delayed, hidden and stepped line by line.
- Player: Rebuilt audio filters panel: add effects from a categorized picker, edit parameters live, and save your own presets per effect (each effect ships with 15-20 ready-made presets).
- Player: A much larger set of MPV audio effects, including convolution reverb driven by your own impulse-response file.
- Player: Added video pan, plus hotkeys for pan, rotate, flip, speed and reverse.
- Player: Added audio delay and ReplayGain controls.

- Player: Media metadata can be viewed from MPV alongside the ffprobe report.

- Preferences: A new Subtitles preferences panel with an accessible colour picker for subtitle styling.

- App GUI: Faster startup times.
- App GUI: The theme now covers dialogs, custom-drawn controls, list views and icons, and the app inherits the application font.
- App GUI: The hotkeys dialog was rebuilt: every hotkey has an enable checkbox and is edited from a panel with a Capture key button.
- App GUI: Standardized labels and command names across the interface.


- Explorer: Add to Queue from the explorer, search results, recents and favorites.
- Explorer: Open in Explorer added to the file context menus.
- Explorer: View and Filter submenus, with a custom format filter dialog.
- Explorer: An image preview dialog for image files.
- Explorer: Faster listings with delegate-painted rows, responsive re-wrapping and batched lazy loading.

- Explorer: Ctrl+Up and Ctrl+Down adjust the explorer's own volume.


- Downloads: New yt-dlp download manager for YouTube videos, playlists and channels, with a review step before downloading.
- Downloads: "Add From Link File" queues every YouTube video link listed in a text file.
- Downloads: The chosen cookies file is copied and staged, so yt-dlp never rewrites your original.

- Podcasts: Download all episodes of a feed from its context menu, grouped into a folder per podcast.

- Tools: New Speech Converter: text to speech with voice selection, volume, rate, pitch and save to file.
- Tools: New Audiobook Tools (Bind, Split, Slide, Labels, Cover) and Audiobook Combiner (Combine, Metadata Dump) for .m4b files.
- Tools: Batch Converter rebuilt with Source/Convert/Processing/Destination tabs, job presets, pause/resume, a live log and notify-on-finish.
- Tools: Media Extractor rebuilt with audio, video and image modes, and batch conversion now defaults to keeping the original sample rate, bit depth and bitrate.
- Tools: The Tools menu is now organized into FFmpeg Tools, M4B Tools and Subtitle Tools submenus.


- Multi Device Capture: New tool for recording cameras, monitors, windows and audio inputs together, with sessions, per-session sources and pause/resume.
- Multi Device Capture: Live preview for camera, monitor and window sources, and audible monitoring with a level meter for audio inputs.

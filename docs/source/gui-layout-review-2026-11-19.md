# PlayForm GUI layout review — 19 November 2026

Baseline result: normal-size Preferences was usable, but the interface had significant clipping and inconsistent sizing at maximum UI zoom. This review resumed the interrupted GUI inspection from the previous chat. The findings below record the interface before fixes; the implementation update at the end records the subsequent changes.

## Conditions and coverage

- Inspected the existing live Windows app; did not launch a second instance.
- Compared saved zoom level **10** (19-point application font) with level **0** (9-point font), and checked both restored and maximized windows.
- Inspected the Downloads preferences maximized at high zoom and Subtitles/Downloads in a newly opened dialog at normal zoom. The previous chat had already inspected General, Media, Accessibility, Advanced, Database, and the compact high-zoom Subtitles/Downloads layouts.
- Compared the System theme, which resolved to light on this machine, with Dark. Tested subtitle rendering dependencies, sidebar show/hide, Audio Filters and Color Adjustments expansion, sidebar scrolling, and Explorer visibility.
- Window captures were 1280 pixels wide. Results apply to this desktop and these settings; other display scales and monitor configurations were not tested.
- No media was loaded. Playback-dependent controls being disabled is expected; playback processing and media rendering were not tested.

## Confirmed findings

### 1. High-zoom Preferences lacks enough space for dense tabs

The previous inspection found unreadable, compressed rows in the compact Subtitles and Downloads tabs at zoom 10. In this continuation, maximizing Downloads made its field labels and values readable, while section titles remained clipped. Newly opened Subtitles and Downloads dialogs at zoom 0 were readable and their action buttons accessible.

Reproduce: use View → Zoom In to reach level 10, open Preferences, and select Downloads or Subtitles. Compare the initial dialog with a maximized dialog and with a newly opened dialog at level 0.

The tabs are added directly to `QTabWidget` in `src/gui/prefs_panels/__init__.py`; there is no scroll area around each preferences page. Provide scrollable page content so increasing the font does not force controls to compress into the available height.

### 2. Group titles are clipped at maximum zoom

Downloads headings such as Transfers, Notifications, Locations, and Network were partly obscured even with Preferences maximized. Explorer's Library and Path & Search headings showed the same problem, including after switching themes to refresh the widget styles.

Reproduce: at level 10, open Downloads preferences or show Explorer and inspect the top edge of each group.

Review the themed `QGroupBox` title margin and content padding against the actual font height. Increasing window width alone did not correct this.

### 3. Live zoom does not consistently refresh existing widgets

Ten Zoom Out actions changed the persisted level from 10 to 0. Existing toolbar labels, player text, and much of Explorer retained the large font. A newly opened Preferences dialog immediately used the smaller font. Changing the theme refreshed the existing widgets and made their fonts consistent with level 0. The reverse transition showed the same difference between existing widgets and a newly opened dialog.

Reproduce: start at level 10, reduce to level 0 using View → Zoom Out, then open Preferences. Compare the dialog text with the existing toolbar/player. Change the theme and compare again.

`src/app_init.py:98` currently changes the application font. Theme application in `src/utilities/theme_manager.py` additionally reapplies styles and repolishes existing widgets. The zoom path should also update existing styled widgets and their layout geometry without requiring a theme change.

### 4. Subtitle color values can disappear into their swatches

At normal zoom in the light theme, dark swatches had very low-contrast dark hexadecimal text. In the dark theme, the white text-color swatch had very low-contrast light hexadecimal text. The buttons remained present and accessible, but their displayed values were hard to read.

Reproduce: open Preferences → Subtitles with rendering enabled; compare the color buttons in light and dark themes.

`src/gui_controls/color_button.py:39` styles the button background without selecting a contrasting text color. Choose foreground contrast from the displayed swatch, including alpha compositing, or show the value alongside a separate swatch.

### 5. Maximum zoom can push lower player controls out of view

The player Minimize label was vertically clipped and the bottom status text was partly hidden at level 10. With Explorer docked above Player, the lower playback controls were pushed below the captured visible window. This remained visible after theme repolishing at level 10; the refreshed level-0 layout had a readable status bar and player controls.

Reproduce: at level 10, compare Player alone with Explorer shown above it, using both restored and maximized main-window states.

Review the combined toolbar, dock, player-control, and status-bar height requirements. The current main-window screen-fit handling in `src/gui/managers/dock_manager.py` does not prevent this configuration from exceeding the visible vertical budget.

## Working behavior and limits

- Turning off “Draw subtitles on the video” disabled the font, styling, color, and position controls as expected. The temporary edit was discarded.
- A newly opened normal-zoom Subtitles page displayed its full set of rendering controls; Downloads displayed transfers, locations, and network controls.
- The sidebar supports one expanded section at a time. Switching from Audio Filters to Color Adjustments replaced the expanded content; scrolling reached the lower controls and Audio Sync header.
- Some sidebar headings briefly clipped or changed size during transitions while the interface had mixed old/new zoom fonts. This was not established as a separate persistent defect after a complete style refresh.
- Theme changes applied live. Reapplying a theme also refreshed stale fonts, but did not remove the high-zoom group-title clipping or lower-player sizing problems.
- The previous chat confirmed that speech and MPV logging toggles reveal their dependent preference controls. Those observations were recovered from its history, rather than repeated here.

## End state

- PlayForm remains open in its restored main window, with Explorer visible and the player sidebar collapsed.
- Original System theme and zoom level 10 were restored. All persisted runtime preference values match the settings backup from before the previous review.
- Dialog preferences match that backup except the audio-device index, which the normal save path normalized from 1 to 2 while preserving the same saved device name. No alternate audio device was selected during the review.
- No source fix, automated test, download, catalog operation, or restart was performed. Suggested fixes above remain implementation work.

## Implementation update

The fixes were applied after the user requested implementation and a commit:

- Preferences pages scroll at their natural minimum size, with long form rows wrapping when needed. The dialog opens at a bounded size on the current screen.
- Group title margins follow the application font height, including locally styled radio groups.
- Live zoom reapplies the active theme styles and refreshes layout geometry, preserving the selected theme.
- Color buttons choose contrasting text using the swatch composited over the theme background. Changing themes recalculates contrast without changing the saved color or alpha.
- Labeled player buttons use their font-dependent height. Toggle animation no longer grows their minimum size on every activation.
- Flow layouts measure children before their parent is shown and calculate minimum height at the available width. Playback rows refresh after font, width, and visibility changes.
- Video/timeline and playback controls have separate scroll areas. Controls receive space before the video and remain reachable by scrolling on very short docks. The playback pane cannot collapse to zero width.
- Screen fitting coalesces overlapping requests, reserves the full status text height, and detects dock overlap with the status bar.

Validation passed:

- `vnv/Scripts/python.exe scripts/gui_layout_smoke_test.py`: seven checks covering live zoom at levels -4/0/10, title geometry, compact Preferences scrolling, color contrast/alpha, flow visibility, toggle cycles, and constrained player/Explorer layouts at 1280×720 and 900×640. Test settings and databases use a temporary directory; the media backend is mocked for the layout fixture.
- Existing `scripts/theme_smoke_test.py`.
- Python compilation of changed modules and `git diff --check`.

The running app was left open. Restart PlayForm to load the changed source before the user's visual verification. Native media playback and fullscreen rendering remain part of that manual check.

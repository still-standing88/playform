# Quick Start Guide - RSS/Atom Feed Reader

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or later
- PySide6, feedparser, and bleach (installed via requirements.txt)

### Installation

```powershell
# Navigate to project directory
cd c:\Users\earsv\OneDrive\Documents\PlayForm\tst\podcasts

# Ensure packages are installed
pip install -r ../../requirements.txt
```

### Running the Application

```powershell
python demo.py
```

## 📖 Basic Usage

### Adding Feeds

1. **Right-click** in the Feed List (left panel)
2. Select **"Add Feed"**
3. Enter the RSS/Atom feed URL
4. Click **OK**

**Popular Podcast Feeds to Try:**

- NPR Politics: `https://feeds.npr.org/510289/podcast.xml`
- BBC World Service: `https://podcasts.files.bbci.co.uk/p02nq0gn.rss`
- The Daily (NY Times): `https://feeds.simplecast.com/54nAGcIl`

### Viewing Entries

1. Click on a feed in the Feed List
2. Entries appear in the tree (middle panel)
3. Click an entry to see Summary/Description (bottom panel)

### Copying Links

1. **Right-click** on an entry
2. Select **"Copy"** → Choose:
   - **"Title"** - Copy entry title
   - **"Page Link"** - Copy episode web page URL
   - **"Direct Media Link"** - Copy direct MP3/media file URL

### Viewing Full Entry Data

1. **Right-click** on an entry
2. Select **"View Full Entry Dump"**
3. Click **"Copy to Clipboard"** to copy all data
4. Click **"Close"** when done

### Sorting Entries

1. **Right-click** on any entry
2. Select **"Sort By"** → Choose:
   - **"Title (Ascending A-Z)"**
   - **"Title (Descending Z-A)"**
   - **"Date (Newest First)"**
   - **"Date (Oldest First)"**

### Searching

1. Type your search query in the search box (top)
2. Press **Enter** or click **"Search"**
3. Results are filtered in the entry tree
4. Click **"Clear"** to show all entries again

## 🎧 Podcast Workflow

### Listen to an Episode

1. Add your podcast feed
2. Click on the feed to see episodes
3. Right-click on an episode
4. Select **"Copy"** → **"Direct Media Link"**
5. Paste the URL into your media player (VLC, Windows Media Player, etc.)

### Download for Offline

1. Copy the direct media link (as above)
2. Paste into your browser or download manager
3. File will download (usually MP3)

### Share an Episode

1. Right-click on episode
2. Select **"Copy"** → **"Page Link"**
3. Paste link in email, chat, etc.

## 🔧 Advanced Features

### Managing Multiple Feeds

- **Refresh a Feed:** Right-click feed → "Refresh Feed"
- **Refresh All:** Right-click anywhere → "Refresh All Feeds"
- **Update URL:** Right-click feed → "Update Feed URL"
- **Remove Feed:** Right-click feed → "Remove Feed"
- **Clear All:** Right-click anywhere → "Clear All Feeds"

### Keyboard Navigation

- **Arrow Keys:** Navigate entries
- **Page Up/Down:** Skip through entries
- **Home/End:** Jump to first/last entry
- **Tab:** Move between UI sections

## 💡 Tips & Tricks

### Finding Direct Media Links

Not all feeds provide direct media links. Podcasts typically do, but blog RSS feeds may not. If "Direct Media Link" returns nothing, use "Page Link" instead.

### HTML Content

The Summary/Description area displays formatted HTML. Click links directly to open them in your browser.

### Feed Validation

The app validates feeds before adding them. If a feed fails validation:

- Check the URL for typos
- Ensure the feed is actually RSS/Atom (not HTML)
- Try accessing the URL in your browser

### Performance

- Feeds are cached locally in the `cache/` directory
- Use "Refresh" to get latest episodes
- Cache survives app restarts

## 🐛 Troubleshooting

### Feed Won't Add

- **Check URL:** Make sure it's a feed URL (ends in .xml or .rss usually)
- **Test in Browser:** Open URL to verify it's accessible
- **Check Internet:** Ensure you have connectivity

### No Media Links

- **Feed Type:** Not all feeds include enclosures
- **Use Page Link:** Fall back to the web page
- **Check Feed Source:** Some feeds are text-only

### Display Issues

- **Refresh Feed:** Right-click feed → "Refresh Feed"
- **Clear Cache:** Delete `cache/` folder and re-add feeds
- **Restart App:** Close and reopen demo.py

### HTML Not Showing

- **Check bleach:** Ensure bleach is installed (`pip install bleach`)
- **Feed Format:** Some feeds use plain text, not HTML

## 📋 Menu Reference

### Feed List Context Menu

- Add Feed
- Refresh Feed (on selected feed)
- Update Feed URL (on selected feed)
- Remove Feed (on selected feed)
- Refresh All Feeds
- Clear All Feeds

### Entry Tree Context Menu

**Sort By:**

- Title (Ascending A-Z)
- Title (Descending Z-A)
- Date (Newest First)
- Date (Oldest First)

**Copy:**

- Title
- Page Link
- Direct Media Link

**Actions:**

- View Full Entry Dump
- Open Link in Browser

## 🎨 UI Layout

```
┌─────────────────────────────────────────────────────┐
│ Search: [________________] [Search] [Clear]         │
├─────────────┬───────────────────────────────────────┤
│             │                                       │
│ Feed List   │  Entry Tree                          │
│             │  ┌─────────────────────────────────┐ │
│ • Feed 1    │  │ Title    | Published | Link    │ │
│ • Feed 2    │  ├─────────────────────────────────┤ │
│ • Feed 3    │  │ Entry 1  | 2025-01  | http:// │ │
│             │  │ Entry 2  | 2025-01  | http:// │ │
│             │  └─────────────────────────────────┘ │
│             │                                       │
│             │  Summary/Description                 │
│             │  ┌─────────────────────────────────┐ │
│             │  │ HTML formatted content...        │ │
│             │  │                                  │ │
│             │  └─────────────────────────────────┘ │
└─────────────┴───────────────────────────────────────┘
```

## 🔗 Useful Resources

### Sample Feeds for Testing

- **News:** `http://feeds.bbci.co.uk/news/rss.xml`
- **Tech:** `https://feeds.arstechnica.com/arstechnica/index`
- **Podcasts:** `https://feeds.megaphone.fm/marketplace`

### Feed Directories

- **Apple Podcasts:** podcasts.apple.com
- **Podcast Index:** podcastindex.org
- **Feedly:** feedly.com

### Documentation

- See `REDESIGN_SUMMARY.md` for full change list
- See `MEDIA_LINK_GUIDE.md` for media link details
- See `IMPLEMENTATION_COMPLETE.md` for technical summary

## 🎯 Common Tasks

### Subscribe to a Podcast

1. Find RSS feed URL (usually on podcast website)
2. Right-click Feed List → "Add Feed"
3. Paste URL → OK

### Listen to Latest Episode

1. Click podcast feed
2. Episodes sorted newest first by default
3. Right-click top entry → Copy → Direct Media Link
4. Open in media player

### Save Episode Info

1. Right-click episode
2. "View Full Entry Dump"
3. "Copy to Clipboard"
4. Paste into notes/document

### Export Feed List

Currently manual - feature could be added:

- Feed URLs stored in `cache/feeds.json`
- Can be backed up/shared

## 🆘 Getting Help

If you encounter issues:

1. Check error messages in console
2. Verify feed URL in browser
3. Try with a different feed
4. Clear cache and retry
5. Check Python/package versions

## 🎊 Enjoy!

You now have a powerful RSS/Atom feed reader with:

- ✅ Clean interface
- ✅ Direct media link access
- ✅ HTML content display
- ✅ Clipboard integration
- ✅ Flexible sorting
- ✅ Search functionality

Happy podcasting! 🎧

# RSS/Atom Feed Reader Redesign Summary

## Overview

This document summarizes the comprehensive redesign of the RSS/Atom feed reader application to improve usability, security, and functionality.

## Key Changes

### 1. Tree View Columns Update

**Before:** Title, Author, Published, Link (4 columns)
**After:** Title, Published, Link (3 columns)

- Removed the Author column as it was not consistently available across feeds
- Updated `COMMON_FIELDS` from `['title', 'author', 'published', 'link']` to `['title', 'published', 'link']`
- Updated tree widget from 4 columns to 3 columns
- Adjusted column resize modes accordingly

### 2. Enhanced Content Display

**Changed from QTextEdit to QTextBrowser**

- Now displays rich HTML content instead of plain text
- Implemented HTML sanitization using the `bleach` library to prevent XSS attacks
- Allowed safe HTML tags: p, br, strong, em, u, a, ul, ol, li, h1-h6, blockquote, code, pre, div, span, img, table, thead, tbody, tr, th, td, hr
- Links are now clickable and open externally
- Better formatting with CSS styling for improved readability

### 3. Direct Media Link Extraction

**New Feature: `get_direct_media_url()` method in FeedManager**

This method reliably extracts direct media links (MP3, etc.) from RSS/Atom feeds by checking:

1. **RSS 2.0 Enclosures** (`entry.enclosures[0].href`)
   - Most common for podcast feeds
2. **Media RSS Extension** (`entry.media_content[0].url`)
   - Used when feeds incorporate Media RSS namespace
3. **Atom Links** (`entry.links` where `rel='enclosure'`)
   - Standard Atom way of linking media

```python
def get_direct_media_url(self, entry):
    # Check for standard RSS <enclosure>
    if hasattr(entry, 'enclosures') and entry.enclosures:
        return entry.enclosures[0].get('href')

    # Check for Media RSS <media:content>
    if hasattr(entry, 'media_content') and entry.media_content:
        return entry.media_content[0].get('url')

    # Check Atom <link rel="enclosure">
    if hasattr(entry, 'links') and entry.links:
        for link in entry.links:
            if link.get('rel') == 'enclosure':
                return link.get('href')

    return None
```

### 4. Improved Context Menu

#### Sort Options (More Descriptive)

- **Title (Ascending A-Z)** - Sort titles alphabetically ascending
- **Title (Descending Z-A)** - Sort titles alphabetically descending
- **Date (Newest First)** - Sort by date, newest entries first
- **Date (Oldest First)** - Sort by date, oldest entries first

#### Copy Options

- **Title** - Copies entry title to clipboard
- **Page Link** - Copies the HTML page link to clipboard
- **Direct Media Link** (NEW) - Copies the direct media file URL (MP3, etc.)

#### Other Options

- **View Full Entry Dump** - Shows complete entry data in a dialog
- **Open Link in Browser** - Opens the entry's web page

### 5. Full Entry Dump Dialog Enhancement

**New Feature: Copy to Clipboard**

- Added "Copy to Clipboard" button in the EntryDetailDialog
- Copies all entry data as formatted text to clipboard
- Includes all fields with proper formatting
- Shows confirmation message when copied

**Implementation:**

```python
def copy_to_clipboard(self):
    """Copy the full entry data to clipboard as text"""
    # Formats all entry attributes as readable text
    # Includes field names, values, and proper indentation
    clipboard = QApplication.clipboard()
    clipboard.setText(formatted_text)
    QMessageBox.information(self, "Copied", "Entry data copied to clipboard")
```

### 6. HTML Sanitization with Bleach

**Dependencies Added:**

- Added `bleach==6.2.0` to requirements.txt
- Installed in the Python environment

**Implementation:**

```python
import bleach

# Define allowed HTML elements and attributes
allowed_tags = [
    'p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code',
    'pre', 'div', 'span', 'img', 'table', 'thead', 'tbody',
    'tr', 'th', 'td', 'hr'
]
allowed_attrs = {
    '*': ['class', 'id', 'style'],
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'title', 'width', 'height']
}

sanitized = bleach.clean(
    content_html,
    tags=allowed_tags,
    attributes=allowed_attrs,
    strip=True
)
```

### 7. Feed Format Support

**Both RSS and Atom are fully supported:**

#### RSS Support

- RSS 0.90, 0.91, 0.92, 0.93, 0.94
- RSS 1.0, RSS 2.0
- iTunes podcast extensions
- Media RSS extensions

#### Atom Support

- Atom 0.3, Atom 1.0
- Content normalization (can access Atom feeds using RSS terminology)

### 8. Field Handling Improvements

**Summary/Description/Content Display:**

- Handles `summary`, `description`, and `content` fields
- Supports nested structures (lists, dicts with 'value' key)
- Properly extracts content from feedparser's structured data
- Displays with proper HTML formatting and sanitization

**Date Formatting:**

- Tries `published` first, then falls back to `updated`
- Converts parsed time tuples to readable format
- Displays as "YYYY-MM-DD HH:MM"
- Shows "N/A" if no date available

## File Changes

### Modified Files

1. **requirements.txt**

   - Added: `bleach==6.2.0`

2. **feed_manager.py**

   - Added: `get_direct_media_url()` method

3. **feed_widget.py**
   - Updated imports: Added `QApplication`, `bleach`, `html`
   - Changed `COMMON_FIELDS` constant
   - Updated `EntryDetailDialog`:
     - Added "Copy to Clipboard" button
     - Added `copy_to_clipboard()` method
     - Added `format_value_as_text()` helper method
   - Updated `FeedWidget`:
     - Changed tree widget from 4 to 3 columns
     - Changed `detail_text` from QTextEdit to QTextBrowser
     - Updated `show_entry_context_menu()` with new options
     - Updated `update_entry_tree()` to populate 3 columns
     - Updated `display_entry_detail()` to use HTML with bleach sanitization
     - Added `copy_direct_media_link()` method

## Testing

To test the application:

```bash
cd c:\Users\earsv\OneDrive\Documents\PlayForm\tst\podcasts
python demo.py
```

### Test Scenarios

1. **Add RSS Feed**: Right-click in Feed List → Add Feed

   - Test with podcast RSS feed (e.g., NPR, BBC)
   - Verify enclosure links are detected

2. **Add Atom Feed**: Test with Atom feed

   - Verify content displays correctly
   - Check link extraction

3. **View Entry Details**:

   - Select an entry
   - Verify Summary/Description shows in bottom panel
   - Check HTML is rendered and sanitized
   - Verify links are clickable

4. **Copy Functions**:

   - Right-click entry → Copy → Page Link
   - Right-click entry → Copy → Direct Media Link
   - Verify correct URLs are copied

5. **Full Entry Dump**:

   - Right-click entry → View Full Entry Dump
   - Click "Copy to Clipboard"
   - Paste in text editor to verify formatting

6. **Sorting**:
   - Right-click entry → Sort By → Test all options
   - Verify correct sort order

## Security Improvements

### XSS Prevention

- All HTML content is sanitized using bleach
- Only safe HTML tags are allowed
- Dangerous attributes are stripped
- JavaScript and inline event handlers are removed

### Safe Link Handling

- External links open in browser (not embedded)
- URL validation before opening
- No automatic execution of content

## Benefits of Redesign

1. **Cleaner UI**: Removed rarely-used Author column
2. **Better Content Display**: Rich HTML rendering with proper formatting
3. **Enhanced Security**: Sanitized HTML prevents XSS attacks
4. **Improved Functionality**: Direct media link extraction for podcasts
5. **Better UX**: More descriptive menu options and clipboard features
6. **Feed Compatibility**: Full support for both RSS and Atom feeds

## Future Enhancements (Potential)

1. **Download Manager**: Use direct media links to download episodes
2. **Playlist Integration**: Add entries to media player playlist
3. **Search Filtering**: Filter by podcast author, date range, etc.
4. **Custom Themes**: User-selectable color schemes
5. **Episode Tracking**: Mark episodes as played/unplayed
6. **Favorites**: Star/bookmark favorite episodes
7. **Export Options**: Export to OPML, JSON, or other formats

## Dependencies

### Required Packages

- PySide6 >= 6.9.1
- feedparser >= 6.0.11
- bleach >= 6.2.0

### Python Version

- Python 3.8 or later

## Conclusion

This redesign significantly improves the RSS/Atom feed reader with better usability, enhanced security through HTML sanitization, reliable media link extraction, and comprehensive clipboard functionality. The application now handles both RSS and Atom feeds seamlessly while providing a cleaner, more intuitive interface.

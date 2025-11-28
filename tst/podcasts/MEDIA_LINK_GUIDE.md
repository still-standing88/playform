# Direct Media Link Extraction - Quick Reference

## Overview

The direct media link extraction feature finds the actual media file URL (MP3, M4A, OGG, etc.) from podcast RSS/Atom feeds, instead of just the episode's web page link.

## How It Works

### The Problem

RSS/Atom feeds typically have two types of links:

1. **Page Link** (`entry.link`) - Points to the episode's web page (HTML)
2. **Media Link** - Points to the actual audio/video file (MP3, M4A, etc.)

The standard `entry.link` is not suitable for media players - they need the direct file URL.

### The Solution

The `get_direct_media_url()` method checks three standard locations in priority order:

#### 1. RSS Enclosures (Most Common for Podcasts)

```xml
<enclosure url="https://example.com/episode123.mp3"
           type="audio/mpeg"
           length="45678901" />
```

Accessed via: `entry.enclosures[0]['href']`

#### 2. Media RSS Extension

```xml
<media:content url="https://example.com/episode123.mp3"
               type="audio/mpeg"
               duration="3600" />
```

Accessed via: `entry.media_content[0]['url']`

#### 3. Atom Enclosure Links

```xml
<link rel="enclosure"
      href="https://example.com/episode123.mp3"
      type="audio/mpeg"
      length="45678901" />
```

Accessed via: `entry.links` where `link.rel == 'enclosure'`

## Usage in Code

### Basic Usage

```python
from feed_manager import FeedManager

feed_mgr = FeedManager()
data = feed_mgr.refresh_feed('https://example.com/podcast.rss')

for entry in data.entries:
    page_link = entry.link  # HTML page
    media_link = feed_mgr.get_direct_media_url(entry)  # Direct file

    print(f"Title: {entry.title}")
    print(f"Page: {page_link}")
    print(f"Media: {media_link}")
```

### In Feed Widget

The feature is integrated into the UI:

1. **Right-click on any entry**
2. **Select "Copy" → "Direct Media Link"**
3. **The media URL is copied to clipboard**

### Handling Missing Links

```python
media_url = feed_mgr.get_direct_media_url(entry)
if media_url:
    print(f"Download from: {media_url}")
else:
    print("No media link available for this entry")
```

## Common Feed Formats

### NPR Podcasts

- Use RSS 2.0 with `<enclosure>` tags
- Reliable media link extraction
- Usually MP3 format

### BBC Podcasts

- Use Atom feeds with `rel="enclosure"`
- May have multiple quality options
- Usually M4A or MP3 format

### YouTube Podcasts

- May use Media RSS extensions
- Often have video enclosures
- MP4 or WEBM format

### Spotify Podcasts

- RSS 2.0 with custom extensions
- Standard enclosure tags
- MP3 format

## Edge Cases

### Multiple Enclosures

Some entries offer multiple formats:

```python
for enclosure in entry.enclosures:
    url = enclosure.get('href')
    mime_type = enclosure.get('type')
    print(f"{mime_type}: {url}")
```

### Relative URLs

Some feeds use relative paths:

```python
media_url = feed_mgr.get_direct_media_url(entry)
if media_url and not media_url.startswith('http'):
    # Construct full URL using feed base
    base_url = "https://example.com"
    full_url = base_url + media_url
```

### Quality Selection

Choose best quality from multiple options:

```python
def get_best_enclosure(entry):
    if not entry.enclosures:
        return None

    # Prefer higher bitrate or larger file
    best = max(entry.enclosures,
               key=lambda e: int(e.get('length', 0)))
    return best.get('href')
```

## Integration Examples

### Download Episode

```python
import requests

media_url = feed_mgr.get_direct_media_url(entry)
if media_url:
    filename = f"{entry.title}.mp3"
    response = requests.get(media_url, stream=True)
    with open(filename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
```

### Add to Playlist

```python
from player import MediaPlayer

player = MediaPlayer()
for entry in entries:
    media_url = feed_mgr.get_direct_media_url(entry)
    if media_url:
        player.add_to_playlist(
            url=media_url,
            title=entry.title,
            artist=entry.get('author', 'Unknown')
        )
```

### Stream Audio

```python
import vlc

media_url = feed_mgr.get_direct_media_url(entry)
if media_url:
    player = vlc.MediaPlayer(media_url)
    player.play()
```

## Troubleshooting

### No Media Link Found

**Possible Causes:**

1. Feed doesn't include enclosures
2. Entry is text-only (no audio/video)
3. Non-standard feed format

**Solution:**

```python
# Fallback to page link
media_url = feed_mgr.get_direct_media_url(entry)
if not media_url:
    page_url = entry.link
    # Try to scrape media URL from page
    # or notify user to download manually
```

### Invalid/Broken URLs

**Check before using:**

```python
import requests

def validate_media_url(url):
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except:
        return False

media_url = feed_mgr.get_direct_media_url(entry)
if media_url and validate_media_url(media_url):
    # Safe to use
    pass
```

### Access Denied / 403 Errors

Some CDNs require specific headers:

```python
def download_with_headers(url):
    headers = {
        'User-Agent': 'FeedManager/1.0',
        'Referer': 'https://example.com/'
    }
    return requests.get(url, headers=headers)
```

## Testing

### Test with Sample Feeds

```python
# NPR Podcast (RSS 2.0)
npr_feed = "https://feeds.npr.org/510289/podcast.xml"

# BBC Podcast (Atom)
bbc_feed = "https://podcasts.files.bbci.co.uk/p02nq0gn.rss"

# Test extraction
for feed_url in [npr_feed, bbc_feed]:
    data = feed_mgr.refresh_feed(feed_url)
    entry = data.entries[0]

    page = entry.link
    media = feed_mgr.get_direct_media_url(entry)

    print(f"\nFeed: {feed_url}")
    print(f"Page: {page}")
    print(f"Media: {media}")
    print(f"Success: {media is not None}")
```

## Best Practices

1. **Always check for None:**

   ```python
   media_url = feed_mgr.get_direct_media_url(entry)
   if media_url:
       # Use it
   ```

2. **Cache media URLs:**

   - Avoid re-parsing feeds unnecessarily
   - Store URLs in database for offline access

3. **Validate MIME types:**

   ```python
   if enclosure.get('type', '').startswith('audio/'):
       # It's audio
   ```

4. **Handle redirects:**

   - Some URLs redirect to CDN
   - Use `requests` with `allow_redirects=True`

5. **Respect bandwidth:**
   - Don't download entire file to test
   - Use HEAD requests to check availability

## Conclusion

The direct media link extraction feature makes it easy to:

- Download podcast episodes
- Stream audio/video directly
- Build media player integrations
- Create offline podcast managers

The method handles the complexity of different feed formats and provides a simple, reliable way to access media files.

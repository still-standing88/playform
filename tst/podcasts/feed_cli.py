import sys
import os
import argparse
from datetime import datetime

# Ensure this script can import feed_manager from the same folder
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from feed_manager import FeedManager

def fmt_dt(val):
    try:
        if hasattr(val, "tm_year"):
            return datetime(*val[:6]).isoformat(sep=" ")
        return str(val)
    except Exception:
        return str(val)

def entry_preview(mgr: FeedManager, entry):
    p = mgr.get_entry_preview(entry)
    title = p.get("title") or "<no title>"
    published = p.get("published") or "?"
    link = p.get("link") or "#"
    return f"- {published} | {title}\n  {link}"

def list_feeds(mgr: FeedManager):
    feeds = mgr.get_feed_list()
    if not feeds:
        print("No feeds found. Use the GUI to add a feed, then re-run.")
        return []
    print(f"Found {len(feeds)} feed(s):")
    for i, url in enumerate(feeds):
        print(f"[{i}] {url}")
    return feeds

def show_feed(mgr: FeedManager, url: str, max_items: int = 10, refresh: bool = False):
    if refresh:
        print(f"Refreshing: {url}")
        try:
            data = mgr.refresh_feed(url, force=True)
        except Exception as e:
            print(f"  ERROR refreshing: {e}")
            data = None
    else:
        data = mgr.get_feed_data(url)
        if not data:
            print("No cache found; fetching once...")
            data = mgr.refresh_feed(url, force=True)

    if not data:
        print("  No data.")
        return

    status = data.get('status') if hasattr(data, 'get') else getattr(data, 'status', None)
    href = data.get('href') if hasattr(data, 'get') else getattr(data, 'href', None)
    etag = data.get('etag') if hasattr(data, 'get') else getattr(data, 'etag', None)
    modified = data.get('modified') if hasattr(data, 'get') else getattr(data, 'modified', None)
    print(f"  HTTP status: {status} | href: {href}")
    print(f"  ETag: {etag} | Modified: {modified}")

    bozo = data.get('bozo', 0)
    if bozo:
        print(f"  BOZO feed (parse error). Exception: {data.get('bozo_exception')}")

    feed_title = getattr(getattr(data, 'feed', {}), 'title', None)
    if not feed_title and hasattr(data, 'feed') and isinstance(data.feed, dict):
        feed_title = data.feed.get('title')
    print(f"  Title: {feed_title or url}")

    entries = getattr(data, 'entries', []) or []
    print(f"  Entries: {len(entries)}")
    for e in entries[:max_items]:
        try:
            print(entry_preview(mgr, e))
        except Exception as ex:
            print(f"  - <error formatting entry>: {ex}")


def main():
    parser = argparse.ArgumentParser(description="FeedManager CLI inspector")
    parser.add_argument("--refresh", action="store_true", help="Refresh feeds before showing")
    parser.add_argument("--index", type=int, help="Select feed by index from list")
    parser.add_argument("--url", type=str, help="Select a specific feed URL")
    parser.add_argument("--max", type=int, default=10, help="Max entries to display per feed")
    default_cache = os.path.join(SCRIPT_DIR, "cache")
    parser.add_argument("--cache", type=str, default=default_cache, help="Cache directory (same as GUI)")
    args = parser.parse_args()

    mgr = FeedManager(cache_dir=args.cache)
    feeds = list_feeds(mgr)

    if not feeds:
        return 0

    targets = []
    if args.url:
        targets = [args.url]
    elif args.index is not None:
        if 0 <= args.index < len(feeds):
            targets = [feeds[args.index]]
        else:
            print(f"Index out of range: {args.index}")
            return 2
    else:
        targets = feeds

    for url in targets:
        show_feed(mgr, url, max_items=args.max, refresh=args.refresh)
        print()

    return 0

if __name__ == "__main__":
    raise SystemExit(main())

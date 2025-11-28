import os
import json
import pickle
import hashlib
import shutil
import feedparser
from datetime import datetime
from time import mktime

class FeedManager:
    def __init__(self, cache_dir='./cache', user_agent='FeedManager/1.0'):
        self.cache_dir = cache_dir
        self.user_agent = user_agent
        self.feeds_meta = {}
        self.feed_data_cache = {}
        self._init_cache()

    def _init_cache(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self._load_meta()

    def _get_hash(self, url):
        return hashlib.md5(url.encode('utf-8')).hexdigest()

    def _get_cache_path(self, url):
        return os.path.join(self.cache_dir, f"{self._get_hash(url)}.pickle")

    def _meta_path(self):
        return os.path.join(self.cache_dir, 'feeds.json')

    def _save_meta(self):
        with open(self._meta_path(), 'w') as f:
            json.dump(self.feeds_meta, f)

    def _load_meta(self):
        path = self._meta_path()
        if os.path.exists(path):
            with open(path, 'r') as f:
                self.feeds_meta = json.load(f)
        else:
            self.feeds_meta = {}

    def _save_feed_data(self, url, data):
        with open(self._get_cache_path(url), 'wb') as f:
            pickle.dump(data, f)

    def _load_feed_data(self, url):
        if url in self.feed_data_cache:
            return self.feed_data_cache[url]
        
        path = self._get_cache_path(url)
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    data = pickle.load(f)
                    self.feed_data_cache[url] = data
                    return data
            except Exception:
                return None
        return None

    def add_feed(self, url):
        if url not in self.feeds_meta:
            self.feeds_meta[url] = {'etag': None, 'modified': None}
            self._save_meta()
            return True
        return False

    def remove_feed(self, url):
        if url in self.feeds_meta:
            del self.feeds_meta[url]
            self._save_meta()
            if url in self.feed_data_cache:
                del self.feed_data_cache[url]
            cache_path = self._get_cache_path(url)
            if os.path.exists(cache_path):
                os.remove(cache_path)
            return True
        return False

    def delete_all_feeds(self):
        self.feeds_meta = {}
        self.feed_data_cache = {}
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        self._init_cache()

    def update_feed_url(self, old_url, new_url):
        if old_url in self.feeds_meta:
            meta = self.feeds_meta.pop(old_url)
            self.feeds_meta[new_url] = {'etag': None, 'modified': None}
            
            if old_url in self.feed_data_cache:
                del self.feed_data_cache[old_url]
            
            old_cache = self._get_cache_path(old_url)
            if os.path.exists(old_cache):
                os.remove(old_cache)
            
            self._save_meta()
            return True
        return False

    def get_feed_list(self):
        return list(self.feeds_meta.keys())

    def refresh_feed(self, url, force=False):
        if url not in self.feeds_meta and not force:
             return None

        meta = self.feeds_meta.get(url, {'etag': None, 'modified': None})
        etag = None if force else meta.get('etag')
        modified = None if force else meta.get('modified')
        if isinstance(modified, (list, tuple)):
            try:
                mod_tuple = tuple(modified)
                modified = datetime.fromtimestamp(mktime(mod_tuple)).strftime('%a, %d %b %Y %H:%M:%S GMT')
            except Exception:
                modified = None

        def do_parse(target_url, use_conditionals=True):
            kwargs = {
                'etag': etag if use_conditionals else None,
                'modified': modified if use_conditionals else None,
                'agent': self.user_agent,
            }
            return feedparser.parse(target_url, **kwargs)

        parsed = do_parse(url, use_conditionals=not force)

        # Handle HTTP redirects explicitly by re-fetching the new URL without conditionals
        status = getattr(parsed, 'status', None)
        if status in (301, 302, 307, 308):
            new_url = getattr(parsed, 'href', None) or url
            if new_url and new_url != url:
                if url in self.feeds_meta:
                    self.remove_feed(url)
                    self.add_feed(new_url)
                url = new_url
                parsed = do_parse(url, use_conditionals=False)

        # If server says Not Modified but we don't have cache yet, force a full fetch
        if status == 304:
            cached = self._load_feed_data(url)
            if cached is not None:
                return cached
            parsed = do_parse(url, use_conditionals=False)

        # Persist new conditional headers using correct types
        new_etag = getattr(parsed, 'etag', None)
        new_modified = getattr(parsed, 'modified', None)
        if not new_modified:
            new_modified_parsed = getattr(parsed, 'modified_parsed', None)
            if new_modified_parsed:
                try:
                    new_modified = datetime.fromtimestamp(mktime(tuple(new_modified_parsed))).strftime('%a, %d %b %Y %H:%M:%S GMT')
                except Exception:
                    new_modified = None

        self.feeds_meta[url] = {
            'etag': new_etag,
            'modified': new_modified,
        }
        self._save_meta()
        self._save_feed_data(url, parsed)
        self.feed_data_cache[url] = parsed
        return parsed

    def refresh_all(self):
        results = {}
        for url in list(self.feeds_meta.keys()):
            results[url] = self.refresh_feed(url)
        return results

    def get_feed_data(self, url):
        return self._load_feed_data(url)

    def get_all_entries(self):
        all_entries = []
        for url in self.feeds_meta:
            data = self.get_feed_data(url)
            if data and 'entries' in data:
                for entry in data.entries:
                    entry['_source_feed_url'] = url
                    all_entries.append(entry)
        return all_entries

    def filter_entries(self, entries=None, **kwargs):
        if entries is None:
            entries = self.get_all_entries()
        
        filtered = []
        for entry in entries:
            match = True
            for key, value in kwargs.items():
                if key not in entry:
                     match = False
                     break
                
                entry_val = entry[key]
                if isinstance(value, str) and isinstance(entry_val, str):
                     if value.lower() not in entry_val.lower():
                          match = False
                          break
                elif entry_val != value:
                     match = False
                     break
            if match:
                filtered.append(entry)
        return filtered

    def search_entries(self, query, fields=['title', 'summary', 'description'], entries=None):
        if entries is None:
            entries = self.get_all_entries()
        
        query = query.lower()
        results = []
        for entry in entries:
            for field in fields:
                if hasattr(entry, field):
                    val = getattr(entry, field)
                    if isinstance(val, str) and query in val.lower():
                        results.append(entry)
                        break
                    elif isinstance(val, dict) and 'value' in val:
                         if query in val['value'].lower():
                             results.append(entry)
                             break
        return results

    def sort_entries(self, entries, key='published_parsed', reverse=True):
        def get_sort_key(entry):
            val = getattr(entry, key, None)
            if val is None:
                 if key == 'published_parsed':
                      return getattr(entry, 'updated_parsed', (0,0,0,0,0,0,0,0,0))
                 return ""
            return val
            
        return sorted(entries, key=get_sort_key, reverse=reverse)

    def get_entry_preview(self, entry):
        published = getattr(entry, 'published', getattr(entry, 'updated', 'N/A'))
        return {
            'title': getattr(entry, 'title', 'No Title'),
            'link': getattr(entry, 'link', '#'),
            'published': published,
            'summary': getattr(entry, 'summary', getattr(entry, 'description', '')),
            'source_url': entry.get('_source_feed_url')
        }

    def get_full_feed_object(self, url):
        return self.get_feed_data(url)

    def query_feed_path(self, url, path):
        data = self.get_feed_data(url)
        if not data:
            return None
        
        current = data
        for part in path.split('.'):
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, list) and part.isdigit():
                 idx = int(part)
                 if 0 <= idx < len(current):
                     current = current[idx]
                 else:
                     return None
            else:
                return None
        return current

    def get_bozo_details(self, url):
        data = self.get_feed_data(url)
        if data and data.get('bozo', 0) == 1:
            return data.get('bozo_exception')
        return None

    def get_direct_media_url(self, entry):
        """
        Tries to find the direct media URL from a feedparser entry,
        checking enclosures, media_content, and links.
        This is useful for getting the direct link to media files (MP3, etc.)
        instead of the HTML page link.
        """
        # 1. Check for standard RSS <enclosure> (most reliable for podcasts)
        if hasattr(entry, 'enclosures') and entry.enclosures:
            # Check 'href' of the first enclosure
            return entry.enclosures[0].get('href')
        
        # 2. Check for Media RSS <media:content>
        if hasattr(entry, 'media_content') and entry.media_content:
            # Check 'url' of the first media_content
            return entry.media_content[0].get('url')
        
        # 3. Check the Atom/general <link> tags
        if hasattr(entry, 'links') and entry.links:
            for link in entry.links:
                # Look for rel="enclosure" (Atom's equivalent of <enclosure>)
                if link.get('rel') == 'enclosure':
                    return link.get('href')
        
        # If all checks fail, return None
        return None
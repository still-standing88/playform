import os
import re

__all__ = ["PodcastDownloadManager"]


class PodcastDownloadManager:
    """Bridges podcast episodes into the app's shared Downloader
    (src/downloader/downloader.py) -- not a second download engine, just
    resolves episodes to direct media URLs and queues them, tagged so the
    Download Manager UI can group/filter them as a "podcast queue" (see
    downloader.DownloadItem.metadata).

    Holds no state of its own beyond its FeedManager/Downloader references
    -- the shared Downloader is the single source of truth for what's
    queued/downloading/paused, matching the rest of this app's
    "one shared engine, multiple thin callers" pattern
    (media_core.ffmpeg.conversion_job, media_core.m4b_tools, ...).
    """

    def __init__(self, feed_manager, downloader, destination_dir):
        self.feed_manager = feed_manager
        self.downloader = downloader
        self.destination_dir = destination_dir

    def _feed_destination(self, feed_url: str) -> str:
        """Each podcast gets its own subfolder under destination_dir, named
        after the feed title -- e.g. downloads/podcasts/My Show/ -- instead
        of dumping every feed's episodes into one flat folder."""
        data = self.feed_manager.get_feed_data(feed_url)
        title = None
        if data and hasattr(data, 'feed'):
            title = getattr(data.feed, 'title', None)
        safe_title = self._safe_component(title or feed_url)
        dest = os.path.join(self.destination_dir, safe_title)
        os.makedirs(dest, exist_ok=True)
        return dest

    def queue_episode(self, feed_url: str, entry):
        media_url = self.feed_manager.get_direct_media_url(entry)
        if not media_url:
            return None
        title = getattr(entry, 'title', None) or 'episode'
        filename = self._safe_filename(title, media_url)
        return self.downloader.add_download(
            media_url,
            destination=self._feed_destination(feed_url),
            filename=filename,
            metadata={
                "source_kind": "podcast",
                "podcast_feed_url": feed_url,
                "episode_title": title,
            },
        )

    def queue_all_unqueued(self, feed_url: str):
        """Queues every not-yet-queued episode in the feed. The queued items
        land in the same shared Downloader as any other download, so the
        Download Manager's existing pause/resume/cancel controls apply to
        them individually and to the queue as a whole -- no separate
        batch-download engine needed."""
        data = self.feed_manager.get_feed_data(feed_url)
        if not data or not hasattr(data, 'entries'):
            return []

        already_queued = self._queued_media_urls()
        queued = []
        for entry in data.entries:
            media_url = self.feed_manager.get_direct_media_url(entry)
            if not media_url or media_url in already_queued:
                continue
            item = self.queue_episode(feed_url, entry)
            if item:
                queued.append(item)
                already_queued.add(media_url)
        return queued

    def _queued_media_urls(self):
        urls = set()
        for bucket in self.downloader.get_all_downloads().values():
            for item in bucket:
                urls.add(item.url)
        return urls

    @staticmethod
    def _safe_component(name: str) -> str:
        safe = re.sub(r'[\\/*?:"<>|]', '_', name).strip()
        return safe.rstrip('. ') or 'podcast'

    @staticmethod
    def _safe_filename(title: str, url: str) -> str:
        ext = os.path.splitext(url.split('?')[0])[1] or '.mp3'
        safe = re.sub(r'[\\/*?:"<>|]', '_', title).strip() or 'episode'
        return f"{safe}{ext}"

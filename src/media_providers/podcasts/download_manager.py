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

    def queue_episode(self, feed_url: str, entry):
        media_url = self.feed_manager.get_direct_media_url(entry)
        if not media_url:
            return None
        title = getattr(entry, 'title', None) or 'episode'
        filename = self._safe_filename(title, media_url)
        return self.downloader.add_download(
            media_url,
            destination=self.destination_dir,
            filename=filename,
            metadata={
                "source_kind": "podcast",
                "podcast_feed_url": feed_url,
                "episode_title": title,
            },
        )

    def queue_next_unqueued(self, feed_url: str, count: int = 3):
        """Appends up to `count` not-yet-queued episodes from a feed to the
        shared downloader -- "a few episodes each time" per the user's
        request, rather than queuing an entire feed's back-catalog at once.
        Call this again later to append the next batch."""
        data = self.feed_manager.get_feed_data(feed_url)
        if not data or not hasattr(data, 'entries'):
            return []

        already_queued = self._queued_media_urls()
        queued = []
        for entry in data.entries:
            if len(queued) >= count:
                break
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
    def _safe_filename(title: str, url: str) -> str:
        ext = os.path.splitext(url.split('?')[0])[1] or '.mp3'
        safe = re.sub(r'[\\/*?:"<>|]', '_', title).strip() or 'episode'
        return f"{safe}{ext}"

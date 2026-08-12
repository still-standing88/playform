"""Podcast feed fetching/caching engine, framework-agnostic (no Qt imports)
same as media_core.m4b_tools/media_core.av_capture. The Qt-facing pieces
(feed list widget, background job thread) live under
media_providers.podcasts and drive this module the same way
tools/ffmpeg/batch_converter/job.py drives media_core.ffmpeg's
ConversionRunner.
"""

from media_core.podcasts.feed_manager import FeedManager
from media_core.podcasts.feed_refresh_runner import FeedRefreshRunner

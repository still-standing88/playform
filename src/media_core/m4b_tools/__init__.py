"""Audiobook (.m4b) tooling: bind, split, slide, cover, labels, and combine.

Ported from the archived `m4b-util` (engine/CLI structure) and `m4b-tools` (CSV-driven
combine, templated chapter-split naming, metadata CSV dump) reference projects under
`archive/`, rebuilt on `media_core.ffmpeg` instead of raw `subprocess`/`ffmpeg`/`ffprobe`
calls. Every operation is framework-agnostic - progress and log lines are reported through
plain callbacks, matching `media_core.ffmpeg.conversion_job.ConversionRunner` - so a Qt
wrapper under `tools/m4b_tools/` can drive any of these the same way
`tools/ffmpeg/batch_converter/job.py` drives batch conversion jobs.

Layering:
    segment, probe, ffmetadata, finders, naming, cover  - shared primitives
    audiobook.Audiobook                                 - the one engine that turns a
                                                           list of `Segment`s into a bound
                                                           .m4b (used by bind/slide/labels/combine)
    bind, slide, labels, split, combine, metadata_dump   - operations built on the above
"""

from media_core.m4b_tools.audiobook import Audiobook
from media_core.m4b_tools.bind import BindRunner
from media_core.m4b_tools.combine import CombineRunner, parse_combine_csv
from media_core.m4b_tools.metadata_dump import dump_metadata_rows, write_metadata_csv
from media_core.m4b_tools.runner import M4bToolsRunner
from media_core.m4b_tools.segment import Segment
from media_core.m4b_tools.split import SplitRunner, split_multiple_files

__all__ = [
    "Audiobook",
    "BindRunner",
    "CombineRunner",
    "M4bToolsRunner",
    "Segment",
    "SplitRunner",
    "dump_metadata_rows",
    "parse_combine_csv",
    "split_multiple_files",
    "write_metadata_csv",
]

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Segment:
    """A single span of audio, such as a chapter or a non-silence region.

    All `*_time` fields are seconds. `backing_file`/`file_start_time`/`file_end_time`
    describe where the segment lives in its *source* file, while `start_time`/`end_time`
    describe where it lands in the *output* timeline once bound together with other
    segments (they're equal for a segment that hasn't been combined with anything yet).
    """

    start_time: float
    end_time: float
    id: Optional[int] = None
    title: Optional[str] = None
    backing_file: Optional[str] = None
    file_start_time: Optional[float] = None
    file_end_time: Optional[float] = None

    def __setattr__(self, key, value):
        if "time" in key and value is not None:
            value = round(value, 3)
        super().__setattr__(key, value)

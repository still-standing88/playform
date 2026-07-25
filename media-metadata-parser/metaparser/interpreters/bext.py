"""bext (Broadcast Audio Extension) chunk interpreter — EBU Tech 3285 v2 (2011).

Fixed 602-byte positional struct followed by a variable-length CodingHistory
that runs to the end of the chunk. This is the one interpreter that's
hardcoded by necessity: it's a C struct, not key-value, so there's nothing to
walk generically. Byte offsets below are the spec's, not guessed.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass

from metaparser.interpreters._text import decode_lenient

logger = logging.getLogger(__name__)

FIXED_SIZE = 602

_FIELD_LAYOUT = {
    "description": (0, 256),
    "originator": (256, 32),
    "originator_reference": (288, 32),
    "origination_date": (320, 10),
    "origination_time": (330, 8),
}


class BextParseError(Exception):
    pass


@dataclass
class BextData:
    description: str
    originator: str
    originator_reference: str
    origination_date: str
    origination_time: str
    time_reference: int
    """Sample count since midnight, reassembled from the low/high uint32 pair."""
    version: int
    umid: bytes
    loudness_value: float | None
    """LUFS. None on version < 2, where the field isn't meaningful."""
    loudness_range: float | None
    max_true_peak_level: float | None
    max_momentary_loudness: float | None
    max_short_term_loudness: float | None
    coding_history: str


def _text_field(raw: bytes, offset: int, size: int) -> str:
    field = raw[offset : offset + size]
    return decode_lenient(field.split(b"\x00", 1)[0]).strip()


def parse(raw: bytes) -> BextData:
    """Parse a bext chunk payload. Raises BextParseError if the payload is too
    short to contain the fixed portion — anything shorter isn't a spec-valid
    bext chunk and callers should treat it as opportunistic/corrupt data.
    """
    if len(raw) < FIXED_SIZE:
        raise BextParseError(
            f"bext payload is {len(raw)} bytes, need at least {FIXED_SIZE} for the fixed portion"
        )

    fields = {name: _text_field(raw, off, size) for name, (off, size) in _FIELD_LAYOUT.items()}

    time_ref_low = struct.unpack_from("<I", raw, 338)[0]
    time_ref_high = struct.unpack_from("<I", raw, 342)[0]
    time_reference = time_ref_low | (time_ref_high << 32)

    version = struct.unpack_from("<H", raw, 346)[0]
    umid = raw[348:412]

    loudness_value = loudness_range = max_true_peak = max_momentary = max_short_term = None
    if version >= 2:
        # All five are int16, stored as the real value * 100.
        (raw_lv, raw_lr, raw_mtp, raw_mm, raw_ms) = struct.unpack_from("<5h", raw, 412)
        loudness_value = raw_lv / 100.0
        loudness_range = raw_lr / 100.0
        max_true_peak = raw_mtp / 100.0
        max_momentary = raw_mm / 100.0
        max_short_term = raw_ms / 100.0
    else:
        logger.debug("bext version %d < 2, loudness fields not present, leaving as None", version)

    coding_history = decode_lenient(raw[FIXED_SIZE:].rstrip(b"\x00")).strip()

    return BextData(
        description=fields["description"],
        originator=fields["originator"],
        originator_reference=fields["originator_reference"],
        origination_date=fields["origination_date"],
        origination_time=fields["origination_time"],
        time_reference=time_reference,
        version=version,
        umid=umid,
        loudness_value=loudness_value,
        loudness_range=loudness_range,
        max_true_peak_level=max_true_peak,
        max_momentary_loudness=max_momentary,
        max_short_term_loudness=max_short_term,
        coding_history=coding_history,
    )


def to_raw_dict(bext: BextData) -> dict:
    """Flat dict form for Phase-4 raw storage (models.RawFileMetadata.bext_raw).
    UMID is kept as hex since it's binary and not meaningfully displayable.
    """
    return {
        "description": bext.description,
        "originator": bext.originator,
        "originator_reference": bext.originator_reference,
        "origination_date": bext.origination_date,
        "origination_time": bext.origination_time,
        "time_reference": bext.time_reference,
        "version": bext.version,
        "umid_hex": bext.umid.hex(),
        "loudness_value": bext.loudness_value,
        "loudness_range": bext.loudness_range,
        "max_true_peak_level": bext.max_true_peak_level,
        "max_momentary_loudness": bext.max_momentary_loudness,
        "max_short_term_loudness": bext.max_short_term_loudness,
        "coding_history": bext.coding_history,
    }

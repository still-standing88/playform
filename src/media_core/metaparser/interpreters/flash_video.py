"""FLV (Flash Video) interpreter, built on metaparser.chunks.flv_walker and
metaparser.interpreters.amf0.

Only the "script data" tag (type 18) carries descriptive metadata — almost
always a two-value AMF0 sequence: a name string (conventionally
"onMetaData") followed by an object/ECMA-array of whatever properties the
encoder chose to write (duration, width, height, framerate, codec ids,
encoder name, and often custom fields specific to the encoder). That value
is decoded and returned as-is via amf0.py's generic decoder — no fixed key
whitelist, since encoders vary in what they include and this project's rule
is to never drop unrecognized fields.
"""

from __future__ import annotations

import logging

from media_core.metaparser.chunks import flv_walker
from media_core.metaparser.interpreters import amf0

logger = logging.getLogger(__name__)


def parse(data: bytes) -> dict:
    """Returns {'script_data': {...}, 'audio_tag_count': N, 'video_tag_count': N}.
    script_data is whatever the first parseable script-data tag decoded to
    (a plain dict, dynamically shaped) — empty if the file has no script
    data tag or it failed to decode, which is logged, never raised.
    """
    result: dict = {"script_data": {}, "audio_tag_count": 0, "video_tag_count": 0}

    for tag in flv_walker.walk(data):
        if tag.tag_type == flv_walker.TAG_TYPE_AUDIO:
            result["audio_tag_count"] += 1
        elif tag.tag_type == flv_walker.TAG_TYPE_VIDEO:
            result["video_tag_count"] += 1
        elif tag.tag_type == flv_walker.TAG_TYPE_SCRIPT_DATA and not result["script_data"]:
            try:
                values = amf0.decode_all(tag.raw)
            except Exception as exc:  # defensive: decode_all already degrades gracefully, but never let this be fatal
                logger.warning("FLV script data tag failed to decode: %s", exc)
                continue
            # Conventionally [name_string, properties_object, ...] — surface
            # whatever object/array-shaped value follows the name rather than
            # hardcoding a check for the literal string "onMetaData", since
            # some encoders use other script-data names.
            for value in values[1:]:
                if isinstance(value, dict):
                    result["script_data"] = value
                    break

    return result

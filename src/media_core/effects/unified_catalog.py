from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Type

from media_core.av_play.mpv_audio_filter import MPVAudioFilter
from media_core.av_play.mpv_effects_catalog import (
    MPVEffectParam,
    MPVEffectDefinition,
    MPV_EFFECTS,
    get_mpv_effect,
)
from media_core.ffmpeg.effects_catalog import (
    EffectParam,
    EffectDefinition,
    EFFECTS,
    EFFECTS_BY_ID,
    get_effect,
    effects_for_branch,
    categories_for_branch,
)

_MANUAL_DIR = "archive/docs/ffmpeg-manuals/ffmpeg-filters/8-audio-filters"


def _fmt(value) -> str:
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


@dataclass(frozen=True)
class UnifiedEffect:
    id: str
    label: str
    category: str
    params: list
    manual_source: str = ""
    filter_class: Optional[Type[MPVAudioFilter]] = None
    build_filter: Optional[Callable[[dict], str]] = None
    branch: Optional[str] = None
    needs_secondary_input: bool = False
    needs_analysis_pass: Optional[str] = None
    live_capable: bool = True


def _mpv_to_ffmpeg_builder(effect: MPVEffectDefinition) -> Optional[Callable[[dict], str]]:
    cls = effect.filter_class
    try:
        probe = cls()
    except TypeError:
        return None
    info = probe.info
    syntax = info.get("effect_syntax", "lavfi")
    if syntax not in ("lavfi", "native"):
        return None
    mpv_name = info.get("mpv_filter_name", "")
    if not mpv_name:
        return None
    param_map = info.get("mpv_param_map", {})

    def builder(values: dict) -> str:
        merged = {k: v for k, v in probe.get_parameters().items()}
        merged.update({k: v for k, v in values.items() if k in param_map})
        parts = []
        for key, value in merged.items():
            entry = param_map.get(key)
            if not entry:
                continue
            parts.append(f"{entry[0]}={_fmt(value)}")
        param_string = ":".join(parts)
        if syntax == "native":
            return f"{mpv_name}={param_string}" if param_string else mpv_name
        return f"{mpv_name}={param_string}" if param_string else mpv_name

    return builder


def _ffmpeg_to_live(effect: EffectDefinition) -> bool:
    return effect.needs_analysis_pass is None and not effect.needs_secondary_input


def _params_to_mpv(params: list) -> list:
    return [
        MPVEffectParam(
            key=p.key, label=p.label, kind=p.kind, default=p.default,
            value_range=p.value_range, choices=p.choices, suffix=p.suffix,
        )
        for p in params
    ]


UNIFIED_EFFECTS: list[UnifiedEffect] = []
_SEEN_IDS: set[str] = set()

for _effect in MPV_EFFECTS:
    UNIFIED_EFFECTS.append(UnifiedEffect(
        id=_effect.id,
        label=_effect.label,
        category=_effect.category,
        params=list(_effect.params),
        manual_source=_effect.manual_source,
        filter_class=_effect.filter_class,
        build_filter=_mpv_to_ffmpeg_builder(_effect),
        live_capable=True,
    ))
    _SEEN_IDS.add(_effect.id)

_FFMPEG_CATEGORY_REMAP = {
    "Loudness": "Dynamics",
    "Volume": "Dynamics",
    "Silence": "Edits",
    "Fade": "Edits",
    "Trim": "Edits",
    "Reverse": "Edits",
}

for _effect in EFFECTS:
    if _effect.id in _SEEN_IDS:
        continue
    _SEEN_IDS.add(_effect.id)
    UNIFIED_EFFECTS.append(UnifiedEffect(
        id=_effect.id,
        label=_effect.label,
        category=_FFMPEG_CATEGORY_REMAP.get(_effect.category, _effect.category),
        params=list(_effect.params),
        manual_source=_effect.manual_source,
        build_filter=_effect.build_filter,
        branch=_effect.branch,
        needs_secondary_input=_effect.needs_secondary_input,
        needs_analysis_pass=_effect.needs_analysis_pass,
        live_capable=_ffmpeg_to_live(_effect),
    ))

UNIFIED_EFFECTS_BY_ID: dict[str, UnifiedEffect] = {e.id: e for e in UNIFIED_EFFECTS}


def get_unified_effect(effect_id: str) -> Optional[UnifiedEffect]:
    return UNIFIED_EFFECTS_BY_ID.get(effect_id)


def unified_categories() -> list[str]:
    seen: list[str] = []
    for effect in UNIFIED_EFFECTS:
        if effect.category not in seen:
            seen.append(effect.category)
    return seen


def effects_for_category(category: str) -> list[UnifiedEffect]:
    return [e for e in UNIFIED_EFFECTS if e.category == category]


def live_effects() -> list[UnifiedEffect]:
    return [e for e in UNIFIED_EFFECTS if e.live_capable]


def offline_effects() -> list[UnifiedEffect]:
    return [e for e in UNIFIED_EFFECTS if e.build_filter is not None]

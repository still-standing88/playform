import json
import os

from utilities.functions import get_app_path

PRESETS_ROOT = os.path.join(get_app_path(), "data", "presets", "audio_effects")


def _presets_dir(effect_id: str) -> str:
    return os.path.join(PRESETS_ROOT, effect_id)


def _ensure_presets_dir(effect_id: str) -> str:
    directory = _presets_dir(effect_id)
    os.makedirs(directory, exist_ok=True)
    return directory


def _preset_path(effect_id: str, name: str) -> str:
    safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip() or "preset"
    return os.path.join(_presets_dir(effect_id), f"{safe_name}.json")


def _seed_defaults_if_empty(effect_id: str, directory: str):
    if os.listdir(directory):
        return
    # Local import: default_effect_presets imports mpv_effects_catalog,
    # which would otherwise be a circular import at module load time.
    from media_core.av_play.default_effect_presets import DEFAULT_EFFECT_PRESETS

    for name, values in DEFAULT_EFFECT_PRESETS.get(effect_id, []):
        save_preset(effect_id, name, values)


def list_presets(effect_id: str) -> list:
    directory = _ensure_presets_dir(effect_id)
    _seed_defaults_if_empty(effect_id, directory)
    return sorted(
        os.path.splitext(filename)[0]
        for filename in os.listdir(directory)
        if filename.endswith(".json")
    )


def save_preset(effect_id: str, name: str, values: dict):
    _ensure_presets_dir(effect_id)
    with open(_preset_path(effect_id, name), "w", encoding="utf-8") as handle:
        json.dump(values, handle, indent=2)


def load_preset(effect_id: str, name: str) -> dict:
    with open(_preset_path(effect_id, name), "r", encoding="utf-8") as handle:
        return json.load(handle)


def delete_preset(effect_id: str, name: str):
    path = _preset_path(effect_id, name)
    if os.path.exists(path):
        os.remove(path)

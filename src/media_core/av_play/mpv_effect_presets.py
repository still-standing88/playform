import json
import logging
import os

from utilities.functions import get_app_path

# Legacy per-effect-id directory tree, only kept around for the one-shot
# migration in _migrate_legacy_presets() -- presets themselves now live in
# the user_presets table (user.sqlite3), one row per (kind, name) where
# kind is "mpv_effect:<effect_id>".
LEGACY_PRESETS_ROOT = os.path.join(get_app_path(), "data", "presets", "audio_effects")
_migrated_legacy = False


def _kind_for(effect_id: str) -> str:
    return f"mpv_effect:{effect_id}"


def _migrate_legacy_presets():
    global _migrated_legacy
    if _migrated_legacy:
        return
    _migrated_legacy = True
    if not os.path.isdir(LEGACY_PRESETS_ROOT):
        return
    try:
        from app_db import user_presets
        for effect_id in os.listdir(LEGACY_PRESETS_ROOT):
            directory = os.path.join(LEGACY_PRESETS_ROOT, effect_id)
            if not os.path.isdir(directory):
                continue
            kind = _kind_for(effect_id)
            for filename in os.listdir(directory):
                if not filename.endswith(".json"):
                    continue
                name = os.path.splitext(filename)[0]
                path = os.path.join(directory, filename)
                try:
                    with open(path, "r", encoding="utf-8") as handle:
                        values = json.load(handle)
                    user_presets.set(kind, name, values)
                    os.remove(path)
                except Exception:
                    logging.exception("Failed to migrate legacy mpv effect preset %r", path)
            try:
                os.rmdir(directory)
            except Exception:
                pass
        try:
            os.rmdir(LEGACY_PRESETS_ROOT)
        except Exception:
            pass
    except Exception:
        logging.exception("Failed to migrate legacy mpv effect presets")


def _seed_defaults_if_empty(effect_id: str):
    from app_db import user_presets
    if user_presets.list_names(_kind_for(effect_id)):
        return
    # Local import: default_effect_presets imports mpv_effects_catalog,
    # which would otherwise be a circular import at module load time.
    from media_core.av_play.default_effect_presets import DEFAULT_EFFECT_PRESETS

    for name, values in DEFAULT_EFFECT_PRESETS.get(effect_id, []):
        save_preset(effect_id, name, values)


def list_presets(effect_id: str) -> list:
    _migrate_legacy_presets()
    from app_db import user_presets
    _seed_defaults_if_empty(effect_id)
    return sorted(user_presets.list_names(_kind_for(effect_id)))


def save_preset(effect_id: str, name: str, values: dict):
    from app_db import user_presets
    user_presets.set(_kind_for(effect_id), name, values)


def load_preset(effect_id: str, name: str) -> dict:
    from app_db import user_presets
    data = user_presets.get(_kind_for(effect_id), name)
    if data is None:
        raise FileNotFoundError(f"Preset {name!r} not found for effect {effect_id!r}")
    return data


def delete_preset(effect_id: str, name: str):
    from app_db import user_presets
    user_presets.delete(_kind_for(effect_id), name)

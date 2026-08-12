import json
import logging
import os

from utilities.functions import get_app_path

KIND = "ffmpeg_batch"
# Legacy directory, only kept around for the one-shot migration below --
# presets themselves now live in the user_presets table (user.sqlite3).
LEGACY_PRESETS_DIR = os.path.join(get_app_path(), "data", "presets", "batch_converter")
_migrated_legacy = False


def _migrate_legacy_presets():
    global _migrated_legacy
    if _migrated_legacy:
        return
    _migrated_legacy = True
    if not os.path.isdir(LEGACY_PRESETS_DIR):
        return
    try:
        from app_db import user_presets
        for filename in os.listdir(LEGACY_PRESETS_DIR):
            if not filename.endswith(".json"):
                continue
            name = os.path.splitext(filename)[0]
            path = os.path.join(LEGACY_PRESETS_DIR, filename)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                user_presets.set(KIND, name, payload)
                os.remove(path)
            except Exception:
                logging.exception("Failed to migrate legacy ffmpeg batch preset %r", path)
        try:
            os.rmdir(LEGACY_PRESETS_DIR)
        except Exception:
            pass
    except Exception:
        logging.exception("Failed to migrate legacy ffmpeg batch presets")


def list_presets() -> list:
    _migrate_legacy_presets()
    from app_db import user_presets
    return sorted(user_presets.list_names(KIND))


def save_preset(name: str, convert_state: dict, processing_state: list):
    from app_db import user_presets
    payload = {"convert": convert_state, "processing": processing_state}
    user_presets.set(KIND, name, payload)


def load_preset(name: str) -> dict:
    from app_db import user_presets
    data = user_presets.get(KIND, name)
    if data is None:
        raise FileNotFoundError(f"Preset {name!r} not found")
    return data


def delete_preset(name: str):
    from app_db import user_presets
    user_presets.delete(KIND, name)

import json
import os

from utilities.functions import get_app_path

PRESETS_DIR = os.path.join(get_app_path(), "data", "presets", "batch_converter")


def _ensure_presets_dir():
    os.makedirs(PRESETS_DIR, exist_ok=True)


def _preset_path(name: str) -> str:
    safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).strip() or "preset"
    return os.path.join(PRESETS_DIR, f"{safe_name}.json")


def list_presets() -> list:
    _ensure_presets_dir()
    return sorted(
        os.path.splitext(filename)[0]
        for filename in os.listdir(PRESETS_DIR)
        if filename.endswith(".json")
    )


def save_preset(name: str, convert_state: dict, processing_state: list):
    _ensure_presets_dir()
    payload = {"convert": convert_state, "processing": processing_state}
    with open(_preset_path(name), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def load_preset(name: str) -> dict:
    with open(_preset_path(name), "r", encoding="utf-8") as handle:
        return json.load(handle)


def delete_preset(name: str):
    path = _preset_path(name)
    if os.path.exists(path):
        os.remove(path)

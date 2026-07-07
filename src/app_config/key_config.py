import os
import re
import keyboard
import configparser as cfgp

from PySide6.QtCore import QObject, Signal

from utilities.functions import get_app_path
from app_constance import default_keys


class HotkeyBridge(QObject):
    triggered = Signal(str)


key_dict = default_keys.key_dict.copy()
hotkeys = {}
hotkeys_funcs = {}
key_config = cfgp.ConfigParser()
_bridge: HotkeyBridge | None = None


def _get_bridge() -> HotkeyBridge:
    global _bridge
    if _bridge is None:
        _bridge = HotkeyBridge()
    return _bridge


def modifyKey(section, hotkey, sequence):
    key_config[section][hotkey] = sequence
    if section.lower() == "global":
        old_id = hotkeys.pop(hotkey, None)
        if old_id is not None:
            try:
                keyboard.remove_hotkey(old_id)
            except Exception:
                pass
        bridge = _get_bridge()
        hid = keyboard.add_hotkey(sequence, lambda n=hotkey: bridge.triggered.emit(n))
        hotkeys[hotkey] = hid


def is_valid_hotkey(hotkey):
    pattern = r"(alt|ctrl|shift|win)?\+?(alt|ctrl|shift|win)?\+?(alt|ctrl|shift|win)?\+?(space|enter|left|right|up|down|pageup|pagedown|home|end|\[|\]|f1|f2|f3|f4|f5|f6|f7|f8|f9|f10|f11|f12|\w)?"
    match = re.match(pattern, hotkey.replace(" ", "").lower())
    return bool(match)


def keysToDefault():
    global key_config
    for keyset, keys in key_dict.items():
        key_config[keyset] = {}
        for key in keys:
            key_config[keyset][key] = keys[key]


def is_valid_config():
    for default_hotkeys_section, current_hotkeys_section in zip(list(default_keys.key_dict.keys()), list(key_config.keys())):
        if default_hotkeys_section != current_hotkeys_section:
            return False
        for default_hotkey, current_hotkey in zip(list(default_keys.key_dict[default_hotkeys_section].keys()), list(key_config[current_hotkeys_section].keys())):
            if default_hotkey != current_hotkey:
                return False
    return True


def saveConfig():
    key_config_file = f"{get_app_path()}/data/key_config.cfg"
    with open(key_config_file, "w") as config_file:
        key_config.write(config_file)


def load_keys():
    current_path = get_app_path()
    key_config_file = f"{current_path}/data/key_config.cfg"
    if os.path.exists(key_config_file):
        key_config.read(key_config_file)
        if not is_valid_config():
            keysToDefault()
            saveConfig()
    else:
        keysToDefault()
        saveConfig()


def apply_global_hotkeys():
    for hid in list(hotkeys.values()):
        try:
            keyboard.remove_hotkey(hid)
        except Exception:
            pass
    hotkeys.clear()

    bridge = _get_bridge()
    global_section = key_config.get("Global", {}) or key_dict.get("Global", {})
    for action, sequence in global_section.items():
        if not sequence:
            continue
        try:
            name = action
            hid = keyboard.add_hotkey(sequence, lambda n=name: bridge.triggered.emit(n))
            hotkeys[action] = hid
        except Exception:
            pass


def initialize(func_dict):
    global hotkeys_funcs
    hotkeys_funcs = func_dict

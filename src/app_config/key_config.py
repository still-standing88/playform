import os
import re
import configparser as cfgp

from utilities.functions import get_app_path
from app_constance import default_keys

key_dict = default_keys.key_dict.copy()
hotkeys = {}
hotkeys_funcs = {}
key_config = cfgp.ConfigParser()
key_config.optionxform = str
DISABLED_HOTKEYS_SECTION = "Disabled hotkeys"


def _disabled_hotkey_id(section, action):
    return f"{section}::{action}"


def is_hotkey_enabled(section, action):
    if DISABLED_HOTKEYS_SECTION not in key_config:
        return True
    return not key_config.getboolean(
        DISABLED_HOTKEYS_SECTION,
        _disabled_hotkey_id(section, action),
        fallback=False,
    )


def set_hotkey_enabled(section, action, enabled):
    if DISABLED_HOTKEYS_SECTION not in key_config:
        key_config[DISABLED_HOTKEYS_SECTION] = {}
    key_config[DISABLED_HOTKEYS_SECTION][
        _disabled_hotkey_id(section, action)
    ] = str(not enabled)


def get_hotkey_sequence(section, action):
    return key_config.get(section, action, fallback="")


def get_active_hotkey_sequence(section, action):
    if not is_hotkey_enabled(section, action):
        return ""
    return get_hotkey_sequence(section, action)


def set_hotkey_sequence(section, action, sequence):
    key_config[section][action] = sequence


def reset_hotkey(section, action):
    set_hotkey_sequence(section, action, key_dict[section][action])
    set_hotkey_enabled(section, action, True)


def modifyKey(section, hotkey, sequence):
    import keyboard
    set_hotkey_sequence(section, hotkey, sequence)
    if section.lower() == "global":
        old_id = hotkeys.pop(hotkey, None)
        if old_id is not None:
            try:
                keyboard.remove_hotkey(old_id)
            except Exception:
                pass
        func = hotkeys_funcs.get(hotkey)
        active_sequence = get_active_hotkey_sequence(section, hotkey)
        if active_sequence and func:
            hid = keyboard.add_hotkey(active_sequence, func)
            hotkeys[hotkey] = hid


def is_valid_hotkey(hotkey):
    pattern = r"(alt|ctrl|shift|win)?\+?(alt|ctrl|shift|win)?\+?(alt|ctrl|shift|win)?\+?(space|enter|left|right|up|down|pageup|pagedown|home|end|\[|\]|f1|f2|f3|f4|f5|f6|f7|f8|f9|f10|f11|f12|\w)?"
    match = re.match(pattern, hotkey.replace(" ", "").lower())
    return bool(match)


def keysToDefault():
    global key_config
    key_config.remove_section(DISABLED_HOTKEYS_SECTION)
    for keyset, keys in key_dict.items():
        key_config[keyset] = {}
        for key in keys:
            key_config[keyset][key] = keys[key]


def is_valid_config():
    default_sections = {s.lower() for s in default_keys.key_dict}
    config_sections = {
        s.lower() for s in key_config
        if s.lower() not in {"default", DISABLED_HOTKEYS_SECTION.lower()}
    }
    if default_sections != config_sections:
        return False
    for section in default_keys.key_dict:
        config_section = next((s for s in key_config if s.lower() == section.lower()), None)
        if not config_section:
            return False
        default_opts = {k.lower() for k in default_keys.key_dict[section]}
        config_opts = {k.lower() for k in key_config[config_section]}
        if default_opts != config_opts:
            return False
    return True


def merge_missing_keys() -> bool:
    """Adds actions introduced since the user's config was written, keeping
    their existing bindings. Without this, any new default key made the whole
    config 'invalid' and keysToDefault() discarded every customization."""
    changed = False
    for section, keys in default_keys.key_dict.items():
        config_section = next((s for s in key_config if s.lower() == section.lower()), None)
        if config_section is None:
            key_config[section] = dict(keys)
            changed = True
            continue
        existing = {k.lower() for k in key_config[config_section]}
        for action, sequence in keys.items():
            if action.lower() not in existing:
                key_config[config_section][action] = sequence
                changed = True
    return changed


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
            if merge_missing_keys() and is_valid_config():
                saveConfig()
            else:
                keysToDefault()
                saveConfig()
    else:
        keysToDefault()
        saveConfig()


def apply_global_hotkeys():
    import keyboard
    for hid in list(hotkeys.values()):
        try:
            keyboard.remove_hotkey(hid)
        except Exception:
            pass
    hotkeys.clear()

    if "Global" in key_config:
        global_section = key_config["Global"]
    else:
        global_section = key_dict.get("Global", {})
    for action in global_section:
        sequence = get_active_hotkey_sequence("Global", action)
        if not sequence:
            continue
        func = hotkeys_funcs.get(action)
        if func:
            try:
                hid = keyboard.add_hotkey(sequence, func)
                hotkeys[action] = hid
            except Exception:
                pass


def initialize(func_dict):
    global hotkeys_funcs
    hotkeys_funcs = func_dict

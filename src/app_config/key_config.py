import os
import re
#import keyboard
import configparser as cfgp

from utilities.functions import get_app_path
from app_constance import default_keys

key_dict = default_keys.key_dict.copy()
hotkeys = {}
hotkeys_funcs = {}
key_config = cfgp.ConfigParser()

def modifyKey(section,hotkey,sequence):
    key_config[section][hotkey] = sequence
    if section == "global":
        pass #keyboard.remove_hotkey(hotkeys.pop(hotkey))
        #hotkeys[hotkey] = keyboard.add_hotkey(sequence,hotkeys_funcs[hotkey])
        

def is_valid_hotkey(hotkey):
    pattern = r"(alt|ctrl|shift|win)?\+?(alt|ctrl|shift|win)?\+?(alt|ctrl|shift|win)?\+?(space|enter|left|right|up|down|pageup|pagedown|home|end|\[|\]|f1|f2|f3|f4|f5|f6|f7|f8|f9|f10|f11|f12|\w)?"
    match = re.match(pattern, hotkey.replace(" ","").lower())
    return bool(match)

def keysToDefault():
    global key_config
    for keyset,keys in key_dict.items():
        key_config[keyset] = {}
        for key  in keys:
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
    if os.path.exists(key_config_file) == True: 
        key_config.read(key_config_file)
        if not is_valid_config():
            keysToDefault()
            saveConfig()
    else:
        keysToDefault()
        saveConfig()



def apply_global_hotkeys():
    #for hotkey in hotkeys:
        #keyboard.remove_hotkey(hotkeys[hotkey])
    hotkeys.clear()
    #for hotkey in key_dict["Global"]:
        #hotkeys[hotkey] = keyboard.add_hotkey(key_config["Global"][hotkey],hotkeys_funcs[hotkey])



def initialize(func_dict):
    global hotkeys_funcs
    hotkeys_funcs = func_dict
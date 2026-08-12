import os, sys, shutil, json

from utilities.functions import get_parent_dir, hexify,dehexify, user_path, get_app_path
from app_constance import prefs_dict

prefs = prefs_dict.prefs.copy()
current_path = get_app_path()
sc_path = f"{current_path}/Screenshots/"
data_path = f"{current_path}/data/"
#marks_path = f"{data_path}/file_marks/"
playlist_path = f"{data_path}/playlists"
prefs_file = os.path.join(data_path, "prefs.json")

RUNTIME_PREFS_KEY = "runtime_prefs"


def _dialog_subset(data: dict) -> dict:
    return {k: v for k, v in data.items() if k in prefs_dict.DIALOG_PREFS_KEYS}


def _runtime_subset(data: dict) -> dict:
    return {k: v for k, v in data.items() if k not in prefs_dict.DIALOG_PREFS_KEYS}


def processData(path,mode,data="", target=""):
    if mode == "read":
        with open(path,"r") as file:
            tstrS = file.readlines()
            tstr = []
            for line in range(0,len(tstrS)-1+1):
                if tstrS[line]: tstr.append(dehexify(tstrS[line]))

        dstr = ""
        pstr = {}
        for line in tstr:
            dstr += line+"\n"
            pstr = json.loads(dstr)
        global prefs
        # prefs.json only ever holds the dialog-exposed subset now -- merge
        # it over the in-memory dict rather than replacing it outright, so
        # whatever runtime/non-dialog keys are already loaded (from
        # app_settings, see load_runtime_prefs()) survive this read.
        prefs.update(pstr)

    elif mode == "write":
        with open(path,"w") as file:
            tstr = hexify(json.dumps(_dialog_subset(data)))
            file.write(tstr)

    elif mode == "delete":
        with open(path,"w") as file:
            file.write("")

def load_runtime_prefs():
    """Loads the non-dialog subset of `prefs` from app_settings
    (user.sqlite3), migrating it out of a legacy all-in-one prefs.json on
    first run after upgrade. Missing/corrupt data falls back to defaults
    already present in `prefs` (prefs_dict.prefs.copy()) rather than
    raising, per the "handled silently and gracefully" requirement."""
    global prefs
    try:
        from app_db import app_settings
        data = app_settings.get(RUNTIME_PREFS_KEY)
        if data is None:
            # First run after upgrading from a version where prefs.json
            # held everything -- whatever non-dialog keys processData just
            # loaded into `prefs` from the old file become the initial
            # runtime_prefs row, then get pruned back out of prefs.json on
            # the next save().
            data = _runtime_subset(prefs)
            app_settings.set(RUNTIME_PREFS_KEY, data)
        if isinstance(data, dict):
            prefs.update(data)
    except Exception:
        pass

def save_runtime_prefs():
    try:
        from app_db import app_settings
        app_settings.set(RUNTIME_PREFS_KEY, _runtime_subset(prefs))
    except Exception:
        pass

def ensure_prefs_schema():
    global prefs
    updated = False

    for key, default_value in prefs_dict.prefs.items():
        if key not in prefs:
            prefs[key] = default_value
            updated = True

    return updated

def save():
    processData(prefs_file, "write", prefs) # type: ignore
    save_runtime_prefs()

def reset():
    global prefs
    prefs = prefs_dict.prefs.copy()
    save()

def is_prefs_dict_valid():
    if set(list(prefs.keys())) == set(list(prefs_dict.prefs.keys())):
        return True
    return False


def initialize():
    if not os.path.exists(data_path): os.makedirs(data_path)
    if not os.path.exists(sc_path): os.makedirs(sc_path)
    if not os.path.exists(playlist_path): os.makedirs(playlist_path)
    if os.path.exists(prefs_file):
        try:
            processData(prefs_file, "read")
            load_runtime_prefs()
            if ensure_prefs_schema():
                save()
        except:
            reset()
    else:
        load_runtime_prefs()
        if ensure_prefs_schema():
            pass
        save()

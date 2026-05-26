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


def processData(path,mode,data="", target=""):
    if mode == "read":
        with open(path,"r") as file:
            tstrS = file.readlines()
            tstr = []
            for line in range(0,len(tstrS)-1+1):
                if tstrS[line]: tstr.append(dehexify(tstrS[line]))

        dstr = ""
        for line in tstr:
            dstr += line+"\n"
            pstr = json.loads(dstr)
            global prefs
            prefs = pstr

    elif mode == "write":
        with open(path,"w") as file:
            tstr = hexify(json.dumps(data))
            file.write(tstr)

    elif mode == "delete":
        with open(path,"w") as file:
            file.write("")

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
            if ensure_prefs_schema():
                save()
        except:
            reset()
    elif not os.path.exists(prefs_file):
        save()


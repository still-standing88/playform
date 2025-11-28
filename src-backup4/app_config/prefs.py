import os, sys, shutil, json

from utilities.functions import get_parent_dir, hexify,dehexify, user_path, get_app_path
from app_constance import prefs_dict

prefs = prefs_dict.prefs.copy()
current_path = get_app_path()
sc_path = f"{current_path}/Screen Shots/"
data_path = f"{current_path}/data/"
marks_path = f"{data_path}/file_marks/"
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

def save():        
    processData(prefs_file, "write", prefs)


def ffmpegbin():
    current_path = get_parent_dir()
    import pyffmpeg

    if prefs["ffmpeg_binary"] == "" or not os.path.exists(prefs["ffmpeg_binary"]):
        if not os.path.exists(f"{current_path}/bin/") : os.makedirs(f"{current_path}/bin/")
        ff = pyffmpeg.FFmpeg()
        ff.enable_log = False
        bin_path = ff.get_ffmpeg_bin()
        dest_path = f"{current_path}/bin/"
        shutil.copy(bin_path,dest_path)
        bin_dir = os.path.dirname(bin_path)
        ff.quit()
        del ff
        shutil.rmtree(bin_dir)
        prefs["ffmpeg_binary"] = f"{dest_path}/{os.path.split(bin_path)[1]}"
        save()

def initialize():
    if not os.path.exists(data_path): os.makedirs(data_path)
    if not os.path.exists(sc_path): os.makedirs(sc_path)
    if not os.path.exists(playlist_path): os.makedirs(playlist_path)
    if not os.path.exists(marks_path): os.makedirs(marks_path)
    if os.path.exists(prefs_file):
        processData(prefs_file, "read")
    elif not os.path.exists(prefs_file):
        save()
    ffmpegbin()

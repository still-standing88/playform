import os, sys, shutil, json
sys.path.append("..")
from utilities.functions import hexify,dehexify, userDir
from prefs_dict import prefs

current_path = os.path.abspath(".")
data_path = f"{current_path}/data/"
sc_path = f"{data_path}/Screen Shots/"
marks_path = f"{current_path}/file_marks/"
playlist_path = f"{current_path}/playlists"
prefs_file = f"{current_path}/prefs.json"

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
    processData(path+"prefs.json","write",prefs)

def appendToLibrary():
    userpath = userDir()
    folders = ["Desktop","Documents","Downloads","Music","Videos"]
    for folder in folders:
        path = f"{userpath}\\{folder}\\"
        if os.path.exists(path): prefs["library"][folder] = path

def ffmpegbin():
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
    userpath = userDir()
    if os.path.exists(userpath+"\\documents\\"): prefs["default path"] = userpath+"\\documents\\"
    else: prefs["default path"] = userpath
    if not os.path.exists(current_path): os.makedirs(current_path)
    if not os.path.exists(sc_path): os.makedirs(sc_path)
    if not os.path.exists(playlist_path): os.makedirs(playlist_path)
    if not os.path.exists(markspath): os.makedirs(marks_path)
    if os.path.exists(prefs_file):
        processData(prefs_file, "read",prefs)
    elif not os.path.exists(prefs_file):
        appendToLibrary()
        save()
    ffmpegbin()

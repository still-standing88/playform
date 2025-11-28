import os
import music_tag
from functions import Formats, getFormat

types = ["video","audio"]
f = Formats()

class playlistError(Exception):
    def __init__(self,e):
        self.message = e
        super().__init__()


class Track:
    def __init__(self,path,isSupported=True):
        self.path = path
        if isSupported == True:
            self.attributes = music_tag.load_file(self.path)
            self.title = self.attributes["tracktitle"]
            self.artist = self.attributes["artist"]
            self.album = self.attributes["album"]
        else:
            self.title = "none"
            self.album = "None"
            self.artist = "None"

    def setAttribute(self,attribute,value):
        self.attribute[attribute] = value

    def appendAttribute(selfattribute,value):
        self.attributes.append_tag(attribute,value)

    def removeAttribute(self,attribute):
        self.attributes.remove_tag(aatribute)

    def save(self):
        self.attributes.save()

class Playlist:

    def __init__(self,type=None,name="",description=None,path=None,formats=None):
        self.path = path
        self.name = name
        self.description = description
        self.type = type
        self.files = {}
        self.supported_formats = [".mp3",".wav",".ogg",".flac",".aif",".aac",".m4a",".opus",""]
        self.formats = formats if formats is not None else self.supported_formats
        self.tracks = {}
        if self.path is not None and  self.path.endswith(".mpls") == False:
            raise playlistError("invalid playlist format")
            return 0
        if self.path is not None and os.path.exists(self.path) == True :self.load()
        if self.name == "": self.name = os.path.basename(self.path)
        if self.description is None: self.setDiscription("None")

    def load(self):
        structure = {}
        with open(self.path,"r") as data:
            lines = data.readlines()
            if len(lines) <3:
                raise playlistError("invalid playlist format")
                return 0
            name = lines[0].rstrip("\n")
            description = lines[1].rstrip("\n")
            type = lines[2].rstrip("\n")
            if description[0:12] != "description " or name[0:9] != "playlist " or type[0:7] != "type = ":
                raise playlistError("invalid playlist format")
                return 0
            if len(name) <10:
                raise playlistError("empty playlist name")
                return 0
            if type[7:12] not in types:
                raise playlistError("invalid playlist type")
                return 0
            structure["name"] = name[9:]
            structure["description"] = description[12:]
            structure["type"] = type[7:]
            if len(lines) >=4:
                self.processFiles(lines[3:])
            self.name = structure["name"]
            self.setDescription(structure["description"])
            self.type = structure["type"]
        if self.type == "audio": self.formats = f.audio
        elif self.type == "video": self.formats = f.video
        del structure

    def processFiles(self,data):
        for line in data:
            if line.startswith("file = ") == False:
                if line.rstrip("\n") == "": continue
                else:
                    raise playlistError("invalid playlist file format")
                return 0
            path = line.rstrip("\n")[7:]
            name = os.path.basename(line.rstrip("\n")[7:])
            self.files[name] = path
            ext = getFormat(path)
            self.tracks[name] = Track(path,isSupported=True if ext in self.supported_formats else False)

    def addEntry(self,path):
        if os.path.exists(path) == True and os.path.splitext(path)[1] in self.formats:
            self.files[os.path.basename(path)] = path
            ext = getFormat(path)
            self.tracks[os.path.basename(path)] = Track(path, isSupported=True if ext in self.supported_formats else False)
        else:
            raise playlistError("invalid path/format")

    def removeEntry(self,name):
        del self.files[name]
        track = self.tracks.pop(name)
        del track

    def clear(self):
        self.files.clear()
        names = list(self.tracks.keys())
        for track in range(len(self.tracks)-1,-1,-1):
            del self.tracks[names[track]]


    def setDescription(self,text):
        self.description = text

    def save(self,path=None,overried=False):
        if path is not None: self.path = path
        data_string = f"playlist {self.name}\rdescription {self.description}\rtype = {self.type}\r"
        for file in self.files:
            data_string+= f"file = {self.files[file]}\r"
        if overried==True:
            if os.path.exists(self.path)==True:os.remove(self.path)
            self.path = f"{os.path.dirname(self.path)}\\{self.name}.mpls"
        with open(self.path,"w") as file:
            file.write(data_string)

def importPls(path):
    data = {"files":{}}
    with open(path,"r") as file:
        lines = file.readlines()
        if line[1].startswith("NumberOfEntries=") == False or line[0] != "[playlist]":
                raise playlistError("invalid pls playlist format structure")
                return 0
        data["name"] = os.path.basename(path)
        data["description"] = "None"
        for line in lines:
            if line.startswith("file") == True and int(line[4]) and line[5] == "=":
                data["files"][os.path.basename[line[6:]]]
        return data

def exportPls(playlist,path):
    data_string = f"[playlist]\rNumberOfEntries={len(playlist.files)}\r"
    l = list(playlist.files.keys())
    for file in playlist.files:
        data_string+=f"file{l.index[file]}={playlist.files[file]}"
    with open(path,"w") as file:
        file.write(string_data)

def importM3u(path):
    pass

def exportM3u(playlist,path):
    pass

def importFromPlaylist(path):
    if path.endswith(".m3u") == True:
        data = importM3u(path)
    elif path.endswith(".pls") == True:
        data = importPls(path)
    else:
        raise playlistError("non support playlist format")
        return 0
    playlist = Playlist(data["name"],data["description"])
    playlist.files = data["files"]
    return Playlist

def export(playlist,path,format):
    if format == "m3u":
        exportM3u(playlist,path)
    elif format== "pls":
        exportPls(playlist,path)
    else:
        raise playlistError("non support playlist format")
        return 0



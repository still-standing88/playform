

class type:
    audio = "audio"
    video = "video"

class format_selector:

    def __init__(self,player="",instance="",vid=""):

        from prefs import prefs
        self.offset = prefs["offset"]["seek"]
        command_dict = {"audio":{"state":self.audioState,"button":self.audioButton, "forword":self.audioForword, "backword":self.audioBackword, "volume":self.audioVolume, "seek":self.audioSeek, "setVolume":self.audioSetVolume, "mute":self.audioMute,"stop":self.audioStop,"gettime":self.audioGettime,"getVolume":self.audioGetVolume},"video":{"button":self.videoButton, "forword":self.videoForword, "backword":self.videoBackword, "volume":self.videoVolume, "seek":self.videoSeek, "setVolume":self.videoSetVolume, "mute":self.videoMute,"stop":self.videoStop, "gettime":self.videoGettime,"state":self.videoState,"getVolume":self.videoGetVolume}}
        self.f = formats
        self.player = player
        self.instance = instance
        self.vid = vid
        self.__dict__.update(command_dict)

    def command(self,format,command,value=None):
        if format in self.f.audio:
            if self.player and self.instance:
                if value is None:
                    self.audio[command]()
                elif value is not None:
                    self.audio[command]
        elif format in self.f.video:
            if self.vid:
                if value is None:
                    self.video[command]()
                elif value is not None:
                    self.video[command]

    def setProperty(self,format,property,value,value2=None):
        type = ""
        if format in formats.audio: type = "audio"
        elif format in formats.video: type = "video"
        if property == "time":
            getattr(self,type)["seek"](value)
        elif property == "volume":
            getattr(self,type)["volume"](value)
        elif property == "setVolume":
            getattr(self,type)["setVolume"](value,value2)

    def audioButton(self): self.player.button(self.instance)

    def audioForword(self): self.player.forword(self.instance,self.offset)

    def audioBackword(self): self.player.backword(self.instance,self.offset)

    def audioMute(self): self.player.mute(self.instance)

    def audioStop(self): self.player.stop(self.instance)

    def audioVolume(self,offset): self.player.setvolume(self.instance,offset)

    def audioSetVolume(self,state,offset): self.player.setVolume(self.instance,state,offset)

    def audioSeek(self,offset): self.player.settime(self.instance,offset)

    def audioGettime(self):return self.player.gettime(self.instance)

    def audioState(self): return self.player.state(self.instance)

    def audioGetVolume(self): return self.player.getvolume(self.instance)

    def videoButton(self): self.vid.button()

    def videoForword(self): self.vid.forword(self.offset)

    def videoBackword(self): self.vid.backword(self.offset)

    def videoMute(self): self.vid.mute()

    def videoStop(self): self.vid.stop()

    def videoVolume(self,offset): self.vid.setvolume(offset)

    def videoSetVolume(self,state,offset): self.vid.setVolume(state,offset)

    def videoSeek(self,offset): self.vid.settime(offset)

    def videoGettime(self): return self.vid.gettime()

    def videoState(self): return self.vid.state()

    def videoGetVolume(self): return self.vid.getvolume()

def get_dir_files(widget,path):
    fr = ""
    dir = os.path.dirname(path)
    files = []
    dir_list = os.listdir(dir)
    if widget.type == type.audio:
        fr = formats.audio
    elif widget.type == type.video:
        fr = formats.video
    for item in dir_list:
        if os.path.isfile(os.path.join(dir,item)) and os.path.splitext(os.path.join(dir,item))[1] in fr:
            files.append(os.path.join(dir,item))
    return files


import wmp, player, prefs
from functions import messageBox, media_url

offset = prefs.prefs["offset"]

def initialize():
    global mediaPlayer
    global player
    global loader
    mediaPlayer = wmp.Player()
    loader = mediaPlayer.load()
    player = mediaPlayer.player()

class Audio(player.Player):
    def __init__(self,parent,name,path,playlist=None,url=False):
        self.url = url
        self.playlist=playlist
        self.parent = parent
        self.path = path
        self.name = name
        self.player = player
        self.vid = None
        self.setpath()
        self.type = "audio"
        super().__init__(self.parent,self.name,self.path,playlist,url)
        if self.url ==False: self.recentMark()
        #else: self.nameFromUrl()
        self.setGeometry(260,200,300,300)


    def setpath(self):
        super().setpath()
        if self.url== False: self.instance= loader.file(self.path,player)
        else: self.instance= loader.url(self.path,player)

    def changePath(self,path):
        if self.url == True: return
        super().changePath(path)
        if player.state(self.instance) == wmp.WMP_STATE_PLAYING:
            self.controls.playbackStop()
        player.free(self.instance)
        self.instance= loader.file(self.path,player)
        self.controls.instance = self.instance
        self.controls.selector.instance = self.instance
        self.controls.markload()
        self.recentMark()

    def nameFromUrl(self):
        if self.url ==True:
            try:
                name = media_url(self.path)
                self.setName()
            except Exception as e:
                messageBox("Error",str(e))


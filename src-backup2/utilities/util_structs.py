
class Formats:

   def __init__(self):

        self.audio = list(formats["audio"].keys())
        self.video = list(formats["video"].keys())
        self.image = list(formats["image"].keys())


class Segment:

    def __init__(self):
        self.beginning = -1
        self.end = ""
        self.active = False

    def erase(self):
        self.beginning,self.end = -1,""
        self.active = False

    def mark_start(self,value):
        self.beginning = int(value)
        if self.end != "": self.active = True
        if self.end != "" and self.beginning > self.end: self.erase()

    def mark_end(self,value):
        self.end= int(value)
        if self.beginning != -1: self.active = True
        if self.end < self.beginning: self.erase()


class time_struct:


    def __init__(self, hours, minutes, seconds):
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds

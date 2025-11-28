
class Flags:

    def __init__(self):

        self.audio  = ""
        self.video = ""
        self.image = ""
        self.All = "All Files (*.*)"
        self.supported_formats =  list(formats["audio"].keys())+list(formats["video"].keys())
        self.supported = "Supported Files ("
        for format in self.supported_formats:
            self.supported += f"*{format};"
        self.supported+= ")"
        audio_list = list(formats["audio"].keys())
        video_list = list(formats["video"].keys())
        image_list = list(formats["image"].keys())
        for audio_format in formats["audio"]:
            self.audio += formats["audio"][audio_format]+" (*"+audio_format+")"
            if audio_list.index(audio_format) != len(audio_list)-1: self.audio += ";;"

        for video_format in formats["video"]:
            self.video += formats["video"][video_format]+" (*"+video_format+")"
            if video_list.index(video_format) != len(video_list)-1: self.video+= ";;"

        for image_format in formats["image"]:
            self.image += formats["image"][image_format]+" (*"+image_format+")"
            if image_list.index(image_format) != len(image_list)-1: self.image += ";;"

        self.all = self.supported+";;"+self.audio+";;"+self.video #+";;"+self.image

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

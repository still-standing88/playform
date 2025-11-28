import sys, os
sys.path.append("..")

from pycaption import *
from pycaption.base import *

import cchardet
import prefs

subtitle_formats = ["srt","vtt","smi","sami","scc","dfxp","ttml"]

class subtitle:

    def __init__(self,title,start,end):

        self.start = start
        self.end = end
        self.text = title

def findFile(path):
    subtitle_file = ""
    dir = os.path.dirname(path)
    filename = os.path.splitext(path)[0]
    for format in subtitle_formats:
        file_path = os.path.join(dir,f"{filename}.{format}")
        if os.path.exists(file_path) ==True:
            subtitle_file = file_path
            break
    return subtitle_file if subtitle_file != "" else None

def getEncoding(path):
    with open(path,"rb") as fp:
        encoding = cchardet.detect(fp.read())
    return encoding["encoding"]


def get_data(path):
    encoding = getEncoding(path)
    with open(path,"r",encoding=encoding) as f:
        data = f.read()
    return str(data)

def get_titles(path):
    sb_path = findFile(path)
    if sb_path is None: return None
    titles = []
    str_data = get_data(sb_path)
    reader = detect_format(str_data)
    captions = reader().read(str_data)
    for caption in captions.get_captions(prefs.prefs["subtitle-language"]):
        start = caption.start / 1000000.0  # Convert to seconds
        end = caption.end / 1000000.0      # Convert to seconds
        text = ' '.join([node.content for node in caption.nodes if node.type_ == CaptionNode.TEXT])
        titles.append(subtitle(text,start,end))
    return titles

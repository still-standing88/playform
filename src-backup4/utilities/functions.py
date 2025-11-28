import platform as pform
import ctypes
import binascii
import os, sys
import time, datetime as dt
import py_youtube, httpx
import subprocess as sp
import validators as vl
import pyperclip

from PySide6.QtCore import Qt as qt
from PySide6.QtCore import QUrl
from pathlib import Path

from utilities.util_structs import time_struct
from pynotifier import NotificationClient, Notification
from pynotifier.backends import platform



def copyText(text):
    if text != "":
        pyperclip.copy(text)


def convertSize(size):
    if int(size) >= 1048576: 
        cs =  size/1024 /1024
        return float(str(cs)[0:5])
    elif size <27:
        pass
    elif size >= 27 and size < 1048576:
        cs = size/1024
        return float(str(cs)[0:4])

def converttime(seconds):
    hours = int(seconds/3600)
    minutes = int((seconds - hours*3600) / 60)
    seconds = int(seconds - (hours*3600 + minutes*60))
    
    time_string = ""
    if hours != 0:
        time_string += "0" + str(hours) + ":" if hours < 10 else str(hours) + ":"
    if minutes != 0:
        time_string += "0" + str(minutes) + ":" if minutes <10 else str(minutes) + ":"
    if seconds != 0:
        time_string += "0" + str(seconds) if seconds < 10 else str(seconds)
    
    return time_string

def timeFrom(seconds):
    hours = int(seconds/3600)
    minutes = int((seconds - hours*3600) / 60)
    seconds = int(seconds - (hours*3600 + minutes*60))
    t = time_struct(hours,minutes,seconds)
    return t

def getFormat(path):
    return os.path.splitext(path)[1]


def datetime(time):
    from datetime import datetime as dt
    return dt.fromtimestamp(time)


def hexify(data):
    str_data = data.encode("utf-8")  # Encoded before hexlify
    hexData = binascii.hexlify(str_data).decode("utf-8")
    return hexData

def dehexify(data):
    byte_data = data#bytes.fromhex(data)  # Converted hex string to bytes
    str_data = binascii.unhexlify(byte_data).decode("utf-8")
    return str_data

def user_path():
    from os import path
    return path.expanduser("~")

def get_user_directories():
    userpath = user_path()
    folders = ["Desktop","Documents","Downloads","Music","Videos"]
    return [f"{userpath}/{folder}" for folder in folders if os.path.exists(f"{userpath}/{folder}")]


def fileProperties(filepath):
    pf = pform.system()
    if pf == "Windows":
        ctypes.windll.shell32.ShellExecuteW(None, "properties", filepath, None, None, 2)
    elif pf == "Linux":
        import subprocess
        subprocess.run(["xdg-open", filepath])
    import subprocess
    subprocess.Popen(["explorer", "/select,", filepath])


def notifyer(msg_title,msg):
    c = NotificationClient()
    c.register_backend(platform.Backend())
    notification = Notification(title=msg_title,message=msg)
    c.notify_all(notification)

def numberList(minx,maxx,mode):
    numlist = []
    for i in range(minx,maxx+1):
#        if i>=10 and mode=="1":
        if mode=="1":
            numlist.append(str(i))

        elif i<10 and mode=="2":
            numlist.append(str(0)+str(i))
        elif i>=10 and mode=="2":
            numlist.append(str(i))
    return numlist


def media_url(url):
    #return str(urllib.request.urlopen(urllib.request.Request(url)).info().get_filename)
    link = httpx.head(url,follow_redirects=True)
    return QUrl(str(link.url)).fileName()

def youtube_url(url):
    return py_youtube.Data(url).data()["title"]

def isValidURL(url):
    return  vl.url() == True

def network_check():
    return sp.call(['ping','-n','1','8.8.8.8'])


def open_explorer(path):
    sp.Popen(fr'explorer /select,"{path}"')

def is_frozen():
    return getattr(sys, 'frozen', False) or hasattr(sys, '__compiled__') or 'nuitka' in sys.executable.lower()

def get_app_path() -> str:
    if is_frozen():
        BASE_DIR = Path(sys.executable).parent
    else:
        BASE_DIR = Path(__file__).parent.parent
    return str(BASE_DIR)

def get_script_parent_dir():
    return Path(__file__).parent.parent.parent

def get_exe_parent_dir():
    return Path(sys.executable).parent

def get_parent_dir():
    return str(get_exe_parent_dir() if is_frozen() else get_script_parent_dir())
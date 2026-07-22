import os
import subprocess as sp
import datetime as dt

from utilities.functions import get_app_path


def take(bin_path, video_path, image_format, position):
    hours = int(position/3600)
    minutes = int((position - hours*3600) / 60)
    sec = int(position - (hours*3600 + minutes*60))
    t = f"{hours:02d}:{minutes:02d}:{sec:02d}"
    file_date = str(dt.datetime.now().strftime("%y-%d-%m-%I-%M-%S%p"))
    image_path = os.path.join(get_app_path(), "Screenshots", f"screenshot-{file_date}.{image_format}")
    sp.run([bin_path, "-ss", t, "-i", video_path, "-vframes", "1", "-q:v", "2", image_path])

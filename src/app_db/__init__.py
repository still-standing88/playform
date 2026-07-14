import os

from .user_db import UserFiles
from .media_db import MediaDatabase
from utilities.functions import get_app_path, get_user_directories

current_path = get_app_path()
db_path = f"{current_path}/data/db.sqlite3"
first_launch = True if not os.path.exists(db_path) else False
user_db = UserFiles(db_path, simple_mode=True)
user_db.connect_to_database()

media_db_path = f"{current_path}/data/media.sqlite3"
media_db = MediaDatabase(media_db_path, simple_mode=False)
media_db.connect_to_database()

if first_launch:
    folders = get_user_directories()
    for folder in folders:
        user_db.add_library_folder(folder)

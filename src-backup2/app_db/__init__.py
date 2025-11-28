import os
from user_db import UserFiles
from media_db import MediaFile, MediaType, MediaDatabase
from utilities.functions import get_app_path

current_path = get_app_path()
user_db = UserFiles(f"{current_path}/data/db.sqlite3")
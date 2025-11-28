import os
from user_db import UserFiles
from media_db import MediaFile, MediaType, MediaDatabase

current_path = os.path.abspath(__file__)
user_db = UserFiles(f"{current_path}/data/db.sqlite3")
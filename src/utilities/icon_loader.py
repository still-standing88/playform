import os
from pathlib import Path
from typing import Optional
from PySide6.QtGui import QIcon, QPixmap
from utilities.functions import is_dev_mode, get_parent_dir

_icon_cache = {}

def get_assets_dir() -> Optional[str]:
    try:
        import assets_rc  # type: ignore
        return None
    except ImportError:
        if is_dev_mode():
            parent_dir = get_parent_dir()
            assets_path = os.path.join(parent_dir, "assets", "icons")
            if os.path.isdir(assets_path):
                return assets_path
        return None

def load_icon(icon_name: str) -> QIcon:
    if icon_name in _icon_cache:
        return _icon_cache[icon_name]
    
    icon = QIcon()
    assets_dir = get_assets_dir()
    
    if assets_dir is None:
        try:
            resource_path = f":/icons/{icon_name}"
            icon = QIcon(resource_path)
        except:
            pass
    else:
        icon_path = os.path.join(assets_dir, icon_name)
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
    
    _icon_cache[icon_name] = icon
    return icon

def load_pixmap(icon_name: str) -> QPixmap:
    cache_key = f"pixmap::{icon_name}"
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    assets_dir = get_assets_dir()
    
    if assets_dir is None:
        try:
            resource_path = f":/icons/{icon_name}"
            pixmap = QPixmap(resource_path)
            _icon_cache[cache_key] = pixmap
            return pixmap
        except:
            return QPixmap()
    else:
        icon_path = os.path.join(assets_dir, icon_name)
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            _icon_cache[cache_key] = pixmap
            return pixmap
    
    return QPixmap()

def get_app_icon() -> QIcon:
    return load_icon("app_icon.png")

def clear_cache():
    global _icon_cache
    _icon_cache.clear()

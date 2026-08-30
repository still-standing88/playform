import os
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap
from utilities.functions import is_dev_mode, get_parent_dir

_icon_cache = {}

# A stylesheet-styled QToolButton bypasses the style's automatic disabled
# fade, so the Disabled pixmaps have to be baked into the QIcon.
_DISABLED_SIZES = (16, 22, 24, 32, 48)
_DISABLED_OPACITY = 0.35

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

def _with_disabled_pixmaps(source: QIcon) -> QIcon:
    if source.isNull():
        return source
    # Rebuilt as a pixmap-backed QIcon: addPixmap() on the SVG icon engine
    # does not register a Disabled variant, so the Normal renderings have to
    # be re-hosted in a plain icon alongside their faded copies.
    icon = QIcon()
    for size in _DISABLED_SIZES:
        normal = source.pixmap(QSize(size, size), QIcon.Mode.Normal)
        if normal.isNull():
            continue
        icon.addPixmap(normal, QIcon.Mode.Normal, QIcon.State.Off)
        icon.addPixmap(normal, QIcon.Mode.Active, QIcon.State.Off)
        faded = QPixmap(normal.size())
        faded.fill(Qt.GlobalColor.transparent)
        painter = QPainter(faded)
        painter.setOpacity(_DISABLED_OPACITY)
        painter.drawPixmap(0, 0, normal)
        painter.end()
        icon.addPixmap(faded, QIcon.Mode.Disabled, QIcon.State.Off)
    return icon if not icon.isNull() else source

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

    icon = _with_disabled_pixmaps(icon)
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

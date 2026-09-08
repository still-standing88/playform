import os
from typing import Optional
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from utilities.functions import is_dev_mode, get_parent_dir

_icon_cache = {}

# A stylesheet-styled QToolButton bypasses the style's automatic disabled
# fade, so the Disabled pixmaps have to be baked into the QIcon.
_DISABLED_SIZES = (16, 22, 24, 32, 48)
_DISABLED_OPACITY = 0.35


def _theme_icon_color() -> QColor:
    from app_constance.styles import theme_qcolor
    return theme_qcolor("COLOR_TEXT_1")


def _tint_pixmap(source: QPixmap, color: QColor) -> QPixmap:
    tinted = QPixmap(source.size())
    tinted.fill(Qt.GlobalColor.transparent)
    painter = QPainter(tinted)
    painter.drawPixmap(0, 0, source)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), color)
    painter.end()
    return tinted

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
        source_pixmap = source.pixmap(QSize(size, size), QIcon.Mode.Normal)
        if source_pixmap.isNull():
            continue
        normal = _tint_pixmap(source_pixmap, _theme_icon_color())
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
    cache_key = f"icon::{icon_name}::{_theme_icon_color().name(QColor.NameFormat.HexArgb)}"
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]
    
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
    _icon_cache[cache_key] = icon
    return icon

def load_pixmap(icon_name: str) -> QPixmap:
    cache_key = f"pixmap::{icon_name}"
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    assets_dir = get_assets_dir()
    
    if assets_dir is None:
        try:
            resource_path = f":/icons/{icon_name}"
            pixmap = _tint_pixmap(QPixmap(resource_path), _theme_icon_color())
            _icon_cache[cache_key] = pixmap
            return pixmap
        except:
            return QPixmap()
    else:
        icon_path = os.path.join(assets_dir, icon_name)
        if os.path.exists(icon_path):
            pixmap = _tint_pixmap(QPixmap(icon_path), _theme_icon_color())
            _icon_cache[cache_key] = pixmap
            return pixmap
    
    return QPixmap()

def get_app_icon() -> QIcon:
    icon = QIcon(":/app/playform.png")
    if not icon.isNull():
        return icon
    app_path = os.path.join(get_parent_dir(), "assets", "playform.png")
    return QIcon(app_path) if os.path.exists(app_path) else QIcon()

def clear_cache():
    global _icon_cache
    _icon_cache.clear()

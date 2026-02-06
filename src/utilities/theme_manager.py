import sys
from typing import Optional
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication
from app_config import prefs

_current_theme = None

def get_system_theme():
    try:
        import qdarktheme  # type: ignore
        detected = qdarktheme.load_stylesheet("auto")
        if "dark" in detected.lower() or len(detected) > 1000:
            return "dark"
        return "light"
    except:
        if sys.platform == "win32":
            try:
                import winreg
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return "light" if value == 1 else "dark"
            except:
                pass
        return "dark"

def apply_theme(theme_name: Optional[str] = None, app: Optional[QApplication] = None) -> None:
    global _current_theme
    
    if app is None:
        app_instance = QApplication.instance()
        if app_instance is None:
            return
        app = app_instance  # type: ignore
    
    if theme_name is None:
        theme_name = prefs.prefs.get("color_theme", "system")
    
    if theme_name == "system":
        theme_name = get_system_theme()
    
    _current_theme = theme_name
    
    try:
        import qdarktheme  # type: ignore
        qdarktheme.setup_theme(theme_name)
    except ImportError:
        from app_constance.styles import get_dark_palette, get_light_palette
        
        if theme_name == "dark":
            palette = get_dark_palette()
        else:
            palette = get_light_palette()
        
        if isinstance(app, QApplication):
            app.setPalette(palette)

def get_current_theme():
    global _current_theme
    if _current_theme is None:
        theme = prefs.prefs.get("color_theme", "system")
        if theme == "system":
            return get_system_theme()
        return theme
    return _current_theme

def setup_theme(app):
    theme = prefs.prefs.get("color_theme", "system")
    apply_theme(theme, app)

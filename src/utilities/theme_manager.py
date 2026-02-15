import sys
from typing import Optional
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication
from app_config import prefs

import qdarkstyle
from qdarkstyle.dark.palette import DarkPalette
from qdarkstyle.light.palette import LightPalette

_current_theme = None


def get_system_theme() -> str:
    """Detect system theme across Windows, macOS, and Linux."""
    
    if sys.platform == "win32":
        # Windows 10/11
        try:
            import winreg
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if value == 1 else "dark"
        except Exception:
            return "dark"
    
    elif sys.platform == "darwin":
        # macOS
        try:
            import subprocess
            result = subprocess.run(
                ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                capture_output=True,
                text=True
            )
            return "dark" if result.returncode == 0 else "light"
        except Exception:
            return "dark"
    
    else:
        # Linux - try common desktop environments
        try:
            import subprocess
            result = subprocess.run(
                ['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'],
                capture_output=True,
                text=True
            )
            theme_output = result.stdout.strip().lower()
            if 'dark' in theme_output:
                return "dark"
            return "light"
        except Exception:
            pass
        
        try:
            import configparser
            import os
            kde_config = os.path.expanduser('~/.config/kdeglobals')
            if os.path.exists(kde_config):
                config = configparser.ConfigParser()
                config.read(kde_config)
                color_scheme = config.get('General', 'ColorScheme', fallback='').lower()
                if 'dark' in color_scheme:
                    return "dark"
                return "light"
        except Exception:
            pass
        
        return "dark"


def apply_theme(theme_name: Optional[str] = None, app: Optional[QApplication] = None) -> None:
    """Apply theme and force all widgets to repaint."""
    global _current_theme
    
    if app is None:
        app_instance = QApplication.instance()
        if app_instance is None:
            return
        app = app_instance
    
    if theme_name is None:
        theme_name = prefs.prefs.get("color_theme", "system")
    
    if theme_name == "system":
        theme_name = get_system_theme()
    
    _current_theme = theme_name
    
    # Load QDarkStyle stylesheet
    if theme_name == "dark":
        stylesheet = qdarkstyle.load_stylesheet(palette=DarkPalette)
    elif theme_name == "light":
        stylesheet = qdarkstyle.load_stylesheet(palette=LightPalette)
    else:
        stylesheet = ""
    
    # Apply stylesheet to application
    app.setStyleSheet(stylesheet)
    
    # Force all widgets to reapply styles
    _repolish_all_widgets(app)


def _repolish_all_widgets(app: QApplication) -> None:
    """Force all widgets to reapply their styles (polish/unpolish cycle).
    
    The polish/unpolish cycle is the official Qt mechanism for forcing widgets
    to reapply their styles. This is sufficient for dynamic theme changes and
    does not require calling update() separately. See Qt documentation for
    QStyle::polish() and QStyle::unpolish().
    """
    for widget in app.allWidgets():
        widget.style().unpolish(widget)
        widget.style().polish(widget)


def get_current_theme() -> str:
    """Get the currently active theme."""
    global _current_theme
    if _current_theme is None:
        theme = prefs.prefs.get("color_theme", "system")
        if theme == "system":
            return get_system_theme()
        return theme
    return _current_theme


def setup_theme(app: QApplication) -> None:
    """Initial theme setup on app start."""
    theme = prefs.prefs.get("color_theme", "system")
    apply_theme(theme, app)
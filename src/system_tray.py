from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QAction
from utilities.icon_loader import load_icon
import os

class SystemTrayIcon:
    def __init__(self, window):
        self.window = window
        self.tray_icon = None
        self.show_hide_action = None
        self._init_tray()
    
    def _init_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        self.tray_icon = QSystemTrayIcon(self.window)
        
        icon = load_icon("PlayForm.png")
        if icon.isNull():
            icon = self.window.style().standardIcon(self.window.style().StandardPixmap.SP_MediaPlay)
        self.tray_icon.setIcon(icon)

        app_name = os.environ.get("APP_NAME", "PlayForm")
        self.tray_icon.setToolTip(app_name)
        self.app_name = app_name
        
        tray_menu = QMenu()
        
        self.show_hide_action = QAction(_("Hide"), self.window)
        self.show_hide_action.triggered.connect(self.toggle_window_visibility)
        tray_menu.addAction(self.show_hide_action)
        
        tray_menu.addSeparator()
        
        exit_action = QAction(_("Exit"), self.window)
        exit_action.triggered.connect(self.window.close_application)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
    
    def hide_window_to_tray(self):
        if self.tray_icon:
            self.window.hide()
            if self.show_hide_action:
                self.show_hide_action.setText(_("Show"))
            if hasattr(self.tray_icon, 'showMessage'):
                self.tray_icon.showMessage(
                    self.app_name,
                    _("Application was minimized to tray"),
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
        else:
            self.window.showMinimized()
    
    def toggle_window_visibility(self):
        if self.window.isVisible() and not self.window.isMinimized():
            self.window.hide()
            if self.show_hide_action:
                self.show_hide_action.setText(_("Show"))
        else:
            self.window.show()
            self.window.raise_()
            self.window.activateWindow()
            if self.show_hide_action:
                self.show_hide_action.setText(_("Hide"))
    
    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window_visibility()
    
    def is_available(self):
        return self.tray_icon is not None
    
    def cleanup(self):
        if self.tray_icon:
            self.tray_icon.hide()
            self.tray_icon.deleteLater()
            self.tray_icon = None

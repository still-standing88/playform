"""Tray-balloon notifications for finished downloads.

Gated by the "download_notify_finished" pref (Downloads tab in
Preferences). Posts through the globally registered tray icon
(QApplication.instance()._tray_icon, same channel as Batch Converter /
Capture notify-on-finish); silently does nothing when no system tray is
available.
"""

from PySide6.QtWidgets import QApplication, QSystemTrayIcon


def notify_download_finished(title: str, succeeded: bool, error: str = "") -> None:
    from app_config import prefs

    if not prefs.prefs.get("download_notify_finished", True):
        return

    tray_icon = getattr(QApplication.instance(), "_tray_icon", None)
    if tray_icon is None or not hasattr(tray_icon, "showMessage"):
        return

    if succeeded:
        summary = _("Download Finished")
        body = _("{title} has finished downloading.").format(title=title)
        icon = QSystemTrayIcon.MessageIcon.Information
    else:
        summary = _("Download Failed")
        body = _("{title} did not finish downloading{error}.").format(
            title=title, error=_(": {detail}").format(detail=error) if error else "")
        icon = QSystemTrayIcon.MessageIcon.Warning

    tray_icon.showMessage(summary, body, icon, 5000)

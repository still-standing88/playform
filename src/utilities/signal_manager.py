from PySide6.QtCore import QObject, Signal

from utilities.announcement_categories import AnnouncementCategory


class SignalManager(QObject):
    statusbar_message = Signal(str)
    media_info_message = Signal(str)
    # Same text as statusbar_message, plus a category id (AnnouncementCategory.value)
    # -- lets the speech-output path (main_window._update_status_message)
    # filter what gets spoken without affecting what the status bar shows.
    statusbar_message_categorized = Signal(str, str)

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            super().__init__()
            self._initialized = True

    def announce(self, text: str, category: AnnouncementCategory = AnnouncementCategory.GENERAL):
        """Preferred way to post a status message that may also be spoken.
        Always updates the status bar (statusbar_message, unchanged
        behavior); statusbar_message_categorized additionally carries the
        category so it can be filtered before reaching speech output."""
        self.statusbar_message.emit(text)
        self.statusbar_message_categorized.emit(text, category.value)


signal_manager = SignalManager()

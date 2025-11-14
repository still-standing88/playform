from PySide6.QtCore import QObject, Signal


class SignalManager(QObject):
    statusbar_message = Signal(str)
    media_info_message = Signal(str)

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            super().__init__()
            self._initialized = True


signal_manager = SignalManager()

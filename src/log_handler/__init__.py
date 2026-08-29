from .manager import LoggingSetup
from .qt_messages import install_qt_message_handler

def get_logger():
    return LoggingSetup.get_logger()

from .manager import LoggingSetup

def get_logger():
    return LoggingSetup.get_logger()

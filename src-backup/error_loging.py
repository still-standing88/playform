import logging
import sys
import traceback


def exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.error(f"Uncaught exception:\n{tb_str}")

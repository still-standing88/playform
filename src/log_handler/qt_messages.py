"""Routes Qt's own qDebug/qWarning/qCritical output into the app logger.

Qt writes these through its C++ message handler straight to the C-level
stderr, so sys.stderr redirection (LoggingStreamRedirect) never sees them:
in a dev run they bypass the debug console, and in a frozen windowed build
they are discarded outright. Installing a handler puts them in errors.log
with everything else.

_MUTED covers warnings from Qt plugins that are both unfixable from here and
emitted in bulk. Qt's SAPI plugin parses each voice's Language attribute as a
single hex LCID, but some installed voices (Classic Mac / eSpeak-style
tokens) report a multi-value list like "409;9", which fails to parse and logs
once per voice per enumeration. Those voices still work -- they fall back to
the system locale -- so the warning is pure noise.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QtMsgType, qInstallMessageHandler

_MUTED = (
    "Could not convert language attribute to LCID",
)

_LEVELS = {
    QtMsgType.QtDebugMsg: logging.DEBUG,
    QtMsgType.QtInfoMsg: logging.INFO,
    QtMsgType.QtWarningMsg: logging.WARNING,
    QtMsgType.QtCriticalMsg: logging.ERROR,
    QtMsgType.QtFatalMsg: logging.CRITICAL,
}


def _handler(msg_type, context, message):
    text = (message or "").strip()
    if not text or any(muted in text for muted in _MUTED):
        return
    logging.getLogger("Qt").log(_LEVELS.get(msg_type, logging.INFO), text)


def install_qt_message_handler():
    qInstallMessageHandler(_handler)

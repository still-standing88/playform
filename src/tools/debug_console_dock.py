from __future__ import annotations

import sys
from gettext import gettext as _

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTextEdit,
    QDockWidget,
    QLabel,
)


from log_handler.manager import LoggingSetup
from log_handler.handlers import LoggingStreamRedirect


class DebugConsoleDock(QDockWidget):

    def __init__(self, parent=None):
        super().__init__(_("Debug Console"), parent)
        
        self.setObjectName("debugConsoleDock")

        container = QWidget()
        container.setObjectName("debugConsoleContainer")
        self.setWidget(container)
        layout = QVBoxLayout(container)
        info = QLabel(_("Console output. Tab key won't insert tabs inside editor."))
        info.setObjectName("consoleInfoLabel")
        layout.addWidget(info)


        self.console = QTextEdit()
        self.console.setObjectName("consoleTextEdit")
        self.console.setReadOnly(True)
        self.console.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.console.setTabChangesFocus(True)
        self.console.setAccessibleName(_("Console Output"))
        self.console.setAccessibleDescription(_("Read-only console output viewer"))
        layout.addWidget(self.console, 1)


        # Pass console widget to LoggingSetup so logger messages appear in console
        self.logging_setup = LoggingSetup(console_widget=self.console)


        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        self.stdout_redirect = LoggingStreamRedirect(self.console, self.original_stdout, self.logging_setup.logger, is_stderr=False)
        self.stderr_redirect = LoggingStreamRedirect(self.console, self.original_stderr, self.logging_setup.logger, is_stderr=True)

        sys.stdout = self.stdout_redirect
        sys.stderr = self.stderr_redirect

        print(_("Debug console initialized."))



        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable)



    def closeEvent(self, event):  # type: ignore[override]

        try:
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
        except Exception:
            pass
        try:
            self.logging_setup.cleanup()
        except Exception:
            pass
        super().closeEvent(event)

from PySide6.QtWidgets import QApplication


class FocusNavigationManager:
    """F6/Shift+F6 pane-cycling logic extracted from MainWindow. Reads/writes
    MainWindow's pre-declared focusable_widgets/current_focus_index."""

    def __init__(self, main_window):
        self.main_window = main_window

    def _current_focus_list_index(self) -> int:
        mw = self.main_window
        # current_focus_index only remembers where F6/Shift+F6 last put focus;
        # it goes stale the moment the user clicks or Tabs somewhere else
        # (e.g. into a floated dock), so derive the real position from
        # QApplication's actual focus widget instead of trusting the counter.
        focus_widget = QApplication.focusWidget()
        if focus_widget is None:
            return -1
        for i, widget in enumerate(mw.focusable_widgets):
            if widget is focus_widget or widget.isAncestorOf(focus_widget):
                return i
        return -1

    def focus_next_widget(self):
        mw = self.main_window
        mw.dock_manager.update_focusable_widgets()
        if not mw.focusable_widgets:
            return

        current = self._current_focus_list_index()
        mw.current_focus_index = (current + 1) % len(mw.focusable_widgets)
        self._focus_navigation_target(mw.focusable_widgets[mw.current_focus_index])

    def focus_previous_widget(self):
        mw = self.main_window
        mw.dock_manager.update_focusable_widgets()
        if not mw.focusable_widgets:
            return

        current = self._current_focus_list_index()
        mw.current_focus_index = (current - 1) % len(mw.focusable_widgets)
        self._focus_navigation_target(mw.focusable_widgets[mw.current_focus_index])

    def _focus_navigation_target(self, widget):
        mw = self.main_window
        if widget is None:
            return

        # Always activate the target's own window, even when it's this
        # MainWindow - returning from a floated pane back to MainWindow is
        # itself one cycle step, and needs the same activation as moving
        # into a floated pane, or MainWindow never regains OS focus even
        # though Qt-internal focus moved.
        target_window = widget.window()
        if target_window is not None:
            target_window.activateWindow()
            target_window.raise_()
            # Window activation isn't always synchronous - without pumping
            # the event loop here, the immediately-following setFocus() calls
            # below can land before the window manager actually hands over
            # activation, leaving QApplication.focusWidget() empty.
            QApplication.processEvents()

        if widget is mw.toolbar or widget is getattr(mw, 'panels_toolbar', None):
            widget.setFocus()
            toolbar_actions = [action for action in widget.actions() if action.isVisible() and not action.isSeparator()]
            if toolbar_actions:
                toolbar_widget = widget.widgetForAction(toolbar_actions[0])
                if toolbar_widget is not None:
                    toolbar_widget.setFocus()
            return

        if widget is mw.status_bar:
            widget.setFocus()
            if mw.show_tool_button.isVisible():
                mw.show_tool_button.setFocus()
            elif mw.show_downloader_button.isVisible():
                mw.show_downloader_button.setFocus()
            elif mw.show_catalog_button.isVisible():
                mw.show_catalog_button.setFocus()
            elif mw.media_info_label.isVisible():
                mw.media_info_label.setFocus()
            else:
                mw.status_label.setFocus()
            return

        widget.setFocus()

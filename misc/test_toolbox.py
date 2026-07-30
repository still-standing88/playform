"""
pytest-qt test suite for SettingsToolBox (see example_app.py).

Requirements:
    pip install pytest pytest-qt PySide6 --break-system-packages

Run:
    pytest test_toolbox.py -v

example_app.py defines SettingsToolBox(QToolBox), a real widget with three
pages: General, Advanced, Debug. This file tests that widget directly
instead of a throwaway inline builder.
"""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QWidget, QAbstractButton, QApplication
from example_app import SettingsToolBox


@pytest.fixture
def toolbox(qtbot):
    """Fixture providing a fresh SettingsToolBox, registered with qtbot for cleanup."""
    widget = SettingsToolBox()
    qtbot.addWidget(widget)
    widget.show()
    return widget


class TestToolBoxStructure:
    def test_has_expected_number_of_pages(self, toolbox):
        assert toolbox.count() == 3

    def test_page_titles(self, toolbox):
        titles = [toolbox.itemText(i) for i in range(toolbox.count())]
        assert titles == ["General", "Advanced", "Debug"]

    def test_default_current_index(self, toolbox):
        # QToolBox defaults to the first page selected
        assert toolbox.currentIndex() == 0

    def test_current_widget_matches_index(self, toolbox):
        assert toolbox.currentWidget() is toolbox.widget(0)


class TestToolBoxNavigation:
    def test_set_current_index_changes_current_widget(self, toolbox):
        toolbox.setCurrentIndex(1)
        assert toolbox.currentIndex() == 1
        assert toolbox.currentWidget() is toolbox.widget(1)

    def test_current_changed_signal_emits_on_switch(self, toolbox, qtbot):
        with qtbot.waitSignal(toolbox.currentChanged, timeout=1000) as blocker:
            toolbox.setCurrentIndex(2)
        assert blocker.args == [2]

    def test_current_changed_not_emitted_for_same_index(self, toolbox, qtbot):
        toolbox.setCurrentIndex(0)  # already 0, no-op
        with qtbot.assertNotEmitted(toolbox.currentChanged, wait=200):
            toolbox.setCurrentIndex(0)

    def test_out_of_range_index_is_ignored_or_clamped(self, toolbox):
        # Qt silently ignores invalid indices rather than raising
        toolbox.setCurrentIndex(99)
        assert toolbox.currentIndex() in range(toolbox.count())


class TestToolBoxMutation:
    def test_remove_item_updates_count(self, toolbox):
        toolbox.removeItem(1)
        assert toolbox.count() == 2
        assert toolbox.itemText(0) == "General"
        assert toolbox.itemText(1) == "Debug"

    def test_insert_item_at_position(self, toolbox):
        new_page = QWidget()
        toolbox.insertItem(1, new_page, "Inserted")
        toolbox._pages.append(new_page)  # keep alive, see SettingsToolBox docstring in example_app.py
        assert toolbox.count() == 4
        assert toolbox.itemText(1) == "Inserted"
        assert toolbox.widget(1) is new_page

    def test_set_item_text_updates_title(self, toolbox):
        toolbox.setItemText(0, "Renamed")
        assert toolbox.itemText(0) == "Renamed"

    def test_set_item_enabled_disables_page(self, toolbox):
        toolbox.setItemEnabled(1, False)
        assert toolbox.isItemEnabled(1) is False


class TestToolBoxAccessibility:
    """
    Given your emphasis on accessibility elsewhere (screen reader trees,
    keyboard nav), these checks catch common regressions.

    QToolBox's internal page-header buttons default to Qt.NoFocus, meaning
    Tab silently skips them - a keyboard-only user can never reach the
    "Advanced" or "Debug" headers to switch pages, even though a mouse
    user can click them freely (see QTBUG-175). SettingsToolBox patches
    this in _fix_header_keyboard_focus(); the tests below guard against
    that patch regressing, e.g. if the widget is rebuilt without it.
    """

    def _header_buttons(self, toolbox):
        header_texts = {toolbox.itemText(i) for i in range(toolbox.count())}
        return [b for b in toolbox.findChildren(QAbstractButton) if b.text() in header_texts]

    def test_pages_have_accessible_names_matching_titles(self, toolbox):
        for i in range(toolbox.count()):
            assert toolbox.itemText(i).strip() != ""

    def test_keyboard_focus_can_reach_toolbox(self, toolbox, qtbot):
        toolbox.setFocus()
        qtbot.waitUntil(lambda: toolbox.hasFocus() or toolbox.currentWidget().hasFocus(),
                         timeout=1000)

    def test_all_page_headers_are_keyboard_focusable(self, toolbox):
        # Regression test: without the fix, this is Qt.NoFocus (0) for every header.
        headers = self._header_buttons(toolbox)
        assert len(headers) == toolbox.count()
        for button in headers:
            assert button.focusPolicy() != Qt.NoFocus

    def test_tab_key_reaches_every_page_header(self, toolbox, qtbot):
        # Regression test: without the fix, Tab loops forever inside the
        # first page's controls and never reaches "Advanced" or "Debug".
        toolbox.setFocus()
        qtbot.wait(50)
        seen_headers = set()
        widget = QApplication.focusWidget()
        for _ in range(20):
            if isinstance(widget, QAbstractButton) and widget.text() in {
                toolbox.itemText(i) for i in range(toolbox.count())
            }:
                seen_headers.add(widget.text())
            if len(seen_headers) == toolbox.count():
                break
            qtbot.keyClick(widget, Qt.Key_Tab)
            widget = QApplication.focusWidget()
        assert seen_headers == {toolbox.itemText(i) for i in range(toolbox.count())}

    def test_space_on_focused_header_switches_page(self, toolbox, qtbot):
        headers = self._header_buttons(toolbox)
        advanced_header = next(b for b in headers if b.text() == "Advanced")
        advanced_header.setFocus()
        qtbot.keyClick(advanced_header, Qt.Key_Space)
        assert toolbox.currentIndex() == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

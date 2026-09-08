import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from utilities.i18n import install_translation

install_translation()

from app_constance.styles import get_theme_palette
from gui_controls.toggle_button import ToggleButton
from media_providers.radio.radio_filter_widget import RadioFilterWidget
from player.widgets.chapters_widget import ChaptersWidget
from utilities.icon_loader import load_icon
from utilities.theme_manager import apply_theme


def icon_center(icon_name: str) -> str:
    image = load_icon(icon_name).pixmap(22, 22).toImage()
    return image.pixelColor(11, 11).name()


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    toggle = ToggleButton("Toggle")
    chapters = ChaptersWidget()
    radio = RadioFilterWidget()
    widgets = (toggle, chapters, radio)

    apply_theme("dark", app)
    dark = get_theme_palette()
    dark_icon = icon_center("play.svg")
    dark_styles = (
        toggle.styleSheet(),
        chapters.chapters_list.styleSheet(),
        radio.search_input.styleSheet(),
    )

    apply_theme("light", app)
    light = get_theme_palette()
    light_icon = icon_center("play.svg")
    light_styles = (
        toggle.styleSheet(),
        chapters.chapters_list.styleSheet(),
        radio.search_input.styleSheet(),
    )

    assert dark.ID == "dark" and light.ID == "light"
    assert dark_icon == dark.COLOR_TEXT_1.lower()
    assert light_icon == light.COLOR_TEXT_1.lower()
    assert dark_icon != light_icon
    assert all(before != after for before, after in zip(dark_styles, light_styles))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
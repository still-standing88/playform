from PySide6.QtGui import QColor
from qdarkstyle.dark.palette import DarkPalette
from qdarkstyle.light.palette import LightPalette


def get_theme_palette(theme_name: str | None = None):
    if theme_name is None:
        from utilities.theme_manager import get_current_theme
        theme_name = get_current_theme()
    return LightPalette if theme_name == "light" else DarkPalette


def theme_color(name: str, theme_name: str | None = None) -> str:
    return getattr(get_theme_palette(theme_name), name)


def theme_qcolor(name: str, alpha: int | None = None, theme_name: str | None = None) -> QColor:
    color = QColor(theme_color(name, theme_name))
    if alpha is not None:
        color.setAlpha(alpha)
    return color


def button_style() -> str:
    palette = get_theme_palette()
    return f"""
        QPushButton {{
            background-color: {palette.COLOR_ACCENT_3};
            border: 1px solid {palette.COLOR_ACCENT_4};
            border-radius: 18px;
            color: {palette.COLOR_TEXT_1};
            font-weight: bold;
        }}
        QPushButton:hover {{ background-color: {palette.COLOR_ACCENT_4}; }}
        QPushButton:pressed {{ background-color: {palette.COLOR_ACCENT_2}; }}
        QPushButton:disabled {{
            background-color: {palette.COLOR_BACKGROUND_3};
            border-color: {palette.COLOR_BACKGROUND_4};
            color: {palette.COLOR_DISABLED};
        }}
    """


def toolbutton_style() -> str:
    palette = get_theme_palette()
    return f"""
        QToolButton {{
            background-color: transparent;
            border: 2px solid transparent;
            color: {palette.COLOR_TEXT_1};
            font-weight: bold;
            padding: 2px;
        }}
        QToolButton:hover {{
            background-color: {palette.COLOR_ACCENT_1};
            border-radius: {palette.SIZE_BORDER_RADIUS};
        }}
        QToolButton:focus {{
            background-color: {palette.COLOR_ACCENT_1};
            border: 2px solid {palette.COLOR_ACCENT_4};
            border-radius: {palette.SIZE_BORDER_RADIUS};
        }}
        QToolButton:pressed {{ background-color: {palette.COLOR_ACCENT_2}; }}
        QToolButton:disabled {{ color: {palette.COLOR_DISABLED}; }}
    """


def slider_style() -> str:
    palette = get_theme_palette()
    return f"""
        QSlider::groove:horizontal {{
            border: 1px solid {palette.COLOR_BACKGROUND_4};
            background: {palette.COLOR_BACKGROUND_2};
            height: 8px;
            border-radius: 4px;
        }}
        QSlider::sub-page:horizontal {{
            background: {palette.COLOR_ACCENT_3};
            border: 1px solid {palette.COLOR_ACCENT_4};
            height: 8px;
            border-radius: 4px;
        }}
        QSlider::add-page:horizontal {{
            background: {palette.COLOR_BACKGROUND_2};
            border: 1px solid {palette.COLOR_BACKGROUND_4};
            height: 8px;
            border-radius: 4px;
        }}
        QSlider::handle:horizontal {{
            background: {palette.COLOR_ACCENT_4};
            border: 2px solid {palette.COLOR_ACCENT_3};
            width: 18px;
            margin: -2px 0;
            border-radius: 9px;
        }}
        QSlider::handle:horizontal:hover {{ background: {palette.COLOR_ACCENT_5}; }}
    """


def controls_separator_style() -> str:
    palette = get_theme_palette()
    return f"QFrame {{ background-color: {palette.COLOR_BACKGROUND_5}; border: none; }}"


PLAYER_CONTROLS_STYLE = "background-color: transparent;"
TIME_LABEL_STYLE = "QLabel { font-weight: bold; }"
TRACK_LABEL_STYLE = ""
TITLE_LABEL_STYLE = "font-weight: bold;"


def video_placeholder_style() -> str:
    palette = get_theme_palette()
    return f"""
        QLabel {{
            background-color: {palette.COLOR_BACKGROUND_2};
            color: {palette.COLOR_TEXT_1};
            font-weight: bold;
            border: 2px dashed {palette.COLOR_BACKGROUND_5};
        }}
    """


VIDEO_LOADING_STYLE = """
    QLabel {
        background-color: rgba(0, 0, 0, 180);
        color: white;
        font-weight: bold;
        border-radius: 10px;
        padding: 20px;
    }
"""


def subtitles_list_style() -> str:
    palette = get_theme_palette()
    return f"""
        QListWidget {{
            background-color: {palette.COLOR_BACKGROUND_1};
            color: {palette.COLOR_TEXT_1};
            border: 1px solid {palette.COLOR_BACKGROUND_4};
            border-radius: {palette.SIZE_BORDER_RADIUS};
            padding: 5px;
        }}
        QListWidget::item {{
            padding: 5px;
            border-bottom: 1px solid {palette.COLOR_BACKGROUND_3};
        }}
        QListWidget::item:selected {{
            background-color: {palette.COLOR_ACCENT_2};
            color: {palette.COLOR_TEXT_1};
        }}
    """


def player_widget_style() -> str:
    palette = get_theme_palette()
    return f"""
        PlayerWidget {{
            background-color: {palette.COLOR_BACKGROUND_1};
            border: 1px solid {palette.COLOR_BACKGROUND_4};
            border-radius: 8px;
        }}
    """


def get_repeat_button_active_style(base_style: str) -> str:
    palette = get_theme_palette()
    return base_style + f"QToolButton {{ background-color: {palette.COLOR_ACCENT_3}; }}"


def radio_group_box_style() -> str:
    palette = get_theme_palette()
    return f"""
        QGroupBox {{
            font-weight: bold;
            border: 1px solid {palette.COLOR_BACKGROUND_4};
            border-radius: {palette.SIZE_BORDER_RADIUS};
            margin-top: 10px;
            padding-top: 10px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }}
    """


def radio_tree_style() -> str:
    palette = get_theme_palette()
    return f"""
        QTreeWidget {{ alternate-row-colors: true; }}
        QTreeWidget::item {{ padding: 5px; }}
        QTreeWidget::item:selected {{
            background-color: {palette.COLOR_ACCENT_2};
            color: {palette.COLOR_TEXT_1};
        }}
        QTreeWidget::item:hover {{ background-color: {palette.COLOR_BACKGROUND_3}; }}
    """


def radio_combo_style() -> str:
    palette = get_theme_palette()
    return f"""
        QComboBox {{
            padding: 5px;
            border: 1px solid {palette.COLOR_BACKGROUND_4};
            border-radius: 3px;
        }}
        QComboBox:focus {{ border-color: {palette.COLOR_ACCENT_4}; }}
        QComboBox::drop-down {{ border: none; }}
    """


def radio_line_edit_style() -> str:
    palette = get_theme_palette()
    return f"""
        QLineEdit {{
            padding: 5px;
            border: 1px solid {palette.COLOR_BACKGROUND_4};
            border-radius: 3px;
            background-color: {palette.COLOR_BACKGROUND_1};
            color: {palette.COLOR_TEXT_1};
        }}
        QLineEdit:focus {{ border-color: {palette.COLOR_ACCENT_4}; }}
    """


def radio_button_style() -> str:
    palette = get_theme_palette()
    return f"""
        QPushButton {{
            background-color: {palette.COLOR_ACCENT_3};
            border: 1px solid {palette.COLOR_ACCENT_4};
            border-radius: {palette.SIZE_BORDER_RADIUS};
            color: {palette.COLOR_TEXT_1};
            padding: 6px 12px;
            font-weight: bold;
        }}
        QPushButton:hover {{ background-color: {palette.COLOR_ACCENT_4}; }}
        QPushButton:pressed {{ background-color: {palette.COLOR_ACCENT_2}; }}
        QPushButton:disabled {{
            background-color: {palette.COLOR_BACKGROUND_3};
            border-color: {palette.COLOR_BACKGROUND_4};
            color: {palette.COLOR_DISABLED};
        }}
    """


from PySide6.QtGui import QColor, QPalette

COLORS = {
    'background_dark': QColor("#1e1e1e"),
    'progress_blue': QColor("#4e9cff"),
    'progress_blue_alpha': QColor("#4e9cff80"),
    'progress_orange_alpha': QColor("#ff9f4080"),
    'marker_yellow_alpha': QColor("#ffff0080"),
    'white': QColor("#ffffff"),
    'white_alpha': QColor("#ffffff80"),
    'black': QColor(0, 0, 0),
    'red': QColor("red"),
    'orange': QColor("orange"),
    'lightgray': QColor("lightgray"),
    'video_bg': QColor("#2c3e50"),
    'video_border': QColor("#34495e"),
    'loading_bg_alpha': QColor("rgba(0, 0, 0, 180)"),
    'subtitle_bg': QColor("#f8f9fa"),
    'subtitle_border': QColor("#dee2e6"),
    'subtitle_item_border': QColor("#e9ecef"),
    'subtitle_selected': QColor("#007bff"),
    'button_primary': "#3498db",
    'button_hover': "#2980b9",
    'button_pressed': "#21618c",
    'button_disabled': "#bdc3c7",
    'button_repeat_active': "#e74c3c",
    'label_text': "#2c3e50",
    'track_label_text': "#34495e",
    'player_bg': "#ecf0f1",
    'player_border': "#bdc3c7",
    'slider_groove_border': "#bbb",
    'slider_sub_page_border': "#777",
}

APP_PALETTE_COLORS = {
    'window': QColor(30, 30, 30),
    'window_text': QColor(255, 255, 255),
    'base': QColor(42, 42, 42),
    'alternate_base': QColor(66, 66, 66),
    'tooltip_base': QColor(50, 50, 50),
    'tooltip_text': QColor(220, 220, 220),
    'text': QColor(255, 255, 255),
    'button': QColor(80, 80, 80),
    'button_text': QColor(255, 255, 255),
    'disabled_text': QColor(120, 120, 120),
    'link': QColor(42, 130, 218),
    'highlight': QColor(42, 130, 218),
    'highlighted_text': QColor(0, 0, 0),
}

PLAYER_CONTROLS_STYLE = "background-color: transparent;"

BUTTON_STYLE = f"""
    QPushButton {{
        background-color: {COLORS['button_primary']}; border: none; border-radius: 20px;
        color: white; font-size: 16px; font-weight: bold;
    }}
    QPushButton:hover {{ background-color: {COLORS['button_hover']}; }}
    QPushButton:pressed {{ background-color: {COLORS['button_pressed']}; }}
    QPushButton:disabled {{ background-color: {COLORS['button_disabled']}; }}
"""

SLIDER_STYLE = f"""
    QSlider::groove:horizontal {{ border: 1px solid {COLORS['slider_groove_border']}; background: white; height: 8px; border-radius: 4px; }}
    QSlider::sub-page:horizontal {{ background: {COLORS['button_primary']}; border: 1px solid {COLORS['slider_sub_page_border']}; height: 8px; border-radius: 4px; }}
    QSlider::add-page:horizontal {{ background: #fff; border: 1px solid {COLORS['slider_sub_page_border']}; height: 8px; border-radius: 4px; }}
    QSlider::handle:horizontal {{ background: {COLORS['button_primary']}; border: 2px solid {COLORS['slider_sub_page_border']}; width: 18px; margin: -2px 0; border-radius: 9px; }}
    QSlider::handle:horizontal:hover {{ background: {COLORS['button_hover']}; }}
"""

TIME_LABEL_STYLE = f"QLabel {{ color: {COLORS['label_text']}; font-weight: bold; }}"

TRACK_LABEL_STYLE = f"QLabel {{ color: {COLORS['track_label_text']}; font-size: 14px; }}"

VIDEO_PLACEHOLDER_STYLE = f"""
    QLabel {{
        background-color: {COLORS['video_bg']};
        color: white;
        font-size: 24px;
        font-weight: bold;
        border: 2px dashed {COLORS['video_border']};
    }}
"""

VIDEO_LOADING_STYLE = """
    QLabel {
        background-color: rgba(0, 0, 0, 180);
        color: white;
        font-size: 18px;
        font-weight: bold;
        border-radius: 10px;
        padding: 20px;
    }
"""

SUBTITLES_LIST_STYLE = f"""
    QListWidget {{
        background-color: {COLORS['subtitle_bg']};
        border: 1px solid {COLORS['subtitle_border']};
        border-radius: 4px;
        padding: 5px;
    }}
    QListWidget::item {{
        padding: 5px;
        border-bottom: 1px solid {COLORS['subtitle_item_border']};
    }}
    QListWidget::item:selected {{
        background-color: {COLORS['subtitle_selected']};
        color: white;
    }}
"""

PLAYER_WIDGET_STYLE = f"""
    PlayerWidget {{ background-color: {COLORS['player_bg']}; border: 1px solid {COLORS['player_border']}; border-radius: 8px; }}
"""

TITLE_LABEL_STYLE = "font-weight: bold; font-size: 14px;"

SECTION_LABEL_STYLE = "font-weight: bold; font-size: 14px;"

def get_repeat_button_active_style(base_style):
    return base_style + f"QPushButton {{ background-color: {COLORS['button_repeat_active']}; }}"

RADIO_GROUP_BOX_STYLE = """
    QGroupBox {
        font-weight: bold;
        border: 2px solid #555;
        border-radius: 5px;
        margin-top: 10px;
        padding-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }
"""

RADIO_TREE_STYLE = """
    QTreeWidget {
        alternate-row-colors: true;
        selection-background-color: #2980b9;
    }
    QTreeWidget::item {
        padding: 5px;
    }
    QTreeWidget::item:hover {
        background-color: #34495e;
    }
"""

RADIO_COMBO_STYLE = """
    QComboBox {
        padding: 5px;
        border: 1px solid #555;
        border-radius: 3px;
    }
    QComboBox::drop-down {
        border: none;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 6px solid #aaa;
        margin-right: 5px;
    }
"""

RADIO_LINE_EDIT_STYLE = """
    QLineEdit {
        padding: 5px;
        border: 1px solid #555;
        border-radius: 3px;
        background-color: #2a2a2a;
    }
    QLineEdit:focus {
        border: 1px solid #2980b9;
    }
"""

RADIO_BUTTON_STYLE = """
    QPushButton {
        background-color: #3498db;
        border: none;
        border-radius: 4px;
        color: white;
        padding: 6px 12px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #2980b9;
    }
    QPushButton:pressed {
        background-color: #21618c;
    }
    QPushButton:disabled {
        background-color: #7f8c8d;
        color: #bdc3c7;
    }
"""

def get_dark_palette():
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, APP_PALETTE_COLORS['window'])
    dark_palette.setColor(QPalette.ColorRole.WindowText, APP_PALETTE_COLORS['window_text'])
    dark_palette.setColor(QPalette.ColorRole.Base, APP_PALETTE_COLORS['base'])
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, APP_PALETTE_COLORS['alternate_base'])
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, APP_PALETTE_COLORS['tooltip_base'])
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, APP_PALETTE_COLORS['tooltip_text'])
    dark_palette.setColor(QPalette.ColorRole.Text, APP_PALETTE_COLORS['text'])
    dark_palette.setColor(QPalette.ColorRole.Button, APP_PALETTE_COLORS['button'])
    dark_palette.setColor(QPalette.ColorRole.ButtonText, APP_PALETTE_COLORS['button_text'])
    dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, APP_PALETTE_COLORS['disabled_text'])
    dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, APP_PALETTE_COLORS['disabled_text'])
    dark_palette.setColor(QPalette.ColorRole.Link, APP_PALETTE_COLORS['link'])
    dark_palette.setColor(QPalette.ColorRole.Highlight, APP_PALETTE_COLORS['highlight'])
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, APP_PALETTE_COLORS['highlighted_text'])
    return dark_palette

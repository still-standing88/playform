from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QMenu

from app_constance.misc import video_aspect_ratios, video_scales, video_speeds, video_rotations


def build_more_options_menu(controls) -> QMenu:
    """Build the Speed/Aspect Ratio/Scale/Fullscreen "More Options" menu for
    PlayerControls' more_btn, extracted out of PlayerControls.show_more_menu."""
    menu = QMenu(controls)

    speed_menu = menu.addMenu(_("Speed"))
    speed_group = QActionGroup(speed_menu)
    speed_group.setExclusive(True)
    for speed in video_speeds:
        speed_text = f"{speed}x"
        action = speed_menu.addAction(speed_text)
        action.setCheckable(True)
        if float(speed) == 1.0:
            action.setChecked(True)
        action.triggered.connect(_make_speed_handler(controls, speed))
        speed_group.addAction(action)

    aspect_menu = menu.addMenu(_("Aspect Ratio"))
    for ratio in video_aspect_ratios:
        a = aspect_menu.addAction(ratio)
        a.triggered.connect(lambda r=ratio: controls.aspectRatioChanged.emit(r))
    aspect_menu.setEnabled(controls.is_video_available)

    scale_menu = menu.addMenu(_("Scale"))
    for s in video_scales:
        a = scale_menu.addAction(s)
        a.triggered.connect(lambda v=s: controls.scaleChanged.emit(float(v)))
    scale_menu.setEnabled(controls.is_video_available)

    rotate_menu = menu.addMenu(_("Rotate"))
    rotate_group = QActionGroup(rotate_menu)
    rotate_group.setExclusive(True)
    for degrees in video_rotations:
        rotate_text = _("0° (Normal)") if degrees == 0 else f"{degrees}°"
        action = rotate_menu.addAction(rotate_text)
        action.setCheckable(True)
        if degrees == controls.video_rotate:
            action.setChecked(True)
        action.triggered.connect(_make_rotate_handler(controls, degrees))
        rotate_group.addAction(action)
    rotate_menu.setEnabled(controls.is_video_available)

    flip_horizontal_action = menu.addAction(_("Flip Horizontal"))
    flip_horizontal_action.setCheckable(True)
    flip_horizontal_action.setChecked(controls.is_flip_horizontal)
    flip_horizontal_action.setEnabled(controls.is_video_available)
    flip_horizontal_action.triggered.connect(controls._on_flip_horizontal_action_toggled)

    flip_vertical_action = menu.addAction(_("Flip Vertical"))
    flip_vertical_action.setCheckable(True)
    flip_vertical_action.setChecked(controls.is_flip_vertical)
    flip_vertical_action.setEnabled(controls.is_video_available)
    flip_vertical_action.triggered.connect(controls._on_flip_vertical_action_toggled)

    fullscreen_action = menu.addAction(_("Fullscreen"))
    fullscreen_action_state = lambda: fullscreen_action.setChecked(controls.is_fullscreen)
    fullscreen_action.setCheckable(True)
    fullscreen_action.setChecked(controls.is_fullscreen)
    fullscreen_action.triggered.connect(controls._toggle_fullscreen)
    controls.fullscreenToggled.connect(fullscreen_action_state)

    reverse_action = menu.addAction(_("Reverse Playback"))
    reverse_action.setCheckable(True)
    reverse_action.setEnabled(controls.is_reverse_available)
    reverse_action.setChecked(controls.is_reverse_active)
    reverse_action.setToolTip(_("Audio only -- disabled while the current media has a video track"))
    reverse_action.triggered.connect(controls._on_reverse_action_toggled)

    return menu


def _make_speed_handler(controls, speed):
    return lambda: controls.speedChanged.emit(speed)


def _make_rotate_handler(controls, degrees):
    return lambda: controls._on_rotate_action_triggered(degrees)

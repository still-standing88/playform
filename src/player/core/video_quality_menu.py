"""Video Quality submenu for the player's More Options menu.

Every entry is a global mpv property (they survive file changes), so the
choices are persisted to prefs and re-applied through apply_saved_options()
when a player is initialized rather than per track. hwdec is the exception
worth knowing about: mpv only re-evaluates it when media is (re)loaded, so
changing it mid-playback takes effect on the next track.
"""
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import QMenu

from app_config import prefs
from app_constance.misc import (
    video_hwdec_modes,
    video_scalers,
    video_downscalers,
    video_interpolation_scalers,
    video_framedrop_modes,
    video_tone_mapping_modes,
    video_sync_modes,
)
from utilities.i18n import N_

# (submenu label, mpv option name, pref key, choices)
_CHOICE_OPTIONS = (
    (N_("Hardware Decoding"), "hwdec", "video_hwdec", video_hwdec_modes),
    (N_("Upscaler"), "scale", "video_scale", video_scalers),
    (N_("Downscaler"), "dscale", "video_dscale", video_downscalers),
    (N_("Chroma Scaler"), "cscale", "video_cscale", video_scalers),
    (N_("Interpolation Scaler"), "tscale", "video_tscale", video_interpolation_scalers),
    (N_("Frame Dropping"), "framedrop", "video_framedrop", video_framedrop_modes),
    (N_("HDR Tone Mapping"), "tone_mapping", "video_tone_mapping", video_tone_mapping_modes),
    (N_("Video Sync"), "video_sync", "video_sync", video_sync_modes),
)

_SHARPEN_STEPS = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)


def build_video_quality_menu(controls, parent_menu: QMenu) -> QMenu:
    menu = parent_menu.addMenu(_("Video Quality"))

    for label, option, pref_key, choices in _CHOICE_OPTIONS:
        submenu = menu.addMenu(_(label))
        group = QActionGroup(submenu)
        group.setExclusive(True)
        current = prefs.prefs.get(pref_key)
        for choice_label, value in choices:
            action = submenu.addAction(_(choice_label))
            action.setCheckable(True)
            action.setChecked(value == current)
            action.triggered.connect(_make_choice_handler(controls, option, pref_key, value))
            group.addAction(action)
        if option == "hwdec":
            submenu.setToolTip(_("Applies to the next loaded file"))

    interpolation_action = menu.addAction(_("Motion Interpolation"))
    interpolation_action.setCheckable(True)
    interpolation_action.setChecked(bool(prefs.prefs.get("video_interpolation", False)))
    interpolation_action.triggered.connect(lambda checked: _set_interpolation(controls, checked))

    sharpen_menu = menu.addMenu(_("Sharpen"))
    sharpen_group = QActionGroup(sharpen_menu)
    sharpen_group.setExclusive(True)
    current_sharpen = float(prefs.prefs.get("video_sharpen", 0.0))
    for amount in _SHARPEN_STEPS:
        action = sharpen_menu.addAction(_("Off") if amount == 0.0 else f"{amount:.1f}")
        action.setCheckable(True)
        action.setChecked(abs(amount - current_sharpen) < 0.001)
        action.triggered.connect(_make_sharpen_handler(controls, amount))
        sharpen_group.addAction(action)

    menu.setEnabled(controls.is_video_available)
    return menu


def apply_saved_options(player):
    """Pushes every persisted choice into a freshly initialized player, since
    these are mpv-instance properties rather than per-file state."""
    for _label, option, pref_key, choices in _CHOICE_OPTIONS:
        value = prefs.prefs.get(pref_key)
        if value is None:
            continue
        valid = {choice_value for _choice_label, choice_value in choices}
        if value not in valid:
            continue
        try:
            player.set_video_quality_option(option, value)
        except Exception:
            pass

    try:
        player.set_interpolation(bool(prefs.prefs.get("video_interpolation", False)))
        player.set_sharpen(float(prefs.prefs.get("video_sharpen", 0.0)))
    except Exception:
        pass


def _player_of(controls):
    widget = controls._player_widget
    return getattr(widget, "player", None) if widget is not None else None


def _make_choice_handler(controls, option: str, pref_key: str, value):
    def handler():
        prefs.prefs[pref_key] = value
        player = _player_of(controls)
        if player is None:
            return
        try:
            player.set_video_quality_option(option, value)
        except Exception:
            pass
    return handler


def _make_sharpen_handler(controls, amount: float):
    def handler():
        prefs.prefs["video_sharpen"] = float(amount)
        player = _player_of(controls)
        if player is None:
            return
        try:
            player.set_sharpen(float(amount))
        except Exception:
            pass
    return handler


def _set_interpolation(controls, enabled: bool):
    prefs.prefs["video_interpolation"] = bool(enabled)
    player = _player_of(controls)
    if player is None:
        return
    try:
        player.set_interpolation(bool(enabled))
    except Exception:
        pass

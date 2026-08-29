"""Applies the persisted subtitle rendering style to a player.

mpv's sub-* properties are instance-global and survive file changes, so this
runs on player init and again when preferences are saved, rather than per
track.
"""
from app_config import prefs


def apply_saved_subtitle_style(player) -> None:
    if player is None:
        return
    try:
        player.set_subtitle_style(
            font=prefs.prefs.get("subtitle_font", "sans-serif"),
            font_size=float(prefs.prefs.get("subtitle_font_size", 38)),
            bold=bool(prefs.prefs.get("subtitle_bold", False)),
            scale=float(prefs.prefs.get("subtitle_scale", 1.0)),
            color=prefs.prefs.get("subtitle_color", "#FFFFFFFF"),
            back_color=prefs.prefs.get("subtitle_back_color", "#AF000000"),
            border_color=prefs.prefs.get("subtitle_border_color", "#FF000000"),
            border_size=float(prefs.prefs.get("subtitle_border_size", 1.65)),
            shadow_offset=float(prefs.prefs.get("subtitle_shadow_offset", 0.0)),
            position=float(prefs.prefs.get("subtitle_position", 100)),
            ass_override=prefs.prefs.get("subtitle_ass_override", "scale"),
        )
        player.set_subtitle_visibility(bool(prefs.prefs.get("subtitle_render_on_video", True)))
    except Exception:
        pass

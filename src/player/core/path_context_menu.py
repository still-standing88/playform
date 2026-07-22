import sys

from PySide6.QtWidgets import QApplication, QMenu

from utilities.functions import is_youtube_url, is_local_file, open_file_location
from ..util.url import is_url_supported


def build_path_context_menu(controls, parent_widget) -> QMenu:
    """Build the Copy Path / Open in Explorer / Show YouTube Info menu shared
    by PlayerControls' own track-label context menu and PlayerWidget's,
    extracted out of PlayerControls.build_path_context_menu."""
    menu = QMenu(parent_widget)
    if not controls._current_file:
        return menu

    copy_action = menu.addAction(_("Copy Path"))
    copy_action.triggered.connect(lambda: _copy_current_path(controls))

    if is_local_file(controls._current_file):
        if sys.platform == "win32":
            explorer_action = menu.addAction(_("Open in Explorer"))
            explorer_action.triggered.connect(lambda p=controls._current_file: open_file_location(p) if p else None)

    source = controls._source_url or controls._current_file
    if is_youtube_url(source):
        menu.addSeparator()
        yt_info_action = menu.addAction(_("Show YouTube Info"))
        yt_info_action.triggered.connect(lambda: _show_youtube_info_dialog(controls))

        download_subs_action = menu.addAction(_("Download Subtitle..."))
        download_subs_action.triggered.connect(lambda: _download_subtitle_file(controls))

        comments_action = menu.addAction(_("View Comments..."))
        comments_action.triggered.connect(lambda: _view_youtube_comments(controls))

    if is_local_file(controls._current_file) or is_url_supported(source):
        menu.addSeparator()
        metadata_action = menu.addAction(_("View Media Metadata..."))
        metadata_action.triggered.connect(lambda: _view_media_metadata(controls))

    return menu


def _view_media_metadata(controls):
    if controls._player_widget and hasattr(controls._player_widget, 'view_media_metadata'):
        controls._player_widget.view_media_metadata()  # type: ignore


def _download_subtitle_file(controls):
    if controls._player_widget and hasattr(controls._player_widget, 'download_subtitle_file'):
        controls._player_widget.download_subtitle_file()  # type: ignore


def _view_youtube_comments(controls):
    if controls._player_widget and hasattr(controls._player_widget, 'view_youtube_comments'):
        controls._player_widget.view_youtube_comments()  # type: ignore


def _copy_current_path(controls):
    if controls._current_file:
        clipboard = QApplication.clipboard()
        clipboard.setText(controls._current_file)


def _show_youtube_info_dialog(controls):
    if controls._player_widget and hasattr(controls._player_widget, 'show_youtube_info_dialog'):
        controls._player_widget.show_youtube_info_dialog()  # type: ignore

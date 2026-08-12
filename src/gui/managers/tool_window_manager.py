from PySide6.QtWidgets import QMessageBox
from tools.ffmpeg.batch_converter.ui import BatchConverterUI
from tools.ffmpeg.media_extractor.ui import ExtractorUI
from tools.tag_editor.ui import TagEditorUI
from tools.ffmpeg.thumbnail_generator.ui import ThumbnailGeneratorUI
from tools.subtitles.converter_ui import SubtitleConverterUI
from tools.subtitles.editor_ui import SubtitleEditorUI
from tools.speech_converter.ui import SpeechConverterUI
from tools.m4b_tools.audiobook_tools.ui import AudiobookToolsUI
from tools.m4b_tools.combiner.ui import AudiobookCombinerUI
from multi_device_capture.ui import MultiDeviceCaptureUI
from gui.dialogs.tool_dialog import ToolDialog
from tools.logs_viewer_dialog import LogsViewerDialog
from utilities import signal_manager
from utilities.announcement_categories import AnnouncementCategory


def _announce(text):
    signal_manager.announce(text, AnnouncementCategory.DIALOGS)
from player.util.utilities import ensure_ffmpeg_available

class ToolWindowManager:
    def __init__(self, main_window):
        self.main_window = main_window
        
    def open_batch_converter(self):
        if not ensure_ffmpeg_available(self.main_window, show_message=True, min_major=6):
            return
        self.open_tool_dialog("batch_converter", BatchConverterUI(), _("Batch Converter"))
        
    def open_extractor(self):
        if not ensure_ffmpeg_available(self.main_window, show_message=True, min_major=6):
            return
        self.open_tool_dialog("extractor", ExtractorUI(), _("Media Extractor"))
        
    def open_tag_editor(self):
        self.open_tool_dialog("tag_editor", TagEditorUI(), _("Tag Editor"))
        
    def open_thumbnail_generator(self):
        if not ensure_ffmpeg_available(self.main_window, show_message=True, min_major=6):
            return
        self.open_tool_dialog("thumbnail_generator", ThumbnailGeneratorUI(), _("Thumbnail Generator"))
    
    def open_subtitle_converter(self):
        self.open_tool_dialog("subtitle_converter", SubtitleConverterUI(), _("Subtitle Converter"))
    
    def open_subtitle_editor(self):
        self.open_tool_dialog("subtitle_editor", SubtitleEditorUI(), _("Subtitle Editor"))

    def open_speech_converter(self):
        self.open_tool_dialog("speech_converter", SpeechConverterUI(), _("Speech Converter"))

    def open_audiobook_tools(self):
        if not ensure_ffmpeg_available(self.main_window, show_message=True, min_major=6):
            return
        self.open_tool_dialog("audiobook_tools", AudiobookToolsUI(), _("Audiobook Tools"))

    def open_audiobook_combiner(self):
        if not ensure_ffmpeg_available(self.main_window, show_message=True, min_major=6):
            return
        self.open_tool_dialog("audiobook_combiner", AudiobookCombinerUI(), _("Audiobook Combiner"))

    def open_multi_device_capture(self):
        if not ensure_ffmpeg_available(self.main_window, show_message=True, min_major=6):
            return
        self.open_tool_dialog("multi_device_capture", MultiDeviceCaptureUI(), _("Multi Device Capture"))

    def open_tool_dialog(self, tool_name, tool_widget, title):
        if self.main_window.active_tool_name and self.main_window.active_tool_name != tool_name:
            if self.main_window.active_tool_name in self.main_window.tool_dialogs:
                active_dialog = self.main_window.tool_dialogs[self.main_window.active_tool_name]
                if active_dialog.isVisible() or self.main_window.show_tool_button.isVisible():
                    QMessageBox.information(
                        self.main_window,
                        _("Tool Already Open"),
                        f"'{active_dialog.title}' {_('is already open. Please close it before opening another tool.')}",
                        QMessageBox.StandardButton.Ok
                    )
                    return
        
        if tool_name in self.main_window.tool_dialogs:
            dialog = self.main_window.tool_dialogs[tool_name]
            dialog.show_dialog()
            self.main_window.show_tool_button.setVisible(False)
        else:
            dialog = ToolDialog(tool_widget, title, self.main_window)
            dialog.dialog_hidden.connect(lambda: self.on_tool_hidden(tool_name, title))
            dialog.finished.connect(lambda: self.on_tool_closed(tool_name))
            self.main_window.tool_dialogs[tool_name] = dialog
            dialog.show_dialog()
        
        self.main_window.active_tool_name = tool_name
        _announce(f"{_('Opened')} {title}")

    def on_tool_hidden(self, tool_name, title):
        self.main_window.show_tool_button.setText(f"{_('Show')} {title}")
        self.main_window.show_tool_button.setVisible(True)
        _announce(f"{title} {_('hidden')}")

    def on_tool_closed(self, tool_name):
        if tool_name in self.main_window.tool_dialogs:
            del self.main_window.tool_dialogs[tool_name]
        if self.main_window.active_tool_name == tool_name:
            self.main_window.active_tool_name = None
        self.main_window.show_tool_button.setVisible(False)
        _announce(_("Tool closed"))

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QCheckBox,
                               QSpinBox, QTextEdit, QLineEdit, QPushButton,
                               QHBoxLayout, QFileDialog, QMessageBox, QGroupBox)
from utilities.functions import is_valid_mpv_options

class AdvancedPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        mpv_group = QGroupBox(_("MPV Settings"))
        mpv_group.setObjectName("mpvGroupBox")
        mpv_layout = QFormLayout(mpv_group)

        self.mpv_logging_check = QCheckBox(_("Enable MPV Logging"))
        self.mpv_logging_check.toggled.connect(self.toggle_mpv_logging_options)
        mpv_layout.addRow(_("MPV Logging:"), self.mpv_logging_check)

        self.debug_level_spin = QSpinBox()
        self.debug_level_spin.setRange(0, 2)
        mpv_layout.addRow(_("Debug Level:"), self.debug_level_spin)
        self.debug_level_row = mpv_layout.rowCount() - 1

        self.mpv_options_edit = QTextEdit()
        self.mpv_options_edit.setMaximumHeight(100)
        self.mpv_options_edit.setTabChangesFocus(True)

        original_focus_out = self.mpv_options_edit.focusOutEvent
        def custom_focus_out(e):
            self.validate_mpv_options()
            original_focus_out(e)
        self.mpv_options_edit.focusOutEvent = custom_focus_out

        mpv_layout.addRow(_("Extra MPV Options:"), self.mpv_options_edit)

        layout.addWidget(mpv_group)
        
        ytdlp_group = QGroupBox(_("yt-dlp Settings"))
        self.ytdlp_layout = QFormLayout(ytdlp_group)
        
        cookies_widget = QWidget()
        cookies_layout = QHBoxLayout(cookies_widget)
        cookies_layout.setContentsMargins(0, 0, 0, 0)
        self.youtube_cookies_edit = QLineEdit()
        self.youtube_cookies_edit.setReadOnly(True)
        self.cookies_browse_btn = QPushButton(_("Browse"))
        self.cookies_browse_btn.clicked.connect(self.browse_cookies_file)
        cookies_layout.addWidget(self.youtube_cookies_edit)
        cookies_layout.addWidget(self.cookies_browse_btn)
        self.ytdlp_layout.addRow(_("Cookies File:"), cookies_widget)
        
        ytdlp_widget_path = QWidget()
        ytdlp_layout_path = QHBoxLayout(ytdlp_widget_path)
        ytdlp_layout_path.setContentsMargins(0, 0, 0, 0)
        self.ytdlp_path_edit = QLineEdit()
        self.ytdlp_path_edit.setReadOnly(True)
        self.ytdlp_browse_btn = QPushButton(_("Browse"))
        self.ytdlp_browse_btn.clicked.connect(self.browse_ytdlp_path)
        ytdlp_layout_path.addWidget(self.ytdlp_path_edit)
        ytdlp_layout_path.addWidget(self.ytdlp_browse_btn)
        self.ytdlp_layout.addRow(_("yt-dlp Path:"), ytdlp_widget_path)
        
        ffmpeg_widget_path = QWidget()
        ffmpeg_layout_path = QHBoxLayout(ffmpeg_widget_path)
        ffmpeg_layout_path.setContentsMargins(0, 0, 0, 0)
        self.ffmpeg_path_edit = QLineEdit()
        self.ffmpeg_path_edit.setReadOnly(True)
        self.ffmpeg_browse_btn = QPushButton(_("Browse"))
        self.ffmpeg_browse_btn.clicked.connect(self.browse_ffmpeg_path)
        ffmpeg_layout_path.addWidget(self.ffmpeg_path_edit)
        ffmpeg_layout_path.addWidget(self.ffmpeg_browse_btn)
        self.ytdlp_layout.addRow(_("FFmpeg Path:"), ffmpeg_widget_path)
        
        self.ytdlp_logging_check = QCheckBox(_("Enable yt-dlp Logging"))
        self.ytdlp_logging_check.toggled.connect(self.toggle_ytdlp_logging_options)
        self.ytdlp_layout.addRow(_("yt-dlp Logging:"), self.ytdlp_logging_check)
        
        self.ytdlp_verbose_check = QCheckBox(_("Enable Verbose Output"))
        self.ytdlp_layout.addRow(_("Verbose Output:"), self.ytdlp_verbose_check)
        self.ytdlp_verbose_row = self.ytdlp_layout.rowCount() - 1
        
        layout.addWidget(ytdlp_group)
        layout.addStretch()
        
    def toggle_mpv_logging_options(self, checked):
        mpv_group = self.findChild(QGroupBox, "mpvGroupBox")
        if mpv_group:
            mpv_layout = mpv_group.findChild(QFormLayout)
            if mpv_layout:
                label_item = mpv_layout.itemAt(self.debug_level_row, QFormLayout.ItemRole.LabelRole)
                field_item = mpv_layout.itemAt(self.debug_level_row, QFormLayout.ItemRole.FieldRole)
                if label_item and label_item.widget():
                    label_item.widget().setVisible(checked)
                if field_item and field_item.widget():
                    field_item.widget().setVisible(checked)
        
    def toggle_ytdlp_logging_options(self, checked):
        label_item = self.ytdlp_layout.itemAt(self.ytdlp_verbose_row, QFormLayout.ItemRole.LabelRole)
        field_item = self.ytdlp_layout.itemAt(self.ytdlp_verbose_row, QFormLayout.ItemRole.FieldRole)
        if label_item and label_item.widget():
            label_item.widget().setVisible(checked)
        if field_item and field_item.widget():
            field_item.widget().setVisible(checked)
        
    def validate_mpv_options(self):
        text = self.mpv_options_edit.toPlainText().strip()
        if text and not is_valid_mpv_options(text):
            QMessageBox.warning(self, _("Invalid MPV Options"),
                              _("The MPV options are not valid. Please check the syntax."))
            self.mpv_options_edit.setFocus()
            return False
        return True
        
    def browse_cookies_file(self):
        file_path, __ = QFileDialog.getOpenFileName(self, _("Select Cookies File"), 
                                                 "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            self.youtube_cookies_edit.setText(file_path)
            
    def browse_ytdlp_path(self):
        dir_path = QFileDialog.getExistingDirectory(self, _("Select yt-dlp Directory"))
        if dir_path:
            self.ytdlp_path_edit.setText(dir_path)
    
    def browse_ffmpeg_path(self):
        dir_path = QFileDialog.getExistingDirectory(self, _("Select FFmpeg Directory"))
        if dir_path:
            self.ffmpeg_path_edit.setText(dir_path)
        
    def load_settings(self, prefs):
        self.mpv_logging_check.setChecked(prefs["mpv_logging"])
        self.debug_level_spin.setValue(prefs["debug_level"])
        self.mpv_options_edit.setPlainText(prefs["mpv_extra_options"])
        self.youtube_cookies_edit.setText(prefs["youtube_cookies"])
        self.ytdlp_path_edit.setText(prefs["yt-dlp_path"])
        self.ffmpeg_path_edit.setText(prefs["ffmpeg_path"])
        self.ytdlp_logging_check.setChecked(prefs["yt-dlp_logging"])
        self.ytdlp_verbose_check.setChecked(prefs["yt-dlp_verbose_output"])

        self.toggle_mpv_logging_options(prefs["mpv_logging"])
        self.toggle_ytdlp_logging_options(prefs["yt-dlp_logging"])

    def save_settings(self, prefs):
        prefs["mpv_logging"] = self.mpv_logging_check.isChecked()
        prefs["debug_level"] = self.debug_level_spin.value()
        prefs["mpv_extra_options"] = self.mpv_options_edit.toPlainText().strip()
        prefs["youtube_cookies"] = self.youtube_cookies_edit.text()
        prefs["yt-dlp_path"] = self.ytdlp_path_edit.text()
        prefs["ffmpeg_path"] = self.ffmpeg_path_edit.text()
        prefs["yt-dlp_logging"] = self.ytdlp_logging_check.isChecked()
        prefs["yt-dlp_verbose_output"] = self.ytdlp_verbose_check.isChecked()

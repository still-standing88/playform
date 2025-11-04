from typing import Callable, Optional
from PySide6.QtWidgets import QWidget, QLayout, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtGui import QCloseEvent, QPalette, QColor
from PySide6.QtCore import Qt
from app_constance.styles import COLORS, VIDEO_PLACEHOLDER_STYLE, VIDEO_LOADING_STYLE

LayoutType = QVBoxLayout | QHBoxLayout 


class VideoDisplayWidget(QWidget):
    
    def __init__(self, parent=None, on_close_callback:Optional[Callable[[bool], None]] = None):
        super().__init__(parent)
        self._on_close_callback = on_close_callback
        self._fullscreen:bool = False
        self._original_parent:Optional[QWidget] = None
        self._original_layout:Optional[LayoutType] = None
        self._original_position:int = -1

        self.setWindowTitle("Video Display")
        self.setAccessibleName("Video Display Area")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.vid_palette = self.palette()
        self.vid_palette.setColor(QPalette.ColorRole.Window, COLORS['black'])
        self.setPalette(self.vid_palette)
        self.setAutoFillBackground(True)

        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)

        
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.placeholder_label = QLabel("Video Display Area", self)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet(VIDEO_PLACEHOLDER_STYLE)
        self.placeholder_label.setMinimumSize(640, 360)
        self.placeholder_label.setAccessibleName("Video display area")
        self.placeholder_label.setAccessibleDescription("Main video playback area")
        
        self.loading_label = QLabel("Extracting URL...", self)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet(VIDEO_LOADING_STYLE)
        self.loading_label.hide()
        
        layout.addWidget(self.placeholder_label)
        layout.addWidget(self.loading_label)

    def set_position_info(self, layout:Optional[LayoutType], position:int):
        self._original_parent= self.parentWidget()
        self._original_layout = layout
        if self._original_layout is not None:
            self._original_position = position


    def remove_window(self):
        if self._original_layout is not None:
            self._original_layout.removeWidget(self)
        self.setParent(None)

    def restore_position(self):
        self.setParent(self._original_parent)
        if self._original_layout is not None:
            self._original_layout.insertWidget(self._original_position, self)


    def set_fullscreen(self, enabled: bool):
        if enabled == self._fullscreen:
            return

        if enabled:
            self.remove_window()
            self.setWindowFlags(Qt.WindowType.Window)
            self.showFullScreen()
            self._fullscreen = True
        else:
            self.showNormal()
            self.restore_position()
            self.setWindowFlags(Qt.WindowType.Widget)
            self.show()
            self._fullscreen = False

    def show_loading(self, message: str = "Extracting URL..."):
        self.loading_label.setText(message)
        self.loading_label.show()
        self.loading_label.raise_()
        
    def hide_loading(self):
        self.loading_label.hide()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._fullscreen:
            self.set_fullscreen(False)
            event.ignore()
            return
        else:
            if self._on_close_callback:
                self._on_close_callback(False)

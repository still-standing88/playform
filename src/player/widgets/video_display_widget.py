from typing import Callable, Optional
from PySide6.QtWidgets import QWidget, QLayout, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QFrame, QPushButton
from PySide6.QtGui import QCloseEvent, QPalette, QColor
from PySide6.QtCore import Qt
from app_constance.styles import video_loading_style, video_placeholder_style
from gui_controls.flow_layout import FlowLayout

LayoutType = QVBoxLayout | QHBoxLayout 


class VideoDisplayWidget(QWidget):
    
    def __init__(self, parent=None, on_close_callback:Optional[Callable[[bool], None]] = None):
        super().__init__(parent)
        self._on_close_callback = on_close_callback
        self._fullscreen:bool = False
        self._original_parent:Optional[QWidget] = None
        self._original_layout:Optional[LayoutType] = None
        self._original_position:int = -1

        self.setWindowTitle(_("Video Display"))
        self.setAccessibleName(_("Video Display Area"))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # Explicitly claim all offered space in both directions so layout
        # changes elsewhere can never quietly demote the video area to its
        # minimum -- mpv scales/letterboxes the picture into whatever size
        # this widget ends up with.
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.vid_palette = self.palette()
        self.vid_palette.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.black)
        self.setPalette(self.vid_palette)
        self.setAutoFillBackground(True)

        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)

        
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.placeholder_label = QLabel(_("Video Display Area"), self)
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet(video_placeholder_style())
        # This used to be 640x360 - a hardcoded floor with no documented
        # reason, dating to before the accordion needed to share this same
        # docked column. In a height-constrained dock, Qt satisfies this
        # widget's minimum before giving the accordion (Expanding policy,
        # shrinks first under pressure) anything at all, which is why the
        # accordion could vanish entirely when docked despite working fine
        # floated (full screen height, so the conflict never came up). A
        # small floor still keeps the placeholder legible without starving
        # everything below it.
        self.placeholder_label.setMinimumSize(160, self.IDEAL_HEIGHT_FLOOR)
        self.placeholder_label.setAccessibleName(_("Video display area"))
        self.placeholder_label.setAccessibleDescription(_("Main video playback area"))
        
        self.loading_label = QLabel(_("Extracting URL..."), self)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet(video_loading_style())
        self.loading_label.hide()
        
        layout.addWidget(self.placeholder_label)
        layout.addWidget(self.loading_label)

    def apply_theme_styles(self):
        self.placeholder_label.setStyleSheet(video_placeholder_style())
        self.loading_label.setStyleSheet(video_loading_style())

    # Recomputed fresh on every clamp_to_screen() pass (see DockManager) -
    # never mutated cumulatively, so a bigger screen restores the full,
    # legible default instead of leaving this permanently shrunk from
    # whatever the smallest screen ever seen last demanded.
    IDEAL_HEIGHT_FLOOR = 90
    MIN_HEIGHT_FLOOR = 0

    def set_height_floor(self, px: int):
        self.placeholder_label.setMinimumHeight(max(self.MIN_HEIGHT_FLOOR, px))

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
            if hasattr(self, "touch_controls"):
                self.touch_controls.hide()
            self.showNormal()
            self.restore_position()
            self.setWindowFlags(Qt.WindowType.Widget)
            self.show()
            self._fullscreen = False

    def create_touch_controls(self, callbacks):
        self.touch_controls = QFrame(self)
        self.touch_controls.setObjectName("fullscreenTouchControls")
        self.touch_controls.setFrameShape(QFrame.Shape.StyledPanel)
        # mpv renders in a native child window, so a non-native Qt overlay
        # would be painted underneath the video.
        self.touch_controls.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.touch_controls.setAutoFillBackground(True)
        self._touch_controls_layout = FlowLayout(self.touch_controls, margin=8, h_spacing=8, v_spacing=8)
        for key, text in (("backward", _("Back")), ("play_pause", _("Play/Pause")),
                          ("forward", _("Forward")), ("menu", _("More")),
                          ("fullscreen", _("Exit fullscreen"))):
            button = QPushButton(text, self.touch_controls)
            button.setMinimumHeight(44)
            button.clicked.connect(callbacks[key])
            self._touch_controls_layout.addWidget(button)
        self.touch_controls.hide()

    def toggle_touch_controls(self):
        self.touch_controls.setVisible(not self.touch_controls.isVisible())
        self._position_touch_controls()
        self.touch_controls.raise_()

    def _position_touch_controls(self):
        if hasattr(self, "touch_controls"):
            height = self._touch_controls_layout.heightForWidth(self.width())
            self.touch_controls.setGeometry(0, max(0, self.height() - height), self.width(), height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_touch_controls()

    def show_loading(self, message: str = _("Extracting URL...")):
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

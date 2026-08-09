"""Add/Edit Source wizard.

Page 1 - Type & Device   (add mode: pick media type, then device/window)
                          (edit mode: type is fixed, only device/window is re-pickable)
Page 2 - Settings        (form swaps per media type; skipped entirely for a
                          type/device with nothing editable - see
                          TypeDevicePage.nextId() / _type_has_editable_settings())
Page 3 - Preview         (opt-in checkbox; live QVideoWidget for video types,
                          a real QAudioSource-driven level meter for audio input)
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtMultimedia import (
    QAudioDevice,
    QCamera,
    QCameraDevice,
    QCapturableWindow,
    QMediaCaptureSession,
    QScreenCapture,
    QWindowCapture,
)
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from ..models import CaptureSource, MediaType, new_id
from ..platform_capabilities import PlatformCapabilities
from .forms import AudioSettingsForm, CameraSettingsForm, ScreenSettingsForm, WindowSettingsForm


class TypeDevicePage(QWizardPage):
    """Add mode: choose media type, then a device for that type.
    Edit mode: media type is fixed (passed in); only the device/window
    picker is shown, since re-typing a source would invalidate its
    settings page."""

    def __init__(self, edit_source: Optional[CaptureSource] = None, parent=None):
        super().__init__(parent)
        self.setTitle(_("Select source") if edit_source else _("Select type and device"))
        self._edit_source = edit_source
        self._selected_type: Optional[MediaType] = (
            edit_source.media_type if edit_source else None
        )
        # Set by SourceWizard right after addPage() - lets nextId() jump
        # straight to Preview for types/devices with nothing editable on
        # page 2 (Monitor, Window, and a Camera reporting zero formats)
        # instead of showing an empty Settings page.
        self._settings_page_id: Optional[int] = None
        self._preview_page_id: Optional[int] = None

        layout = QVBoxLayout(self)

        self.type_combo = QComboBox()
        self.type_combo.setAccessibleName(_("Source type"))
        if edit_source is None:
            available = PlatformCapabilities.available_types()
            for mt in available:
                self.type_combo.addItem(mt.label, mt)
            self.type_combo.currentIndexChanged.connect(self._on_type_changed)
            layout.addWidget(QLabel(_("Source type")))
            layout.addWidget(self.type_combo)
        else:
            # Fixed type in edit mode - show as a disabled label instead of
            # a combo the user could nudge; re-typing a source is really
            # "delete and add", not "edit".
            fixed = QLineEdit(edit_source.media_type.label)
            fixed.setReadOnly(True)
            layout.addWidget(QLabel(_("Source type")))
            layout.addWidget(fixed)

        device_row = QHBoxLayout()
        device_row.addWidget(QLabel(_("Device")))
        device_row.addStretch()
        self.refresh_btn = QPushButton(_("Refresh devices"))
        self.refresh_btn.clicked.connect(self._refresh_devices)
        device_row.addWidget(self.refresh_btn)
        layout.addLayout(device_row)

        self.device_combo = QComboBox()
        self.device_combo.setAccessibleName(_("Device"))
        layout.addWidget(self.device_combo)

        # Camera/Window enumeration can genuinely come back empty (no camera
        # plugged in, no capturable windows found by the current Qt
        # Multimedia backend) - both types stay selectable regardless (see
        # PlatformCapabilities.available_types()), so this explains why the
        # device list is empty right now instead of it just looking broken.
        self.empty_state_label = QLabel()
        self.empty_state_label.setStyleSheet("color: gray; font-size: 11px;")
        self.empty_state_label.setWordWrap(True)
        layout.addWidget(self.empty_state_label)

        self.friendly_name_edit = QLineEdit()
        self.friendly_name_edit.setPlaceholderText(_("Friendly name shown in lists"))
        if edit_source:
            self.friendly_name_edit.setText(edit_source.friendly_name)
        layout.addWidget(QLabel(_("Friendly name")))
        layout.addWidget(self.friendly_name_edit)

        self.registerField("friendly_name*", self.friendly_name_edit)

        layout.addStretch()

        if edit_source is not None:
            self._populate_devices(edit_source.media_type)
        elif self.type_combo.count():
            self._on_type_changed(0)

    def _on_type_changed(self, index: int) -> None:
        mt = self.type_combo.itemData(index)
        self._selected_type = mt
        self._populate_devices(mt)
        if not self.friendly_name_edit.text():
            self.friendly_name_edit.setText(mt.label if mt else "")

    _EMPTY_STATE_TEXT = {
        MediaType.CAMERA: _(
            "No cameras found. Make sure one is connected and allowed under "
            "Windows Settings > Privacy > Camera, then Refresh."
        ),
        MediaType.WINDOW: _(
            "No capturable windows found right now. Open the window you want to "
            "capture, then Refresh."
        ),
    }

    def _populate_devices(self, mt: Optional[MediaType]) -> None:
        self.device_combo.clear()
        if mt == MediaType.AUDIO_INPUT:
            for dev in PlatformCapabilities.audio_inputs():
                self.device_combo.addItem(dev.description(), dev)
        elif mt == MediaType.AUDIO_OUTPUT:
            for dev in PlatformCapabilities.audio_outputs():
                self.device_combo.addItem(dev.description(), dev)
        elif mt == MediaType.CAMERA:
            for dev in PlatformCapabilities.cameras():
                self.device_combo.addItem(dev.description(), dev)
        elif mt == MediaType.MONITOR:
            for scr in PlatformCapabilities.screens():
                self.device_combo.addItem(scr.name(), scr)
        elif mt == MediaType.WINDOW:
            for win in PlatformCapabilities.capturable_windows():
                self.device_combo.addItem(win.description(), win)

        # Pre-select current device when editing
        if self._edit_source and mt == self._edit_source.media_type:
            target = self._edit_source.device_id or self._edit_source.window_description
            for i in range(self.device_combo.count()):
                text = self.device_combo.itemText(i)
                if target and target in text:
                    self.device_combo.setCurrentIndex(i)
                    break

        is_empty = self.device_combo.count() == 0
        self.device_combo.setVisible(not is_empty)
        self.empty_state_label.setText(self._EMPTY_STATE_TEXT.get(mt, "") if is_empty else "")
        self.empty_state_label.setVisible(is_empty and mt in self._EMPTY_STATE_TEXT)
        self.completeChanged.emit()

    def _refresh_devices(self) -> None:
        if self._edit_source is None:
            current_type = self._selected_type
            self.type_combo.blockSignals(True)
            self.type_combo.clear()
            for mt in PlatformCapabilities.available_types():
                self.type_combo.addItem(mt.label, mt)
            idx = self.type_combo.findData(current_type) if current_type is not None else -1
            self.type_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.type_combo.blockSignals(False)
            self._selected_type = self.type_combo.currentData()
        self._populate_devices(self._selected_type)

    def selected_type(self) -> Optional[MediaType]:
        return self._selected_type

    def selected_device(self):
        idx = self.device_combo.currentIndex()
        return self.device_combo.itemData(idx) if idx >= 0 else None

    def isComplete(self) -> bool:
        return bool(self.friendly_name_edit.text()) and self.device_combo.count() > 0

    def nextId(self) -> int:
        if self._settings_page_id is not None and self._preview_page_id is not None:
            if not _type_has_editable_settings(self.selected_type(), self.selected_device()):
                return self._preview_page_id
            return self._settings_page_id
        return super().nextId()


def _type_has_editable_settings(mt: Optional[MediaType], device) -> bool:
    """Whether page 2 (Settings) has anything real for this type/device to
    show - Monitor and Window have no Qt-backed configurable properties at
    all (see ScreenSettingsForm/WindowSettingsForm), and a Camera device can
    report zero formats (driver quirk, virtual camera) even though the type
    itself generally does have settings."""
    if mt in (MediaType.AUDIO_INPUT, MediaType.AUDIO_OUTPUT):
        return True
    if mt == MediaType.CAMERA:
        return isinstance(device, QCameraDevice) and len(device.videoFormats()) > 0
    return False


class SettingsPage(QWizardPage):
    def __init__(self, type_device_page: TypeDevicePage, parent=None):
        super().__init__(parent)
        self.setTitle(_("Configure settings"))
        self._type_device_page = type_device_page

        self.stack = QStackedWidget()
        self.audio_form = AudioSettingsForm()
        self.camera_form = CameraSettingsForm()
        self.screen_form = ScreenSettingsForm()
        self.window_form = WindowSettingsForm()
        for w in (self.audio_form, self.camera_form, self.screen_form, self.window_form):
            self.stack.addWidget(w)

        layout = QVBoxLayout(self)
        layout.addWidget(self.stack)

    def initializePage(self) -> None:
        mt = self._type_device_page.selected_type()
        device = self._type_device_page.selected_device()
        if mt in (MediaType.AUDIO_INPUT, MediaType.AUDIO_OUTPUT):
            self.stack.setCurrentWidget(self.audio_form)
            if isinstance(device, QAudioDevice):
                self.audio_form.load_device_defaults(device)
        elif mt == MediaType.CAMERA:
            self.stack.setCurrentWidget(self.camera_form)
            if isinstance(device, QCameraDevice):
                self.camera_form.load_device_formats(device)
        elif mt == MediaType.MONITOR:
            self.stack.setCurrentWidget(self.screen_form)
            if device is not None:
                self.screen_form.load_screen(device)
        elif mt == MediaType.WINDOW:
            self.stack.setCurrentWidget(self.window_form)
            if isinstance(device, QCapturableWindow):
                self.window_form.load_window(device)

    def current_settings(self) -> dict:
        return self.stack.currentWidget().to_settings()

    def load_settings(self, s: dict) -> None:
        self.stack.currentWidget().from_settings(s)


class PreviewPage(QWizardPage):
    """Live preview so the user confirms they picked the right device before
    saving - camera/monitor/window get a QVideoWidget, audio gets a real
    QAudioSource-driven level meter (see audio_level_meter.AudioLevelMeter).

    Preview is opt-in via a checkbox rather than starting the moment this
    page is shown: it's the point in the wizard that actually activates a
    camera or microphone, and auto-starting that the instant Preview becomes
    current is the kind of thing that should need a deliberate click, not
    just clicking Next twice."""

    def __init__(self, type_device_page: TypeDevicePage, parent=None):
        super().__init__(parent)
        self.setTitle(_("Preview"))
        self._type_device_page = type_device_page
        self._session = QMediaCaptureSession(self)
        self._camera: Optional[QCamera] = None
        self._screen_capture: Optional[QScreenCapture] = None
        self._window_capture: Optional[QWindowCapture] = None
        self._audio_meter = None  # audio_level_meter.AudioLevelMeter, created lazily

        layout = QVBoxLayout(self)
        self.preview_checkbox = QCheckBox(_("Enable live preview"))
        self.preview_checkbox.toggled.connect(self._on_preview_toggled)
        layout.addWidget(self.preview_checkbox)

        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(220)
        self.level_meter = QProgressBar()
        self.level_meter.setRange(0, 100)
        self.level_meter.setTextVisible(False)
        self.status_label = QLabel()

        layout.addWidget(self.video_widget)
        layout.addWidget(self.level_meter)
        layout.addWidget(self.status_label)

        self._session.setVideoOutput(self.video_widget)

    def initializePage(self) -> None:
        self._teardown()
        mt = self._type_device_page.selected_type()
        is_loopback = mt == MediaType.AUDIO_OUTPUT
        self.video_widget.setVisible(mt is not None and mt.is_video)
        self.level_meter.setVisible(mt in (MediaType.AUDIO_INPUT, MediaType.AUDIO_OUTPUT))
        self.level_meter.setValue(0)

        # Reset to unchecked on every visit (including navigating back and
        # forward again) rather than remembering the last state - so a
        # camera/mic already granted once doesn't silently reactivate.
        self.preview_checkbox.blockSignals(True)
        self.preview_checkbox.setChecked(False)
        self.preview_checkbox.blockSignals(False)
        self.preview_checkbox.setEnabled(not is_loopback)

        if is_loopback:
            self.status_label.setText(PlatformCapabilities.loopback_capture_note())
        else:
            self.status_label.setText(_("Click 'Enable live preview' to preview this device."))

    def _on_preview_toggled(self, checked: bool) -> None:
        self._teardown()
        if not checked:
            mt = self._type_device_page.selected_type()
            if mt != MediaType.AUDIO_OUTPUT:
                self.status_label.setText(_("Click 'Enable live preview' to preview this device."))
            return
        self._start_preview()

    def _start_preview(self) -> None:
        mt = self._type_device_page.selected_type()
        device = self._type_device_page.selected_device()

        try:
            if mt == MediaType.CAMERA and isinstance(device, QCameraDevice):
                self._camera = QCamera(device)
                self._session.setCamera(self._camera)
                self._camera.start()
                self.status_label.setText(_("Previewing {device}").format(device=device.description()))
            elif mt == MediaType.MONITOR and device is not None:
                self._screen_capture = QScreenCapture()
                self._screen_capture.setScreen(device)
                self._session.setScreenCapture(self._screen_capture)
                self._screen_capture.start()
                self.status_label.setText(_("Previewing {device}").format(device=device.name()))
            elif mt == MediaType.WINDOW and isinstance(device, QCapturableWindow):
                self._window_capture = QWindowCapture()
                self._window_capture.setWindow(device)
                self._session.setWindowCapture(self._window_capture)
                self._window_capture.start()
                self.status_label.setText(_("Previewing {device}").format(device=device.description()))
            elif mt == MediaType.AUDIO_INPUT and isinstance(device, QAudioDevice):
                from .audio_level_meter import AudioLevelMeter

                self._audio_meter = AudioLevelMeter(device, self)
                self._audio_meter.level_changed.connect(self._on_audio_level)
                self._audio_meter.error.connect(self._on_audio_error)
                if self._audio_meter.start():
                    self.status_label.setText(_("Previewing {device}").format(device=device.description()))
        except Exception as exc:  # device may vanish mid-wizard
            self.status_label.setText(_("Preview unavailable: {error}").format(error=exc))
            self.preview_checkbox.setChecked(False)

    def _on_audio_level(self, peak: float) -> None:
        self.level_meter.setValue(int(peak * 100))

    def _on_audio_error(self, message: str) -> None:
        self.status_label.setText(_("Preview unavailable: {error}").format(error=message))
        self.preview_checkbox.setChecked(False)

    def _teardown(self) -> None:
        for obj in (self._camera, self._screen_capture, self._window_capture):
            if obj is not None:
                try:
                    obj.stop()
                except Exception:
                    pass
        self._camera = None
        self._screen_capture = None
        self._window_capture = None
        if self._audio_meter is not None:
            self._audio_meter.stop()
            self._audio_meter.deleteLater()
            self._audio_meter = None
        self.level_meter.setValue(0)

    def cleanupPage(self) -> None:
        self._teardown()


class SourceWizard(QWizard):
    def __init__(self, edit_source: Optional[CaptureSource] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Edit source") if edit_source else _("Add source"))
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self._edit_source = edit_source

        self.type_device_page = TypeDevicePage(edit_source)
        self.settings_page = SettingsPage(self.type_device_page)
        self.preview_page = PreviewPage(self.type_device_page)

        self.addPage(self.type_device_page)
        settings_page_id = self.addPage(self.settings_page)
        preview_page_id = self.addPage(self.preview_page)
        self.type_device_page._settings_page_id = settings_page_id
        self.type_device_page._preview_page_id = preview_page_id

        if edit_source and edit_source.settings:
            # Pre-seed the settings page once it's shown by connecting to
            # currentIdChanged, since forms only exist after initializePage.
            self.currentIdChanged.connect(self._maybe_preload_settings)

    def _maybe_preload_settings(self, page_id: int) -> None:
        if self.page(page_id) is self.settings_page:
            self.settings_page.load_settings(self._edit_source.settings)

    def result_source(self) -> CaptureSource:
        mt = self.type_device_page.selected_type()
        device = self.type_device_page.selected_device()
        friendly_name = self.type_device_page.friendly_name_edit.text()

        # Settings page is skipped entirely (see TypeDevicePage.nextId()) for
        # types/devices with nothing editable - pulling current_settings()
        # from it unconditionally would return whatever form the QStackedWidget
        # last happened to show instead of anything meaningful for this type.
        settings_id = self.type_device_page._settings_page_id
        if settings_id is not None and settings_id in self.visitedIds():
            settings = self.settings_page.current_settings()
        elif mt == MediaType.MONITOR and device is not None:
            settings = {"screen_name": device.name()}
        else:
            settings = {}

        device_id = ""
        window_desc = ""
        if isinstance(device, (QAudioDevice, QCameraDevice)):
            device_id = PlatformCapabilities.device_identity(device)
        elif mt == MediaType.MONITOR and device is not None:
            device_id = device.name()
        elif mt == MediaType.WINDOW and isinstance(device, QCapturableWindow):
            window_desc = device.description()

        if self._edit_source:
            self._edit_source.friendly_name = friendly_name
            self._edit_source.device_id = device_id or self._edit_source.device_id
            self._edit_source.window_description = window_desc or self._edit_source.window_description
            self._edit_source.settings = settings
            return self._edit_source

        return CaptureSource(
            id=new_id(),
            friendly_name=friendly_name,
            media_type=mt,
            device_id=device_id,
            window_description=window_desc,
            settings=settings,
        )

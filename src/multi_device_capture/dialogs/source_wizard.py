"""Add/Edit Source wizard.

Page 1 - Type & Device   (add mode: pick media type, then device/window)
                          (edit mode: type is fixed, only device/window is re-pickable)
Page 2 - Settings        (form swaps per media type; skipped entirely for a
                          type/device with nothing editable - see
                          TypeDevicePage.nextId() / _type_has_editable_settings())
Page 3 - Preview         (opt-in checkbox; a real-time astats-based level
                          meter for audio, a single test-frame grab for
                          camera/monitor/window - see
                          media_core.av_capture.level_meter /
                          .command_builder.capture_still_frame)

Every device on every page is a plain media_core.av_capture.models
.CaptureDevice - no more per-type Qt Multimedia classes
(QAudioDevice/QCameraDevice/QScreen/QCapturableWindow) to isinstance()
against, since CaptureCapabilities returns the same shape for all five
media kinds.
"""
from __future__ import annotations

import os
import tempfile
import threading
import uuid
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
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

from media_core.av_capture.capabilities import CaptureCapabilities
from media_core.av_capture.command_builder import capture_still_frame
from media_core.av_capture.models import CaptureDevice

from ..models import CaptureSource, MediaType, is_video, media_type_label, new_id
from .forms import AudioSettingsForm, CameraSettingsForm, ScreenSettingsForm, WindowSettingsForm


class TypeDevicePage(QWizardPage):
    """Add mode: choose media type, then a device for that type.
    Edit mode: media type is fixed (passed in); only the device/window
    picker is shown, since re-typing a source would invalidate its
    settings page."""

    def __init__(self, capabilities: CaptureCapabilities, edit_source: Optional[CaptureSource] = None, parent=None):
        super().__init__(parent)
        self.setTitle(_("Select source") if edit_source else _("Select type and device"))
        self.capabilities = capabilities
        self._edit_source = edit_source
        self._selected_type: Optional[MediaType] = (
            edit_source.media_type if edit_source else None
        )
        # Set by SourceWizard right after addPage() - lets nextId() jump
        # straight to Preview for a type/device with nothing editable on
        # page 2 (a Camera reporting zero formats) instead of showing an
        # empty Settings page.
        self._settings_page_id: Optional[int] = None
        self._preview_page_id: Optional[int] = None

        layout = QVBoxLayout(self)

        self.type_combo = QComboBox()
        self.type_combo.setAccessibleName(_("Source type"))
        if edit_source is None:
            for mt in capabilities.available_kinds():
                self.type_combo.addItem(media_type_label(mt), mt)
            self.type_combo.currentIndexChanged.connect(self._on_type_changed)
            layout.addWidget(QLabel(_("Source type")))
            layout.addWidget(self.type_combo)
        else:
            # Fixed type in edit mode - show as a disabled label instead of
            # a combo the user could nudge; re-typing a source is really
            # "delete and add", not "edit".
            fixed = QLineEdit(media_type_label(edit_source.media_type))
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
        # plugged in, no capturable windows found right now) - both types
        # stay selectable regardless (see CaptureCapabilities
        # .available_kinds()), so this explains why the device list is
        # empty right now instead of it just looking broken.
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
            self.friendly_name_edit.setText(media_type_label(mt) if mt else "")

    def _empty_state_text(self, mt: Optional[MediaType]) -> str:
        if mt == MediaType.CAMERA:
            return _(
                "No cameras found. Make sure one is connected and allowed under your "
                "system's camera privacy settings, then Refresh."
            )
        if mt == MediaType.WINDOW:
            note = self.capabilities.window_capture_note()
            base = _("No capturable windows found right now. Open the window you want to capture, then Refresh.")
            return f"{base} {note}" if note else base
        return ""

    def _populate_devices(self, mt: Optional[MediaType]) -> None:
        self.device_combo.clear()
        devices: list[CaptureDevice] = self.capabilities.list_devices(mt) if mt is not None else []
        for device in devices:
            label = f"{device.name} (likely loopback)" if device.loopback_hint else device.name
            self.device_combo.addItem(label, device)

        # Pre-select current device when editing
        if self._edit_source and mt == self._edit_source.media_type:
            target = self._edit_source.device_id
            for i in range(self.device_combo.count()):
                device = self.device_combo.itemData(i)
                if target and isinstance(device, CaptureDevice) and device.id == target:
                    self.device_combo.setCurrentIndex(i)
                    break

        is_empty = self.device_combo.count() == 0
        self.device_combo.setVisible(not is_empty)
        self.empty_state_label.setText(self._empty_state_text(mt) if is_empty else "")
        self.empty_state_label.setVisible(is_empty and bool(self._empty_state_text(mt)))
        self.completeChanged.emit()

    def _refresh_devices(self) -> None:
        self.capabilities.refresh()
        if self._edit_source is None:
            current_type = self._selected_type
            self.type_combo.blockSignals(True)
            self.type_combo.clear()
            for mt in self.capabilities.available_kinds():
                self.type_combo.addItem(media_type_label(mt), mt)
            idx = self.type_combo.findData(current_type) if current_type is not None else -1
            self.type_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.type_combo.blockSignals(False)
            self._selected_type = self.type_combo.currentData()
        self._populate_devices(self._selected_type)

    def selected_type(self) -> Optional[MediaType]:
        return self._selected_type

    def selected_device(self) -> Optional[CaptureDevice]:
        idx = self.device_combo.currentIndex()
        return self.device_combo.itemData(idx) if idx >= 0 else None

    def isComplete(self) -> bool:
        return bool(self.friendly_name_edit.text()) and self.device_combo.count() > 0

    def nextId(self) -> int:
        if self._settings_page_id is not None and self._preview_page_id is not None:
            if not _type_has_editable_settings(self.capabilities, self.selected_type(), self.selected_device()):
                return self._preview_page_id
            return self._settings_page_id
        return super().nextId()


def _type_has_editable_settings(capabilities: CaptureCapabilities, mt: Optional[MediaType], device) -> bool:
    """Whether page 2 (Settings) has anything real for this type/device to
    show. Monitor/Window now do (frame-rate cap + cursor toggle, both real
    gdigrab/x11grab/avfoundation options) - the previous QScreenCapture/
    QWindowCapture-based module genuinely had nothing to show here, which is
    why it skipped this page for those types; a Camera device can still
    report zero usable formats (driver quirk, virtual camera)."""
    if mt in (MediaType.AUDIO_INPUT, MediaType.AUDIO_OUTPUT):
        return True
    if mt == MediaType.CAMERA:
        return device is not None and len(capabilities.camera_formats(device)) > 0
    if mt in (MediaType.MONITOR, MediaType.WINDOW):
        return True
    return False


class SettingsPage(QWizardPage):
    def __init__(self, capabilities: CaptureCapabilities, type_device_page: TypeDevicePage, parent=None):
        super().__init__(parent)
        self.setTitle(_("Configure settings"))
        self.capabilities = capabilities
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
            if device is not None:
                self.audio_form.load_device_defaults(device)
        elif mt == MediaType.CAMERA:
            self.stack.setCurrentWidget(self.camera_form)
            if device is not None:
                self.camera_form.load_device_formats(self.capabilities, device)
        elif mt == MediaType.MONITOR:
            self.stack.setCurrentWidget(self.screen_form)
            if device is not None:
                self.screen_form.load_screen(device, self.capabilities)
        elif mt == MediaType.WINDOW:
            self.stack.setCurrentWidget(self.window_form)
            if device is not None:
                self.window_form.load_window(device, self.capabilities)

    def current_settings(self) -> dict:
        return self.stack.currentWidget().to_settings()

    def load_settings(self, s: dict) -> None:
        self.stack.currentWidget().from_settings(s)


class PreviewPage(QWizardPage):
    """Live preview so the user confirms they picked the right device before
    saving - audio gets a real astats-based level meter; camera/monitor/
    window get a one-shot test-frame grab (see command_builder
    .capture_still_frame - simpler and just as conclusive as decoding a
    live video stream for a "did I pick the right device" check).

    Preview is opt-in via a checkbox rather than starting the moment this
    page is shown: it's the point in the wizard that actually opens a
    camera/microphone, and auto-starting that the instant Preview becomes
    current is the kind of thing that should need a deliberate click."""

    _frame_ready = Signal(str)
    _frame_failed = Signal(str)

    def __init__(self, capabilities: CaptureCapabilities, type_device_page: TypeDevicePage, parent=None):
        super().__init__(parent)
        self.setTitle(_("Preview"))
        self.capabilities = capabilities
        self._type_device_page = type_device_page
        self._audio_meter = None  # dialogs.audio_level_meter.AudioLevelMeter, created lazily
        self._frame_path = os.path.join(tempfile.gettempdir(), f"playform_capture_preview_{uuid.uuid4().hex}.png")
        # capture_still_frame() runs in a background thread (see
        # _capture_test_frame) - these signals marshal its result back onto
        # the GUI thread instead of touching frame_label/status_label from
        # that thread directly.
        self._frame_ready.connect(self._on_frame_ready)
        self._frame_failed.connect(self._on_frame_error)

        layout = QVBoxLayout(self)
        self.preview_checkbox = QCheckBox(_("Enable live preview"))
        self.preview_checkbox.toggled.connect(self._on_preview_toggled)
        layout.addWidget(self.preview_checkbox)

        self.frame_label = QLabel()
        self.frame_label.setMinimumHeight(220)
        self.frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.level_meter = QProgressBar()
        self.level_meter.setRange(0, 100)
        self.level_meter.setTextVisible(False)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)

        layout.addWidget(self.frame_label)
        layout.addWidget(self.level_meter)
        layout.addWidget(self.status_label)

    def initializePage(self) -> None:
        self._teardown()
        mt = self._type_device_page.selected_type()
        is_loopback = mt == MediaType.AUDIO_OUTPUT
        self.frame_label.setVisible(mt is not None and is_video(mt))
        self.frame_label.setText(_("No test frame captured yet."))
        self.frame_label.setPixmap(QPixmap())
        self.level_meter.setVisible(mt in (MediaType.AUDIO_INPUT, MediaType.AUDIO_OUTPUT))
        self.level_meter.setValue(0)

        # Reset to unchecked on every visit (including navigating back and
        # forward again) rather than remembering the last state - so a
        # camera/mic already granted once doesn't silently reactivate.
        self.preview_checkbox.blockSignals(True)
        self.preview_checkbox.setChecked(False)
        self.preview_checkbox.blockSignals(False)
        self.preview_checkbox.setEnabled(not is_loopback)
        self.preview_checkbox.setText(_("Capture a test frame") if mt is not None and is_video(mt) else _("Enable live preview"))

        if is_loopback:
            self.status_label.setText(self.capabilities.loopback_note())
        else:
            self.status_label.setText(_("Click above to preview this device."))

    def _on_preview_toggled(self, checked: bool) -> None:
        mt = self._type_device_page.selected_type()
        if not checked:
            self._teardown()
            if mt != MediaType.AUDIO_OUTPUT:
                self.status_label.setText(_("Click above to preview this device."))
            return
        self._start_preview()

    def _start_preview(self) -> None:
        mt = self._type_device_page.selected_type()
        device = self._type_device_page.selected_device()
        if device is None:
            return

        try:
            if mt in (MediaType.AUDIO_INPUT, MediaType.AUDIO_OUTPUT):
                from .audio_level_meter import AudioLevelMeter

                self._audio_meter = AudioLevelMeter(self.capabilities, device, mt, self.capabilities.ffmpeg_executable, self)
                self._audio_meter.level_changed.connect(self._on_audio_level)
                self._audio_meter.error.connect(self._on_audio_error)
                if self._audio_meter.start():
                    self.status_label.setText(_("Previewing {device}").format(device=device.name))
            elif mt is not None and is_video(mt):
                self._capture_test_frame(mt, device)
        except Exception as exc:  # device may vanish mid-wizard
            self.status_label.setText(_("Preview unavailable: {error}").format(error=exc))
            self.preview_checkbox.setChecked(False)

    def _capture_test_frame(self, mt: MediaType, device: CaptureDevice) -> None:
        wizard = self.wizard()
        settings_id = self._type_device_page._settings_page_id
        if settings_id is not None and settings_id in wizard.visitedIds():
            settings = wizard.settings_page.current_settings()
        else:
            settings = {}
        self.status_label.setText(_("Capturing test frame..."))
        self.preview_checkbox.setEnabled(False)

        def _worker(_mt=mt, _device=device, _settings=settings, _path=self._frame_path):
            ok, error = capture_still_frame(
                self.capabilities, _mt, _device, _settings, _path, self.capabilities.ffmpeg_executable,
            )
            if ok:
                self._frame_ready.emit(_path)
            else:
                self._frame_failed.emit(error)

        threading.Thread(target=_worker, daemon=True, name="av-capture-preview-frame").start()

    def _on_frame_ready(self, path: str) -> None:
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self._on_frame_error(_("The captured frame could not be loaded."))
            return
        self.frame_label.setPixmap(pixmap.scaledToWidth(400, Qt.TransformationMode.SmoothTransformation))
        self.status_label.setText(_("Test frame captured."))
        self.preview_checkbox.setEnabled(True)
        self.preview_checkbox.setChecked(False)

    def _on_frame_error(self, message: str) -> None:
        self.status_label.setText(_("Preview unavailable: {error}").format(error=message))
        self.preview_checkbox.setEnabled(True)
        self.preview_checkbox.setChecked(False)

    def _on_audio_level(self, peak: float) -> None:
        self.level_meter.setValue(int(peak * 100))

    def _on_audio_error(self, message: str) -> None:
        self.status_label.setText(_("Preview unavailable: {error}").format(error=message))
        self.preview_checkbox.setChecked(False)

    def _teardown(self) -> None:
        if self._audio_meter is not None:
            self._audio_meter.stop()
            self._audio_meter.deleteLater()
            self._audio_meter = None
        self.level_meter.setValue(0)

    def cleanupPage(self) -> None:
        self._teardown()

    def __del__(self):
        try:
            if os.path.exists(self._frame_path):
                os.remove(self._frame_path)
        except Exception:
            pass


class SourceWizard(QWizard):
    def __init__(self, capabilities: CaptureCapabilities, edit_source: Optional[CaptureSource] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Edit source") if edit_source else _("Add source"))
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.capabilities = capabilities
        self._edit_source = edit_source

        self.type_device_page = TypeDevicePage(capabilities, edit_source)
        self.settings_page = SettingsPage(capabilities, self.type_device_page)
        self.preview_page = PreviewPage(capabilities, self.type_device_page)

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

    def closeEvent(self, event) -> None:
        self.preview_page._teardown()
        super().closeEvent(event)

    def reject(self) -> None:
        self.preview_page._teardown()
        super().reject()

    def result_source(self) -> CaptureSource:
        mt = self.type_device_page.selected_type()
        device = self.type_device_page.selected_device()
        friendly_name = self.type_device_page.friendly_name_edit.text()

        # Settings page is skipped entirely (see TypeDevicePage.nextId()) for
        # types/devices with nothing editable - pulling current_settings()
        # from it unconditionally would return whatever form the
        # QStackedWidget last happened to show instead of anything
        # meaningful for this type.
        settings_id = self.type_device_page._settings_page_id
        if settings_id is not None and settings_id in self.visitedIds():
            settings = self.settings_page.current_settings()
        else:
            settings = {}

        device_id = device.id if device is not None else ""
        window_description = device.name if (device is not None and mt == MediaType.WINDOW) else ""

        if self._edit_source:
            self._edit_source.friendly_name = friendly_name
            self._edit_source.device_id = device_id or self._edit_source.device_id
            self._edit_source.window_description = window_description or self._edit_source.window_description
            self._edit_source.settings = settings
            return self._edit_source

        return CaptureSource(
            id=new_id(),
            friendly_name=friendly_name,
            media_type=mt,
            device_id=device_id,
            window_description=window_description,
            settings=settings,
        )

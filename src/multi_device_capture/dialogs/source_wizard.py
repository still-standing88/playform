"""Add/Edit Source wizard.

Page 1 - Type & Device   (add mode: pick media type, then device/window)
                          (edit mode: type is fixed, only device/window is re-pickable)
Page 2 - Settings        (form swaps per media type; skipped entirely for a
                          type/device with nothing editable - see
                          TypeDevicePage.nextId() / _type_has_editable_settings())
Page 3 - Preview         (opt-in checkbox; per-kind preview - live MJPEG feed
                          for camera/monitor/window, real audio monitoring
                          (hear it) + level meter for audio input, level
                          meter only for audio output/loopback - see
                          media_core.av_capture.{video_preview,audio_monitor,
                          level_meter} and this module's PreviewPage
                          docstring)

Every device on every page is a plain media_core.av_capture.models
.CaptureDevice - no more per-type Qt Multimedia classes
(QAudioDevice/QCameraDevice/QScreen/QCapturableWindow) to isinstance()
against, since CaptureCapabilities returns the same shape for all five
media kinds.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
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
from media_core.av_capture.models import CaptureDevice, CaptureFormatOption

from ..async_probe import AsyncProbe
from ..models import CaptureSource, MediaType, is_video, media_type_label, new_id
from .forms import AudioSettingsForm, CameraSettingsForm, ScreenSettingsForm, WindowSettingsForm


class TypeDevicePage(QWizardPage):
    """Add mode: choose media type, then a device for that type.
    Edit mode: media type is fixed (passed in); only the device/window
    picker is shown, since re-typing a source would invalidate its
    settings page.

    Every device list (and, for Camera, its format list - needed up front
    by nextId()/_type_has_editable_settings) comes from one background
    probe via AsyncProbe rather than blocking the GUI thread on
    CaptureCapabilities' real ffmpeg/platform subprocess calls - opening
    this page or clicking Refresh used to freeze the wizard for however
    long device enumeration took."""

    def __init__(self, capabilities: CaptureCapabilities, edit_source: Optional[CaptureSource] = None,
                 existing_names: Optional[set] = None, parent=None):
        super().__init__(parent)
        self.setTitle(_("Select source") if edit_source else _("Select type and device"))
        self.capabilities = capabilities
        self._edit_source = edit_source
        self._existing_names = existing_names or set()
        self._selected_type: Optional[MediaType] = (
            edit_source.media_type if edit_source else None
        )
        # Set by SourceWizard right after addPage() - lets nextId() jump
        # straight to Preview for a type/device with nothing editable on
        # page 2 (a Camera reporting zero formats) instead of showing an
        # empty Settings page.
        self._settings_page_id: Optional[int] = None
        self._preview_page_id: Optional[int] = None

        self._probe = AsyncProbe(self)
        self._probe.result_ready.connect(self._on_probe_result)
        self._probe.failed.connect(self._on_probe_failed)
        self._devices_by_kind: dict[MediaType, list[CaptureDevice]] = {}
        self._camera_formats_cache: dict[str, list[CaptureFormatOption]] = {}
        self._loading = False
        # Tracks whether friendly_name_edit still holds an auto-filled value
        # (kept in sync with the selected type) vs. something the user typed
        # themselves (left alone from then on). False from the start in edit
        # mode, since the field already holds the source's real name.
        self._name_is_autofilled = edit_source is None

        layout = QVBoxLayout(self)

        self.type_combo = QComboBox()
        self.type_combo.setAccessibleName(_("Source type"))
        if edit_source is None:
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
        self.device_row_label = QLabel(_("Device"))
        device_row.addWidget(self.device_row_label)
        device_row.addStretch()
        self.refresh_btn = QPushButton(_("Refresh"))
        self.refresh_btn.clicked.connect(self._start_probe)
        device_row.addWidget(self.refresh_btn)
        layout.addLayout(device_row)

        self.device_combo = QComboBox()
        self.device_combo.setAccessibleName(_("Device"))
        layout.addWidget(self.device_combo)

        # Camera/Window enumeration can genuinely come back empty (no camera
        # plugged in, no capturable windows found right now) - both types
        # stay selectable regardless (see CaptureCapabilities
        # .available_kinds()), so this explains why the device list is
        # empty right now instead of it just looking broken. It also
        # doubles as the "loading" status line while the probe is running.
        self.empty_state_label = QLabel()
        self.empty_state_label.setStyleSheet("color: gray; font-size: 11px;")
        self.empty_state_label.setWordWrap(True)
        layout.addWidget(self.empty_state_label)

        self.friendly_name_edit = QLineEdit()
        self.friendly_name_edit.setPlaceholderText(_("Friendly name shown in lists"))
        self.friendly_name_edit.textEdited.connect(self._on_name_edited_by_user)
        if edit_source:
            self.friendly_name_edit.setText(edit_source.friendly_name)
        layout.addWidget(QLabel(_("Friendly name")))
        layout.addWidget(self.friendly_name_edit)

        self.registerField("friendly_name*", self.friendly_name_edit)

        layout.addStretch()

        self._start_probe()

    def _on_name_edited_by_user(self, _text: str) -> None:
        # textEdited (unlike textChanged) only fires from real user
        # keystrokes, never from our own setText() calls below - so this is
        # exactly "the user overrode the auto-fill, stop touching it".
        self._name_is_autofilled = False

    def _unique_default_name(self, mt: MediaType) -> str:
        base = f"{media_type_label(mt)} {_('source')}"
        if base not in self._existing_names:
            return base
        n = 1
        while f"{base} {n}" in self._existing_names:
            n += 1
        return f"{base} {n}"

    def _apply_autofill_name(self, mt: Optional[MediaType]) -> None:
        if not self._name_is_autofilled or mt is None:
            return
        self.friendly_name_edit.setText(self._unique_default_name(mt))

    def _start_probe(self) -> None:
        self._loading = True
        self.refresh_btn.setEnabled(False)
        self.device_combo.setEnabled(False)
        self.device_combo.setVisible(False)
        self.empty_state_label.setText(_("Checking available devices..."))
        self.empty_state_label.setVisible(True)
        self.completeChanged.emit()

        capabilities = self.capabilities
        edit_mt = self._edit_source.media_type if self._edit_source else None
        capabilities.refresh()

        def _work(_edit_mt=edit_mt):
            kinds = [_edit_mt] if _edit_mt is not None else capabilities.available_kinds()
            devices_by_kind = {kind: capabilities.list_devices(kind) for kind in kinds}
            camera_formats = {
                device.id: capabilities.camera_formats(device)
                for device in devices_by_kind.get(MediaType.CAMERA, [])
            }
            return kinds, devices_by_kind, camera_formats

        self._probe.run(_work)

    def _on_probe_failed(self, message: str) -> None:
        self._loading = False
        self.refresh_btn.setEnabled(True)
        self.empty_state_label.setText(_("Could not check devices: {error}").format(error=message))
        self.empty_state_label.setVisible(True)
        self.completeChanged.emit()

    def _on_probe_result(self, result) -> None:
        kinds, devices_by_kind, camera_formats = result
        self._loading = False
        self._devices_by_kind = devices_by_kind
        self._camera_formats_cache = camera_formats
        self.refresh_btn.setEnabled(True)

        if self._edit_source is None:
            current_type = self._selected_type
            self.type_combo.blockSignals(True)
            self.type_combo.clear()
            for mt in kinds:
                self.type_combo.addItem(media_type_label(mt), mt)
            idx = self.type_combo.findData(current_type) if current_type is not None else -1
            self.type_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.type_combo.blockSignals(False)
            self._selected_type = self.type_combo.currentData()
        else:
            self._selected_type = self._edit_source.media_type

        self._populate_devices(self._selected_type)
        self._apply_autofill_name(self._selected_type)

    def _on_type_changed(self, index: int) -> None:
        if self._loading:
            return
        mt = self.type_combo.itemData(index)
        self._selected_type = mt
        self._populate_devices(mt)
        self._apply_autofill_name(mt)

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
        self.device_row_label.setText(media_type_label(mt) if mt is not None else _("Device"))
        self.device_combo.setEnabled(True)
        self.device_combo.clear()
        devices: list[CaptureDevice] = self._devices_by_kind.get(mt, []) if mt is not None else []
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

    def selected_type(self) -> Optional[MediaType]:
        return self._selected_type

    def selected_device(self) -> Optional[CaptureDevice]:
        idx = self.device_combo.currentIndex()
        return self.device_combo.itemData(idx) if idx >= 0 else None

    def isComplete(self) -> bool:
        return not self._loading and bool(self.friendly_name_edit.text()) and self.device_combo.count() > 0

    def nextId(self) -> int:
        if self._settings_page_id is not None and self._preview_page_id is not None:
            device = self.selected_device()
            formats = self._camera_formats_cache.get(device.id, []) if device is not None else []
            if not _type_has_editable_settings(self.selected_type(), device, formats):
                return self._preview_page_id
            return self._settings_page_id
        return super().nextId()


def _type_has_editable_settings(mt: Optional[MediaType], device, camera_formats: list) -> bool:
    """Whether page 2 (Settings) has anything real for this type/device to
    show. Monitor/Window now do (frame-rate cap + cursor toggle, both real
    gdigrab/x11grab/avfoundation options) - the previous QScreenCapture/
    QWindowCapture-based module genuinely had nothing to show here, which is
    why it skipped this page for those types; a Camera device can still
    report zero usable formats (driver quirk, virtual camera)."""
    if mt in (MediaType.AUDIO_INPUT, MediaType.AUDIO_OUTPUT):
        return True
    if mt == MediaType.CAMERA:
        return device is not None and len(camera_formats) > 0
    if mt in (MediaType.MONITOR, MediaType.WINDOW):
        return True
    return False


class SettingsPage(QWizardPage):
    def __init__(self, capabilities: CaptureCapabilities, type_device_page: TypeDevicePage,
                 global_settings=None, parent=None):
        super().__init__(parent)
        self.setTitle(_("Configure settings"))
        self.capabilities = capabilities
        self._type_device_page = type_device_page
        self._global_settings = global_settings

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
        is_new_source = self._type_device_page._edit_source is None
        if mt in (MediaType.AUDIO_INPUT, MediaType.AUDIO_OUTPUT):
            self.stack.setCurrentWidget(self.audio_form)
            if is_new_source and self._global_settings is not None:
                self.audio_form.from_settings(self._global_settings.get_audio())
            if device is not None:
                self.audio_form.load_device_defaults(device)
        elif mt == MediaType.CAMERA:
            self.stack.setCurrentWidget(self.camera_form)
            if device is not None:
                formats = self._type_device_page._camera_formats_cache.get(device.id, [])
                self.camera_form.load_device_formats(formats)
        elif mt == MediaType.MONITOR:
            self.stack.setCurrentWidget(self.screen_form)
            if is_new_source and self._global_settings is not None:
                self.screen_form.from_settings(self._video_defaults())
            if device is not None:
                self.screen_form.load_screen(device, self.capabilities)
        elif mt == MediaType.WINDOW:
            self.stack.setCurrentWidget(self.window_form)
            if is_new_source and self._global_settings is not None:
                self.window_form.from_settings(self._video_defaults())
            if device is not None:
                self.window_form.load_window(device, self.capabilities)

    def _video_defaults(self) -> dict:
        video = self._global_settings.get_video()
        return {"fps": video.get("fps", 30), "capture_cursor": video.get("capture_cursor", False)}

    def current_settings(self) -> dict:
        return self.stack.currentWidget().to_settings()

    def load_settings(self, s: dict) -> None:
        self.stack.currentWidget().from_settings(s)


class PreviewPage(QWizardPage):
    """Live preview so the user confirms they picked the right device before
    saving:
    - Camera/Monitor/Window get a continuous downscaled MJPEG feed (see
      media_core.av_capture.video_preview) - an actual live picture, not a
      single test-frame grab.
    - Audio input gets real audio monitoring (hear the mic through the
      system's default output) plus a level meter, both driven off one
      ffmpeg process's raw PCM (media_core.av_capture.audio_monitor).
    - Audio output (loopback) keeps the astats-based level meter only -
      playing a loopback capture back out to the same device it's
      monitoring would create an audible feedback/echo loop, so there's no
      "hear it" option for this one.

    Preview is opt-in via a checkbox rather than starting the moment this
    page is shown: it's the point in the wizard that actually opens a
    camera/microphone, and auto-starting that the instant Preview becomes
    current is the kind of thing that should need a deliberate click."""

    def __init__(self, capabilities: CaptureCapabilities, type_device_page: TypeDevicePage, parent=None):
        super().__init__(parent)
        self.setTitle(_("Preview"))
        self.capabilities = capabilities
        self._type_device_page = type_device_page
        self._audio_meter = None    # dialogs.audio_level_meter.AudioLevelMeter (Audio output only)
        self._audio_monitor = None  # dialogs.audio_monitor.AudioMonitor (Audio input only)
        self._video_preview = None  # dialogs.video_preview.VideoPreview

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
        self.frame_label.setText(_("No preview yet."))
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
        self.preview_checkbox.setText(_("Enable live preview"))

        if is_loopback:
            note = self.capabilities.loopback_note()
            self.status_label.setText(
                _("Playing this back would create an audio feedback loop, so there is no 'hear it' "
                  "preview for a loopback source - level meter only.")
                if not note else note
            )
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

    def _current_settings(self) -> dict:
        wizard = self.wizard()
        settings_id = self._type_device_page._settings_page_id
        if settings_id is not None and settings_id in wizard.visitedIds():
            return wizard.settings_page.current_settings()
        return {}

    def _start_preview(self) -> None:
        mt = self._type_device_page.selected_type()
        device = self._type_device_page.selected_device()
        if device is None:
            return
        ffmpeg_executable = self.capabilities.ffmpeg_executable

        try:
            if mt == MediaType.AUDIO_INPUT:
                from .audio_monitor import AudioMonitor

                self._audio_monitor = AudioMonitor(self.capabilities, device, ffmpeg_executable, self)
                self._audio_monitor.level_changed.connect(self._on_audio_level)
                self._audio_monitor.error.connect(self._on_audio_error)
                if self._audio_monitor.start():
                    self.status_label.setText(_("Previewing {device} - you should hear it.").format(device=device.name))
            elif mt == MediaType.AUDIO_OUTPUT:
                from .audio_level_meter import AudioLevelMeter

                self._audio_meter = AudioLevelMeter(self.capabilities, device, mt, ffmpeg_executable, self)
                self._audio_meter.level_changed.connect(self._on_audio_level)
                self._audio_meter.error.connect(self._on_audio_error)
                if self._audio_meter.start():
                    self.status_label.setText(_("Previewing {device}").format(device=device.name))
            elif mt is not None and is_video(mt):
                from .video_preview import VideoPreview

                self._video_preview = VideoPreview(self.capabilities, device, mt, self._current_settings(), ffmpeg_executable, self)
                self._video_preview.frame_ready.connect(self._on_video_frame)
                self._video_preview.error.connect(self._on_video_error)
                if self._video_preview.start():
                    self.status_label.setText(_("Previewing {device}").format(device=device.name))
        except Exception as exc:  # device may vanish mid-wizard
            self.status_label.setText(_("Preview unavailable: {error}").format(error=exc))
            self.preview_checkbox.setChecked(False)

    def _on_video_frame(self, jpeg_bytes: bytes) -> None:
        pixmap = QPixmap()
        if pixmap.loadFromData(jpeg_bytes, "JPEG"):
            self.frame_label.setPixmap(pixmap.scaledToWidth(400, Qt.TransformationMode.SmoothTransformation))

    def _on_video_error(self, message: str) -> None:
        self.status_label.setText(_("Preview unavailable: {error}").format(error=message))
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
        if self._audio_monitor is not None:
            self._audio_monitor.stop()
            self._audio_monitor.deleteLater()
            self._audio_monitor = None
        if self._video_preview is not None:
            self._video_preview.stop()
            self._video_preview.deleteLater()
            self._video_preview = None
        self.level_meter.setValue(0)

    def cleanupPage(self) -> None:
        self._teardown()


class SourceWizard(QWizard):
    def __init__(self, capabilities: CaptureCapabilities, edit_source: Optional[CaptureSource] = None,
                 global_settings=None, existing_names: Optional[set] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Edit source") if edit_source else _("Add source"))
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.capabilities = capabilities
        self._edit_source = edit_source

        self.type_device_page = TypeDevicePage(capabilities, edit_source, existing_names)
        self.settings_page = SettingsPage(capabilities, self.type_device_page, global_settings)
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

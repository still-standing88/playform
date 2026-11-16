from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QProgressBar,
    QPushButton, QVBoxLayout, QWizard, QWizardPage,
)

from media_core.av_capture.capabilities import CaptureCapabilities

from ..async_probe import AsyncProbe
from ..models import CaptureSource, MediaType, is_audio, is_video, media_type_label, new_id
from .forms import AudioSettingsForm, VideoSettingsForm
from .source_preview import SourcePreview


class TypeDevicePage(QWizardPage):
    def __init__(self, capabilities, edit_source, existing_names, parent=None):
        super().__init__(parent)
        self.setTitle(_("Choose a capture source"))
        self.capabilities = capabilities
        self._edit_source = edit_source
        self._existing_names = existing_names or set()
        self._devices_by_kind = {}
        self._loading = True
        self._auto_name = edit_source is None

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.type_combo = QComboBox()
        self.type_combo.currentIndexChanged.connect(self._populate_devices)
        form.addRow(_("Source type"), self.type_combo)

        row = QHBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.setAccessibleName(_("Capture device"))
        self.device_combo.currentIndexChanged.connect(self._device_changed)
        row.addWidget(self.device_combo, 1)
        self.refresh_btn = QPushButton(_("Refresh"))
        self.refresh_btn.clicked.connect(self._start_probe)
        row.addWidget(self.refresh_btn)
        form.addRow(_("Device"), row)

        self.friendly_name_edit = QLineEdit(edit_source.friendly_name if edit_source else "")
        self.friendly_name_edit.textEdited.connect(self._name_edited)
        self.friendly_name_edit.textChanged.connect(self.completeChanged)
        form.addRow(_("Source name"), self.friendly_name_edit)

        self.status = QLabel()
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch()

        self._probe = AsyncProbe(self)
        self._probe.result_ready.connect(self._on_probe_result)
        self._probe.failed.connect(self._on_probe_failed)
        self._start_probe()

    def _start_probe(self):
        self._loading = True
        self.refresh_btn.setEnabled(False)
        self.type_combo.setEnabled(False)
        self.device_combo.setEnabled(False)
        self.status.setText(_("Checking available sources…"))
        self.completeChanged.emit()
        self._probe.run(self.capabilities.inventory)

    def _on_probe_failed(self, message):
        self._loading = False
        self._devices_by_kind.clear()
        self.device_combo.clear()
        self.refresh_btn.setEnabled(True)
        self.status.setText(_("Could not check sources: {error}").format(error=message))
        self.completeChanged.emit()

    def _on_probe_result(self, devices):
        current_kind = self.type_combo.currentData()
        self._devices_by_kind = devices
        self._loading = False
        self.refresh_btn.setEnabled(True)
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        if self._edit_source:
            kind = self._edit_source.media_type
            self.type_combo.addItem(media_type_label(kind), kind)
        else:
            for kind, sources in devices.items():
                if sources or kind in (MediaType.CAMERA, MediaType.WINDOW):
                    self.type_combo.addItem(media_type_label(kind), kind)
        self.type_combo.setCurrentIndex(max(0, self.type_combo.findData(current_kind)))
        self.type_combo.setEnabled(self._edit_source is None)
        self.type_combo.blockSignals(False)
        self._populate_devices()

    def _populate_devices(self, *_):
        old_device = self.selected_device()
        kind = self.type_combo.currentData()
        devices = self.devices(kind)
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        for device in devices:
            self.device_combo.addItem(device.name or _("Mixed audio"), device)

        target = None
        if old_device and old_device.kind == kind:
            target = self.capabilities.resolve_device(devices, old_device.id, old_device.name)
        elif self._edit_source:
            saved = self._edit_source
            target = self.capabilities.resolve_device(
                devices, saved.device_id, saved.device_name or saved.settings.get("screen_name", ""),
            )
        if target is not None:
            self.device_combo.setCurrentIndex(devices.index(target))
        elif self._edit_source:
            self.device_combo.setCurrentIndex(-1)
        self.device_combo.setEnabled(bool(devices))
        self.device_combo.blockSignals(False)
        self._device_changed()

    def _device_changed(self, *_):
        device = self.selected_device()
        if device is not None:
            if self._auto_name:
                base = device.name or media_type_label(device.kind)
                name = base
                suffix = 2
                while name in self._existing_names:
                    name = f"{base} {suffix}"
                    suffix += 1
                self.friendly_name_edit.setText(name)
            self.status.clear()
        elif self._loading:
            self.status.setText(_("Checking available sources…"))
        elif self.device_combo.count():
            self.status.setText(_("The saved device is unavailable. Select a device to update this source."))
        else:
            self.status.setText(_("No sources of this type are available. Connect the device or open the target, then refresh."))
        self.completeChanged.emit()

    def _name_edited(self, _text):
        self._auto_name = False

    def devices(self, kind):
        return self._devices_by_kind.get(kind, [])

    def selected_type(self):
        return self.type_combo.currentData()

    def selected_device(self):
        return self.device_combo.currentData()

    def isComplete(self):
        return not self._loading and self.selected_device() is not None and bool(self.friendly_name_edit.text().strip())


class SettingsPage(QWizardPage):
    def __init__(self, capabilities, device_page, global_settings, edit_source, parent=None):
        super().__init__(parent)
        self.setTitle(_("Capture and encoding settings"))
        self._capabilities = capabilities
        self._devices = device_page
        self._defaults = global_settings
        self._edit_source = edit_source
        self._device_key = None
        self._form = None
        self._layout = QVBoxLayout(self)
        self._status = QLabel()
        self._status.setWordWrap(True)
        self._layout.addWidget(self._status)
        self._layout.addStretch()
        self._probe = AsyncProbe(self)
        self._probe.result_ready.connect(self._on_camera_formats)

    def initializePage(self):
        device = self._devices.selected_device()
        kind = device.kind
        key = (kind, device.id)
        if self._device_key == key:
            return
        self._device_key = key
        if self._form is not None:
            self._layout.removeWidget(self._form)
            self._form.deleteLater()

        if is_audio(kind):
            self._form = AudioSettingsForm(
                kind, self._devices.devices(MediaType.AUDIO_INPUT), self._devices.devices(MediaType.AUDIO_OUTPUT),
            )
            settings = self._defaults.get_audio() if self._defaults else {}
        else:
            self._form = VideoSettingsForm(kind)
            settings = self._defaults.get_video() if self._defaults else {}
        if self._edit_source:
            settings.update(self._edit_source.settings)
        self._form.from_settings(settings)
        self._layout.insertWidget(0, self._form)
        self._status.clear()

        if kind == MediaType.CAMERA:
            self._status.setText(_("Checking camera resolutions…"))

            def get_formats():
                try:
                    return key, self._capabilities.camera_formats(device)
                except (OSError, RuntimeError):
                    return key, []

            self._probe.run(get_formats)

    def _on_camera_formats(self, result):
        key, formats = result
        if key != self._device_key:
            return
        self._form.load_camera_formats(formats)
        self._status.setText("" if formats else _("MediaCap could not read camera resolutions. You can use the default."))

    def current_settings(self):
        return self._form.to_settings()


class PreviewPage(QWizardPage):

    def __init__(self, capabilities: CaptureCapabilities, type_device_page: TypeDevicePage, parent=None):
        super().__init__(parent)
        self.setTitle(_("Preview"))
        self.capabilities = capabilities
        self._type_device_page = type_device_page
        self._preview = None

        layout = QVBoxLayout(self)
        self.preview_checkbox = QCheckBox(_("Preview this source"))
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
        self.frame_label.setVisible(mt is not None and is_video(mt))
        self.frame_label.setText(_("No preview yet."))
        self.frame_label.setPixmap(QPixmap())
        self.level_meter.setVisible(is_audio(mt))
        self.level_meter.setValue(0)

        self.preview_checkbox.blockSignals(True)
        self.preview_checkbox.setChecked(False)
        self.preview_checkbox.blockSignals(False)
        self.status_label.clear()

    def _on_preview_toggled(self, checked: bool) -> None:
        if not checked:
            self._teardown()
            self.status_label.clear()
            return
        self._start_preview()

    def _current_settings(self) -> dict:
        return self.wizard().settings_page.current_settings()

    def _start_preview(self) -> None:
        mt = self._type_device_page.selected_type()
        device = self._type_device_page.selected_device()
        if device is None:
            return
        preview = SourcePreview(self.capabilities.executable, device, self._current_settings(),
                                listen=mt == MediaType.AUDIO_INPUT)
        self._preview = preview
        preview.frame_ready.connect(self._on_video_frame)
        preview.level_changed.connect(self._on_audio_level)
        preview.error.connect(self._on_preview_error)
        preview.finished.connect(self._on_preview_finished)
        preview.finished.connect(preview.deleteLater)
        self.status_label.setText(_("Previewing {device}").format(device=device.name))
        preview.start()

    @Slot(QImage)
    def _on_video_frame(self, image) -> None:
        if self.sender() is self._preview:
            self.frame_label.setPixmap(QPixmap.fromImage(image))

    @Slot(float)
    def _on_audio_level(self, peak: float) -> None:
        if self.sender() is self._preview:
            self.level_meter.setValue(int(peak * 100))

    @Slot(str)
    def _on_preview_error(self, message: str) -> None:
        if self.sender() is self._preview:
            self.preview_checkbox.setChecked(False)
            self.status_label.setText(_("Preview unavailable: {error}").format(error=message))

    @Slot()
    def _on_preview_finished(self) -> None:
        if self.sender() is self._preview:
            self.preview_checkbox.setChecked(False)
            self.status_label.setText(_("Preview finished. Select Preview to run it again."))

    def _teardown(self) -> None:
        if self._preview is not None:
            self._preview.stop()
            self._preview = None
        self.level_meter.setValue(0)

    def cleanupPage(self) -> None:
        self._teardown()


class SourceWizard(QWizard):
    def __init__(self, capabilities: CaptureCapabilities, edit_source: Optional[CaptureSource] = None,
                 global_settings=None, existing_names: Optional[set] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Edit source") if edit_source else _("Add source"))
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self._edit_source = edit_source
        self.type_device_page = TypeDevicePage(capabilities, edit_source, existing_names)
        self.settings_page = SettingsPage(capabilities, self.type_device_page, global_settings, edit_source)
        self.preview_page = PreviewPage(capabilities, self.type_device_page)
        self.addPage(self.type_device_page)
        self.addPage(self.settings_page)
        self.addPage(self.preview_page)

    def done(self, result: int) -> None:
        self.preview_page._teardown()
        super().done(result)

    def result_source(self) -> CaptureSource:
        device = self.type_device_page.selected_device()
        saved = self._edit_source
        return CaptureSource(
            id=saved.id if saved else new_id(),
            friendly_name=self.type_device_page.friendly_name_edit.text().strip(),
            media_type=device.kind,
            device_id=device.id,
            window_description=device.name,
            settings=self.settings_page.current_settings(),
            enabled=saved.enabled if saved else True,
        )

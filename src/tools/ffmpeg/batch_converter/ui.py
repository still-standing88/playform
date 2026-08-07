import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QComboBox,
    QLabel, QProgressDialog, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt

from tools.ffmpeg.batch_converter.source_tab import SourceTab
from tools.ffmpeg.batch_converter.convert_tab import ConvertTab
from tools.ffmpeg.batch_converter.processing_tab import ProcessingTab
from tools.ffmpeg.batch_converter.destination_tab import DestinationTab
from tools.ffmpeg.batch_converter.job import BatchConverterJob
from tools.ffmpeg.batch_converter import presets
from utilities import signal_manager


class BatchConverterUI(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.job: BatchConverterJob | None = None
        self.progress_dialog: QProgressDialog | None = None
        self._build_ui()
        self._reload_presets()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel(_("Preset:")))
        self.preset_combo = QComboBox(self)
        self.preset_combo.setEditable(True)
        preset_row.addWidget(self.preset_combo, stretch=1)
        self.save_preset_button = QPushButton(_("Save"), self)
        self.delete_preset_button = QPushButton(_("Delete"), self)
        preset_row.addWidget(self.save_preset_button)
        preset_row.addWidget(self.delete_preset_button)
        layout.addLayout(preset_row)

        self.tabs = QTabWidget(self)
        self.source_tab = SourceTab(self)
        self.convert_tab = ConvertTab(self)
        self.processing_tab = ProcessingTab(self)
        self.destination_tab = DestinationTab(self)
        self.tabs.addTab(self.source_tab, _("Source"))
        self.tabs.addTab(self.convert_tab, _("Convert"))
        self.tabs.addTab(self.processing_tab, _("Processing"))
        self.tabs.addTab(self.destination_tab, _("Destination"))
        layout.addWidget(self.tabs)

        button_row = QHBoxLayout()
        self.begin_button = QPushButton(_("Begin"), self)
        self.cancel_button = QPushButton(_("Cancel"), self)
        self.cancel_button.setEnabled(False)
        button_row.addStretch()
        button_row.addWidget(self.begin_button)
        button_row.addWidget(self.cancel_button)
        layout.addLayout(button_row)

        self.begin_button.clicked.connect(self._on_begin)
        self.cancel_button.clicked.connect(self._on_cancel)
        self.save_preset_button.clicked.connect(self._on_save_preset)
        self.delete_preset_button.clicked.connect(self._on_delete_preset)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)

    def _reload_presets(self):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItems(presets.list_presets())
        self.preset_combo.blockSignals(False)

    def _on_preset_selected(self, index: int):
        name = self.preset_combo.itemText(index)
        if not name:
            return
        try:
            data = presets.load_preset(name)
        except OSError:
            return
        self.convert_tab.load_options(data.get("convert"))
        self.processing_tab.load_applied_effects(data.get("processing") or [])

    def _on_save_preset(self):
        name = self.preset_combo.currentText().strip()
        if not name:
            name, ok = QInputDialog.getText(self, _("Save Preset"), _("Preset name:"))
            if not ok or not name.strip():
                return
            name = name.strip()

        presets.save_preset(name, self.convert_tab.selected_options(), self.processing_tab.applied_effects())
        self._reload_presets()
        index = self.preset_combo.findText(name)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)

    def _on_delete_preset(self):
        name = self.preset_combo.currentText().strip()
        if not name:
            return
        presets.delete_preset(name)
        self._reload_presets()

    def _on_begin(self):
        if not self.source_tab.has_sources():
            QMessageBox.warning(self, _("No Sources"), _("Add at least one file or folder in the Source tab."))
            return

        destination_options = self.destination_tab.selected_options()
        if not destination_options["store_in_original_folder"] and not destination_options["target_folder"]:
            QMessageBox.warning(self, _("No Destination"), _("Choose a destination folder."))
            return

        entries = list(self.source_tab.iter_entries())
        convert_options = self.convert_tab.selected_options()
        processing_effects = self.processing_tab.applied_effects()

        self.job = BatchConverterJob(entries, convert_options, processing_effects, destination_options)
        self.job.overall_progress.connect(self._on_overall_progress)
        self.job.file_progress.connect(self._on_file_progress)
        self.job.file_completed.connect(self._on_file_completed)
        self.job.finished_all.connect(self._on_finished)

        self.progress_dialog = QProgressDialog(_("Converting..."), _("Cancel"), 0, 1, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.canceled.connect(self._on_cancel)

        self.begin_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.job.start()
        self.progress_dialog.show()
        signal_manager.statusbar_message.emit(_("Batch conversion started"))

    def _on_cancel(self):
        if self.job:
            self.job.stop()
        self.cancel_button.setEnabled(False)

    def _on_overall_progress(self, current: int, total: int, filename: str):
        if not self.progress_dialog:
            return
        self.progress_dialog.setMaximum(max(total, 1))
        self.progress_dialog.setValue(current)
        if filename:
            self.progress_dialog.setLabelText(
                _("Converting file {current} of {total}: {filename}").format(
                    current=current + 1, total=total, filename=filename
                )
            )

    def _on_file_progress(self, text: str):
        if self.progress_dialog:
            base = self.progress_dialog.labelText().split(" — ")[0]
            self.progress_dialog.setLabelText(f"{base} — {text}")

    def _on_file_completed(self, path: str, success: bool, message: str):
        if not success:
            signal_manager.statusbar_message.emit(
                _("Failed: {filename} — {message}").format(filename=os.path.basename(path), message=message)
            )

    def _on_finished(self):
        self.begin_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if self.progress_dialog:
            self.progress_dialog.close()
        signal_manager.statusbar_message.emit(_("Batch conversion finished"))

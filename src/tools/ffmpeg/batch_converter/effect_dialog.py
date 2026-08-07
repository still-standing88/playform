from PySide6.QtWidgets import (
    QDialog, QFormLayout, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QPushButton, QFileDialog
)

from tools.ffmpeg.batch_converter.effects_catalog import EffectDefinition


class EffectParameterDialog(QDialog):

    def __init__(self, effect: EffectDefinition, values: dict = None, parent=None):
        super().__init__(parent)
        self.effect = effect
        self._values = dict(values or {})
        self._inputs: dict = {}
        self.setWindowTitle(effect.label)
        self.setMinimumWidth(360)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        if not self.effect.params:
            form.addRow(QLabel(_("This effect has no configurable parameters.")))

        for param in self.effect.params:
            current = self._values.get(param.key, param.default)
            widget = self._make_widget(param, current)
            self._inputs[param.key] = widget
            form.addRow(param.label, widget if not isinstance(widget, tuple) else widget[0])

        button_row = QHBoxLayout()
        self.ok_button = QPushButton(_("OK"), self)
        self.cancel_button = QPushButton(_("Cancel"), self)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        button_row.addStretch()
        button_row.addWidget(self.ok_button)
        button_row.addWidget(self.cancel_button)
        layout.addLayout(button_row)

    def _make_widget(self, param, current):
        if param.kind == "choice":
            combo = QComboBox(self)
            for choice in param.choices or []:
                combo.addItem(str(choice), choice)
            index = combo.findData(current)
            combo.setCurrentIndex(index if index >= 0 else 0)
            return combo

        if param.kind == "bool":
            check = QCheckBox(self)
            check.setChecked(bool(current))
            return check

        if param.kind == "int":
            spin = QSpinBox(self)
            low, high = param.value_range or (-1000000, 1000000)
            spin.setRange(int(low), int(high))
            spin.setSuffix(param.suffix)
            spin.setValue(int(current) if current is not None else int(low))
            return spin

        if param.kind == "float":
            spin = QDoubleSpinBox(self)
            low, high = param.value_range or (-1000000.0, 1000000.0)
            spin.setRange(float(low), float(high))
            spin.setDecimals(3)
            spin.setSuffix(param.suffix)
            spin.setValue(float(current) if current is not None else float(low))
            return spin

        if param.kind == "file":
            row = QHBoxLayout()
            edit = QLineEdit(self)
            edit.setText(str(current or ""))
            browse = QPushButton(_("Browse..."), self)

            def _browse():
                path, _filter = QFileDialog.getOpenFileName(self, _("Select File"))
                if path:
                    edit.setText(path)

            browse.clicked.connect(_browse)
            row.addWidget(edit)
            row.addWidget(browse)
            container = self._wrap_layout(row)
            container._value_edit = edit
            return container

        edit = QLineEdit(self)
        edit.setText(str(current) if current is not None else "")
        return edit

    @staticmethod
    def _wrap_layout(layout):
        from PySide6.QtWidgets import QWidget
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def values(self) -> dict:
        result = dict(self._values)
        for key, widget in self._inputs.items():
            if isinstance(widget, QComboBox):
                result[key] = widget.currentData()
            elif isinstance(widget, QCheckBox):
                result[key] = widget.isChecked()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                result[key] = widget.value()
            elif hasattr(widget, "_value_edit"):
                result[key] = widget._value_edit.text()
            elif isinstance(widget, QLineEdit):
                result[key] = widget.text()
        return result

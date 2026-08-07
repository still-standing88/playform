from PySide6.QtWidgets import QDialog, QFormLayout, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

from tools.ffmpeg.batch_converter.effects_catalog import EffectDefinition
from tools.ffmpeg.batch_converter.param_widgets import make_param_widget, read_param_widget


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
            widget = make_param_widget(self, param.kind, param.choices, param.value_range, current, param.suffix)
            self._inputs[param.key] = widget
            form.addRow(param.label, widget)

        button_row = QHBoxLayout()
        self.ok_button = QPushButton(_("OK"), self)
        self.cancel_button = QPushButton(_("Cancel"), self)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        button_row.addStretch()
        button_row.addWidget(self.ok_button)
        button_row.addWidget(self.cancel_button)
        layout.addLayout(button_row)

    def values(self) -> dict:
        result = dict(self._values)
        for key, widget in self._inputs.items():
            result[key] = read_param_widget(widget)
        return result

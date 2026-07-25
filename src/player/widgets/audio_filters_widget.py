from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QSpinBox,
                                QDoubleSpinBox, QComboBox, QLineEdit)
from PySide6.QtCore import Qt, Signal

from gui_controls.list_tab import ListTabCtrl
from gui_controls.player_key_event_filter import KeyEventFilter


class FilterParamPanel(QWidget):
    paramChanged = Signal(str, object)

    def __init__(self, param_map: dict, values: dict, key_event_filter: KeyEventFilter, parent=None):
        super().__init__(parent)
        self._building = True
        layout = QFormLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        widgets = []
        for param_name, (mpv_name, param_type, param_range) in param_map.items():
            field = self._make_field(param_name, param_type, param_range, values.get(param_name))
            layout.addRow(self._label_for(param_name), field)
            widgets.append(field)
        key_event_filter.install_on_widgets(widgets)
        self._building = False

    @staticmethod
    def _label_for(param_name: str) -> str:
        return param_name.replace("-", " ").replace("_", " ").title()

    def _make_field(self, param_name: str, param_type: type, param_range: tuple, current_value):
        if param_type is float:
            field = QDoubleSpinBox()
            field.setDecimals(3)
            if param_range:
                min_v, max_v, step, default = param_range
                field.setRange(min_v, max_v)
                field.setSingleStep(step)
                field.setValue(current_value if current_value is not None else default)
            field.valueChanged.connect(lambda v, p=param_name: self._emit(p, float(v)))
            return field

        if param_type is int:
            field = QSpinBox()
            if param_range:
                min_v, max_v, step, default = param_range
                field.setRange(int(min_v), int(max_v))
                field.setSingleStep(int(step))
                field.setValue(int(current_value) if current_value is not None else int(default))
            field.valueChanged.connect(lambda v, p=param_name: self._emit(p, int(v)))
            return field

        if param_range:
            field = QComboBox()
            field.addItems(list(param_range))
            if current_value is not None:
                idx = field.findText(str(current_value))
                if idx >= 0:
                    field.setCurrentIndex(idx)
            field.currentTextChanged.connect(lambda v, p=param_name: self._emit(p, v))
            return field

        field = QLineEdit(str(current_value) if current_value is not None else "")
        field.editingFinished.connect(lambda p=param_name, w=field: self._emit(p, w.text()))
        return field

    def _emit(self, param_name: str, value):
        if self._building:
            return
        self.paramChanged.emit(param_name, value)


class AudioFiltersWidget(QWidget):
    def __init__(self, parent=None, player=None):
        super().__init__(parent)
        self.player = player
        self._building = False
        self._names = []
        self._key_event_filter = KeyEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.list_tab = ListTabCtrl(self)
        layout.addWidget(self.list_tab)
        self.list_tab.tabLabels.itemChanged.connect(self._on_item_changed)
        self._key_event_filter.install_on_widgets([self.list_tab.tabLabels])

    def set_player(self, player):
        self.player = player
        self._populate()

    def _populate(self):
        if not self.player:
            return
        self._building = True
        try:
            self.list_tab.deleteTabs()
            self._names = []
            for name in self.player.get_audio_filter_names():
                spec = self.player.get_audio_filter_param_spec(name)
                if spec is None:
                    continue
                param_map, values = spec
                panel = FilterParamPanel(param_map, values, self._key_event_filter, self)
                panel.paramChanged.connect(lambda p, v, n=name: self._on_param_changed(n, p, v))
                self.list_tab.addTab(_(name), panel)
                self._names.append(name)
                if self.player.is_audio_filter_enabled(name):
                    tab = self.list_tab.getTab(len(self._names) - 1)
                    if tab is not None:
                        # Only marks it enabled -- ListTabCtrl no longer ties
                        # panel visibility to check state, so this doesn't
                        # show anything by itself.
                        tab.setActivated(True)
            if self._names:
                self.list_tab.tabLabels.setCurrentRow(0)
        finally:
            self._building = False

    def _on_item_changed(self, item):
        if self._building or not self.player:
            return
        index = self.list_tab.tabLabels.row(item)
        if 0 <= index < len(self._names):
            enabled = item.checkState() == Qt.CheckState.Checked
            self.player.set_audio_filter_enabled(self._names[index], enabled)

    def _on_param_changed(self, name: str, param_name: str, value):
        if self._building or not self.player:
            return
        self.player.set_audio_filter_parameter(name, param_name, value)

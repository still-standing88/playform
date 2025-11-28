from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QSpinBox, QDoubleSpinBox, QComboBox, QFrame,
                               QSizePolicy, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from gui_controls.toggle_button import ToggleButton
from gui_controls.list_tab import ListTabCtrl


class FilterParameter(QWidget):
    valueChanged = Signal(str, object)
    
    def __init__(self, param_name, param_config, parent=None):
        super().__init__(parent)
        self.param_name = param_name
        self.param_config = param_config
        self.control_widget = None
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)
        
        self.name_label = QLabel(self.param_name, self)
        self.name_label.setFixedWidth(100)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.name_label)
        
        param_type = self.param_config[0]
        param_data = self.param_config[1]
        
        if param_type == 'str':
            self.control_widget = QComboBox(self)
            self.control_widget.addItems(param_data)
            self.control_widget.currentTextChanged.connect(self.on_value_changed)
            
        elif param_type == 'int':
            min_val, max_val, offset, default = param_data
            self.control_widget = QSpinBox(self)
            self.control_widget.setMinimum(min_val)
            self.control_widget.setMaximum(max_val)
            self.control_widget.setSingleStep(offset)
            self.control_widget.setValue(default)
            self.control_widget.valueChanged.connect(self.on_value_changed)
            
        elif param_type == 'float':
            min_val, max_val, offset, default = param_data
            self.control_widget = QDoubleSpinBox(self)
            self.control_widget.setMinimum(min_val)
            self.control_widget.setMaximum(max_val)
            self.control_widget.setSingleStep(offset)
            self.control_widget.setValue(default)
            self.control_widget.setDecimals(2)
            self.control_widget.valueChanged.connect(self.on_value_changed)
            
        if self.control_widget:
            self.control_widget.setAccessibleName(f"{self.param_name} control")
            layout.addWidget(self.control_widget, 1)
            
    def on_value_changed(self, value):
        self.valueChanged.emit(self.param_name, value)
        
    def get_value(self):
        if isinstance(self.control_widget, QComboBox):
            return self.control_widget.currentText()
        elif isinstance(self.control_widget, (QSpinBox, QDoubleSpinBox)):
            return self.control_widget.value()
        return None
        
    def set_value(self, value):
        if isinstance(self.control_widget, QComboBox):
            index = self.control_widget.findText(str(value))
            if index >= 0:
                self.control_widget.setCurrentIndex(index)
        elif isinstance(self.control_widget, (QSpinBox, QDoubleSpinBox)):
            self.control_widget.setValue(value)

class FilterWidget(QWidget):
    filterActivated = Signal(str, bool)
    parameterChanged = Signal(str, str, object)
    
    def __init__(self, filter_name, filter_config, activate_callback=None, 
                 parameter_callback=None, parent=None):
        super().__init__(parent)
        
        self.filter_name = filter_name
        self.filter_config = filter_config
        self.activate_callback = activate_callback
        self.parameter_callback = parameter_callback
        self.is_active = False
        
        self.parameter_widgets = {}
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        header_layout = QHBoxLayout()
        
        self.filter_label = QLabel(self.filter_name, self)
        self.filter_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        header_layout.addWidget(self.filter_label)
        
        header_layout.addStretch()
        
        self.activate_toggle = ToggleButton("Activate", self)
        self.activate_toggle.setFixedSize(80, 25)
        header_layout.addWidget(self.activate_toggle)
        
        layout.addLayout(header_layout)
        
        separator = QFrame(self)
        separator.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Sunken)

        layout.addWidget(separator)
        
        self.parameters_widget = QWidget(self)
        self.parameters_layout = QVBoxLayout(self.parameters_widget)
        self.parameters_layout.setContentsMargins(0, 0, 0, 0)
        self.parameters_layout.setSpacing(3)
        
        for param_name, param_config in self.filter_config.items():
            param_widget = FilterParameter(param_name, param_config, self)
            param_widget.valueChanged.connect(self.on_parameter_changed)
            self.parameter_widgets[param_name] = param_widget
            self.parameters_layout.addWidget(param_widget)
            
        layout.addWidget(self.parameters_widget)
        
        self.parameters_widget.setEnabled(False)
        
    def connect_signals(self):
        self.activate_toggle.actuated.connect(self.on_filter_toggled)
        
    def on_filter_toggled(self, activated):
        self.is_active = activated
        self.parameters_widget.setEnabled(activated)
        
        if self.activate_callback:
            self.activate_callback(activated)
            
        self.filterActivated.emit(self.filter_name, activated)
        
    def on_parameter_changed(self, param_name, value):
        if self.parameter_callback:
            self.parameter_callback(param_name, value)
            
        self.parameterChanged.emit(self.filter_name, param_name, value)
        
    def get_parameter_value(self, param_name):
        if param_name in self.parameter_widgets:
            return self.parameter_widgets[param_name].get_value()
        return None
        
    def set_parameter_value(self, param_name, value):
        if param_name in self.parameter_widgets:
            self.parameter_widgets[param_name].set_value(value)
            
    def get_all_parameters(self):
        return {name: widget.get_value() 
                for name, widget in self.parameter_widgets.items()}
                
    def set_filter_active(self, active):
        self.activate_toggle.setActuated(active)

class FiltersWidget(QWidget):
    filterActivated = Signal(str, bool)
    parameterChanged = Signal(str, str, object)
    filtersToggled = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.filter_widgets = {}
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Filters", self)
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.title_label.setAccessibleName("Filters section")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.toggle_btn = ToggleButton("Show", self)
        self.toggle_btn.setFixedSize(60, 25)
        self.toggle_btn.setActuated(True)
        header_layout.addWidget(self.toggle_btn)
        
        layout.addLayout(header_layout)
        
        self.filters_tab = ListTabCtrl(self)
        self.filters_tab.setAccessibleName("Filters list")
        self.filters_tab.setAccessibleDescription("List of available video filters")
        self.filters_tab.setVisible(False)
        layout.addWidget(self.filters_tab, 1)
        
    def connect_signals(self):
        self.toggle_btn.actuated.connect(self.toggle_filters)
        
    def toggle_filters(self, hidden):
        self.filters_tab.setVisible(not hidden)
        
        if hidden:
            self.toggle_btn.setText("Show")
        else:
            self.toggle_btn.setText("Hide")
            
        self.filtersToggled.emit(not hidden)
        
    def add_filter(self, filter_name, filter_config, activate_callback=None, 
                   parameter_callback=None):
        if filter_name in self.filter_widgets:
            print(f"Filter '{filter_name}' already exists")
            return
            
        filter_widget = FilterWidget(
            filter_name, filter_config, activate_callback, parameter_callback, self
        )
        
        filter_widget.filterActivated.connect(self.filterActivated.emit)
        filter_widget.parameterChanged.connect(self.parameterChanged.emit)
        
        self.filters_tab.addTab(filter_name, filter_widget)
        
        self.filter_widgets[filter_name] = filter_widget
        
    def remove_filter(self, filter_name):
        if filter_name not in self.filter_widgets:
            return
            
        index = self.filters_tab.indexOfTab(filter_name)
        if index >= 0:
            self.filters_tab.removeTab(index)
            
        del self.filter_widgets[filter_name]
        
    def get_filter_widget(self, filter_name):
        return self.filter_widgets.get(filter_name)
        
    def get_active_filters(self):
        return [name for name, widget in self.filter_widgets.items() 
                if widget.is_active]
                
    def clear_filters(self):
        self.filters_tab.deleteTabs()
        self.filter_widgets.clear()
        
    def set_filter_active(self, filter_name, active):
        if filter_name in self.filter_widgets:
            self.filter_widgets[filter_name].set_filter_active(active)
            
    def get_filter_parameters(self, filter_name):
        if filter_name in self.filter_widgets:
            return self.filter_widgets[filter_name].get_all_parameters()
        return {}
        
    def set_filter_parameter(self, filter_name, param_name, value):
        if filter_name in self.filter_widgets:
            self.filter_widgets[filter_name].set_parameter_value(param_name, value)
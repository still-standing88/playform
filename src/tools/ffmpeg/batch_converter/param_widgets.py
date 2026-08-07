from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QCheckBox, QPushButton, QFileDialog
)


def make_param_widget(parent, kind: str, choices=None, value_range=None, default=None, suffix: str = ""):
    if kind == "choice":
        combo = QComboBox(parent)
        for choice in choices or []:
            combo.addItem(str(choice), choice)
        index = combo.findData(default)
        combo.setCurrentIndex(index if index >= 0 else 0)
        return combo

    if kind == "bool":
        check = QCheckBox(parent)
        check.setChecked(bool(default))
        return check

    if kind == "int":
        spin = QSpinBox(parent)
        low, high = value_range or (-1000000, 1000000)
        spin.setRange(int(low), int(high))
        spin.setSuffix(suffix)
        spin.setValue(int(default) if default is not None else int(low))
        return spin

    if kind == "float":
        spin = QDoubleSpinBox(parent)
        low, high = value_range or (-1000000.0, 1000000.0)
        spin.setRange(float(low), float(high))
        spin.setDecimals(3)
        spin.setSuffix(suffix)
        spin.setValue(float(default) if default is not None else float(low))
        return spin

    if kind == "file":
        container = QWidget(parent)
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit(container)
        edit.setText(str(default or ""))
        browse = QPushButton(_("Browse..."), container)

        def _browse():
            path, _filter = QFileDialog.getOpenFileName(container, _("Select File"))
            if path:
                edit.setText(path)

        browse.clicked.connect(_browse)
        row.addWidget(edit)
        row.addWidget(browse)
        container._value_edit = edit
        return container

    edit = QLineEdit(parent)
    edit.setText(str(default) if default is not None else "")
    return edit


def read_param_widget(widget):
    if isinstance(widget, QComboBox):
        return widget.currentData()
    if isinstance(widget, QCheckBox):
        return widget.isChecked()
    if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
        return widget.value()
    if hasattr(widget, "_value_edit"):
        return widget._value_edit.text()
    if isinstance(widget, QLineEdit):
        return widget.text()
    return None

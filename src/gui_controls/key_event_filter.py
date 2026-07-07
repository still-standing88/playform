from PySide6.QtCore import QObject, Qt, QEvent
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (QApplication, QPushButton, QToolButton, QListWidget, QTreeWidget, QLineEdit, QTextEdit, QPlainTextEdit, 
                               QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QRadioButton, QSlider, QScrollBar, 
                               QListView, QTreeView, QTableWidget, QTableView, QAbstractItemView, QAbstractSpinBox,
                               QDial, QProgressBar, QTabWidget, QTabBar, QSplitter, QGroupBox, QFrame)
from typing import Dict, Callable, Union, List, Optional, Set
import logging

class ShortcutScope:
    GLOBAL = "global"
    CONTEXT_AWARE = "context_aware" 
    WIDGET_LOCAL = "widget_local"

class ShortcutManager(QObject):


    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.shortcuts: Dict[str, Dict] = {}
        self.widget_local_shortcuts: Dict[QObject, Dict[str, Callable]] = {}
        
        self.enabled = True
        self.debug_mode = False
        self.logger = logging.getLogger(__name__)
        
        self.input_widgets = {
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox
        }
        
        self.navigation_widgets = {
            QListWidget, QTreeWidget, QListView, QTreeView, 
            QTableWidget, QTableView, QAbstractItemView
        }
        
        self.clickable_widgets = {
            QPushButton, QToolButton, QCheckBox, QRadioButton
        }
        
        self.value_widgets = {
            QSpinBox, QDoubleSpinBox, QAbstractSpinBox,
            QSlider, QScrollBar, QDial
        }
        
        self.tab_widgets = {
            QTabWidget, QTabBar
        }
        
        self.container_widgets = {
            QSplitter
        }

    def add_global_shortcut(self, key_combination: str, callback: Callable, description: str = ""):
        normalized_combo = self._normalize_key_combination(key_combination)
        self.shortcuts[normalized_combo] = {
            'callback': callback,
            'scope': ShortcutScope.GLOBAL,
            'description': description
        }

    def add_context_shortcut(self, key_combination: str, callback: Callable, description: str = ""):
        normalized_combo = self._normalize_key_combination(key_combination)
        self.shortcuts[normalized_combo] = {
            'callback': callback,
            'scope': ShortcutScope.CONTEXT_AWARE,
            'description': description
        }

    def add_widget_shortcut(self, widget: QObject, key_combination: str, callback: Callable):
        if widget not in self.widget_local_shortcuts:
            self.widget_local_shortcuts[widget] = {}
        
        normalized_combo = self._normalize_key_combination(key_combination)
        self.widget_local_shortcuts[widget][normalized_combo] = callback

    def remove_shortcut(self, key_combination: str) -> bool:
        normalized_combo = self._normalize_key_combination(key_combination)
        if normalized_combo in self.shortcuts:
            del self.shortcuts[normalized_combo]
            return True
        return False

    def remove_widget_shortcut(self, widget: QObject, key_combination: str = None):
        if widget in self.widget_local_shortcuts:
            if key_combination:
                normalized_combo = self._normalize_key_combination(key_combination)
                self.widget_local_shortcuts[widget].pop(normalized_combo, None)
            else:
                del self.widget_local_shortcuts[widget]

    def clear_shortcuts(self):
        self.shortcuts.clear()
        self.widget_local_shortcuts.clear()

    def set_enabled(self, enabled: bool):
        self.enabled = enabled

    def set_debug_mode(self, debug: bool):
        self.debug_mode = debug
        if debug:
            logging.basicConfig(level=logging.INFO)

    def install_on_application(self):
        QApplication.instance().installEventFilter(self)

    def uninstall_from_application(self):
        QApplication.instance().removeEventFilter(self)

    def eventFilter(self, obj, event):
        if not self.enabled or event.type() != QEvent.KeyPress:
            return False

        return self._handle_key_press(event)

    def _handle_key_press(self, event) -> bool:
        key = event.key()
        modifiers = event.modifiers()

        if self._is_modifier_key(key):
            return False

        key_combo = self._create_key_combination(modifiers, key)
        focused_widget = QApplication.focusWidget()

        if self.debug_mode:
            widget_name = focused_widget.__class__.__name__ if focused_widget else "None"
            self.logger.info(f"Key: {key_combo}, Focused: {widget_name}")

        if focused_widget and focused_widget in self.widget_local_shortcuts:
            if key_combo in self.widget_local_shortcuts[focused_widget]:
                try:
                    self.widget_local_shortcuts[focused_widget][key_combo]()
                    return True
                except Exception as e:
                    if self.debug_mode:
                        self.logger.error(f"Error in widget shortcut: {e}")

        if key_combo in self.shortcuts:
            shortcut_info = self.shortcuts[key_combo]
            scope = shortcut_info['scope']
            
            if scope == ShortcutScope.GLOBAL:
                try:
                    shortcut_info['callback']()
                    return True
                except Exception as e:
                    if self.debug_mode:
                        self.logger.error(f"Error in global shortcut: {e}")
                        
            elif scope == ShortcutScope.CONTEXT_AWARE:
                if self._should_allow_context_shortcut(key_combo, focused_widget):
                    try:
                        shortcut_info['callback']()
                        return True
                    except Exception as e:
                        if self.debug_mode:
                            self.logger.error(f"Error in context shortcut: {e}")

        return False

    def _should_allow_context_shortcut(self, key_combo: str, focused_widget) -> bool:
        if not focused_widget:
            return True

        key_without_modifiers = key_combo.split('+')[-1]
        widget_type = type(focused_widget)

        if key_without_modifiers == "Space":
            if widget_type in self.clickable_widgets:
                return False
            if widget_type in self.tab_widgets:
                return False

        if key_without_modifiers == "Return" or key_without_modifiers == "Enter":
            if widget_type in self.clickable_widgets:
                return False

        if key_without_modifiers in ["Up", "Down"]:
            if widget_type in self.navigation_widgets:
                return False
            if widget_type in self.value_widgets:
                return False
            if widget_type in self.input_widgets and isinstance(focused_widget, QComboBox):
                return False
            if widget_type in self.tab_widgets:
                return False

        if key_without_modifiers in ["Left", "Right"]:
            if widget_type in self.navigation_widgets:
                return False
            if widget_type in self.value_widgets:
                return False
            if widget_type in self.tab_widgets:
                return False
            if widget_type in self.container_widgets:
                return False

        if key_without_modifiers in ["Home", "End"]:
            if widget_type in self.navigation_widgets:
                return False
            if widget_type in self.input_widgets:
                return False
            if widget_type in self.value_widgets:
                return False

        if key_without_modifiers in ["PageUp", "PageDown"]:
            if widget_type in self.navigation_widgets:
                return False
            if widget_type in self.value_widgets:
                return False

        if key_without_modifiers == "Tab":
            return False

        if key_without_modifiers == "Escape":
            if widget_type in self.input_widgets and isinstance(focused_widget, QComboBox):
                return False

        if key_without_modifiers in ["Plus", "Minus", "+", "-"]:
            if widget_type in self.value_widgets:
                return False

        if widget_type in self.input_widgets:
            if key_without_modifiers in ["Space", "Home", "End", "Left", "Right", "Backspace", "Delete"]:
                if not isinstance(focused_widget, QComboBox):
                    return False

        return True

    def _is_modifier_key(self, key) -> bool:
        modifier_keys = {
            Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta,
            Qt.Key_AltGr, Qt.Key_CapsLock, Qt.Key_NumLock, Qt.Key_ScrollLock
        }
        return key in modifier_keys

    def _create_key_combination(self, modifiers, key) -> str:
        parts = []
        
        if modifiers & Qt.ControlModifier:
            parts.append("Ctrl")
        if modifiers & Qt.AltModifier:
            parts.append("Alt")
        if modifiers & Qt.ShiftModifier:
            parts.append("Shift")
        if modifiers & Qt.MetaModifier:
            parts.append("Win")
        
        key_name = self._get_key_name(key)
        if key_name:
            parts.append(key_name)
        
        return "+".join(parts)

    def _normalize_key_combination(self, key_combination: str) -> str:
        if not key_combination:
            return ""
        
        parts = [part.strip() for part in key_combination.split('+')]
        normalized_parts = []
        
        modifier_order = ["Ctrl", "Alt", "Shift", "Win"]
        found_modifiers = []
        main_key = None
        
        for part in parts:
            part_lower = part.lower()
            
            if part_lower in ["ctrl", "control"]:
                found_modifiers.append("Ctrl")
            elif part_lower == "alt":
                found_modifiers.append("Alt")
            elif part_lower == "shift":
                found_modifiers.append("Shift")
            elif part_lower in ["win", "meta", "cmd", "super"]:
                found_modifiers.append("Win")
            else:
                if part in ["[", "]"]:
                    main_key = part
                elif part.lower() == "backspace":
                    main_key = "Backspace"
                elif len(part) == 1:
                    main_key = part.upper()
                else:
                    main_key = part.title()
        
        for modifier in modifier_order:
            if modifier in found_modifiers:
                normalized_parts.append(modifier)
        
        if main_key:
            normalized_parts.append(main_key)
        
        return "+".join(normalized_parts)

    def _get_key_name(self, key) -> str:
        special_keys = {
            Qt.Key_Escape: "Escape",
            Qt.Key_Tab: "Tab",
            Qt.Key_Backtab: "Backtab",
            Qt.Key_Backspace: "Backspace",
            Qt.Key_Return: "Return",
            Qt.Key_Enter: "Enter",
            Qt.Key_Insert: "Insert",
            Qt.Key_Delete: "Delete",
            Qt.Key_Pause: "Pause",
            Qt.Key_Print: "Print",
            Qt.Key_SysReq: "SysReq",
            Qt.Key_Clear: "Clear",
            Qt.Key_Home: "Home",
            Qt.Key_End: "End",
            Qt.Key_Left: "Left",
            Qt.Key_Up: "Up",
            Qt.Key_Right: "Right",
            Qt.Key_Down: "Down",
            Qt.Key_PageUp: "PageUp",
            Qt.Key_PageDown: "PageDown",
            Qt.Key_Space: "Space",
            Qt.Key_BracketLeft: "[",
            Qt.Key_BracketRight: "]",
        }
        
        if key in special_keys:
            return special_keys[key]
        
        if Qt.Key_F1 <= key <= Qt.Key_F35:
            return f"F{key - Qt.Key_F1 + 1}"
        
        if 32 <= key <= 126:
            return chr(key).upper()
        
        if Qt.Key_0 <= key <= Qt.Key_9:
            return chr(key)
        
        try:
            sequence = QKeySequence(key)
            return sequence.toString()
        except:
            return f"Key_{key}"


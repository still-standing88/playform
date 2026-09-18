from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence


KEY_NAMES = {
    Qt.Key.Key_Escape: "Escape",
    Qt.Key.Key_Tab: "Tab",
    Qt.Key.Key_Backtab: "Backtab",
    Qt.Key.Key_Backspace: "Backspace",
    Qt.Key.Key_Return: "Return",
    Qt.Key.Key_Enter: "Enter",
    Qt.Key.Key_Insert: "Insert",
    Qt.Key.Key_Delete: "Delete",
    Qt.Key.Key_Pause: "Pause",
    Qt.Key.Key_Print: "Print",
    Qt.Key.Key_SysReq: "SysReq",
    Qt.Key.Key_Clear: "Clear",
    Qt.Key.Key_Home: "Home",
    Qt.Key.Key_End: "End",
    Qt.Key.Key_Left: "Left",
    Qt.Key.Key_Up: "Up",
    Qt.Key.Key_Right: "Right",
    Qt.Key.Key_Down: "Down",
    Qt.Key.Key_PageUp: "Page Up",
    Qt.Key.Key_PageDown: "Page Down",
    Qt.Key.Key_Space: "Space",
    Qt.Key.Key_BracketLeft: "[",
    Qt.Key.Key_BracketRight: "]",
}

# A hotkey has to be stored spelled exactly the way key_name() spells a live
# press -- ShortcutManager builds "Ctrl+Shift+P"-style strings from these
# names and compares them literally against the config. Qt's parser accepts
# several other spellings for the same key ("Esc", "Del", "PgUp" -- but not
# "PageUp"), so every one of those folds back onto a single form here.
KEY_NAME_ALIASES = {name.casefold(): name for name in KEY_NAMES.values()}
KEY_NAME_ALIASES.update({
    "esc": "Escape",
    "del": "Delete",
    "ins": "Insert",
    "pgup": "Page Up",
    "pgdn": "Page Down",
    "pageup": "Page Up",
    "pagedown": "Page Down",
})


def key_name(key) -> str:
    if key in KEY_NAMES:
        return KEY_NAMES[key]

    if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F35:
        return f"F{key - Qt.Key.Key_F1 + 1}"

    if 32 <= key <= 126:
        return chr(key).upper()

    if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
        return chr(key)

    try:
        return QKeySequence(key).toString()
    except Exception:
        return f"Key_{key}"

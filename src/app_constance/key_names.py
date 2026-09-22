import warnings

from PySide6.QtCore import Qt, QKeyCombination
from PySide6.QtGui import QKeySequence


# The only five keys this app spells differently from Qt. The stored spelling
# predates the table being generated, and key_config.cfg files carry it.
KEY_NAME_OVERRIDES = {
    Qt.Key.Key_Escape: "Escape",
    Qt.Key.Key_Insert: "Insert",
    Qt.Key.Key_Delete: "Delete",
    Qt.Key.Key_PageUp: "Page Up",
    Qt.Key.Key_PageDown: "Page Down",
}


def _build_key_names() -> dict:
    """Every key Qt can report, named the way Qt names it. Walking the enum is
    what makes the table exhaustive -- a key missing from it can be stored in
    one spelling and compared in another, which is a hotkey that never fires."""
    names = {}
    with warnings.catch_warnings():
        # Qt marks a few of its own key values deprecated, and warns on each
        # one, but reading them is still how they arrive from the platform.
        warnings.simplefilter("ignore", DeprecationWarning)
        for member in Qt.Key:
            text = QKeySequence(QKeyCombination(Qt.KeyboardModifier.NoModifier, member)).toString()
            if text:
                names[member] = text
    names.update(KEY_NAME_OVERRIDES)
    return names


KEY_NAMES = _build_key_names()

# A hotkey has to be stored spelled exactly the way key_name() spells a live
# press -- ShortcutManager builds "Ctrl+Shift+P"-style strings from these
# names and compares them literally against the config. Every name in the
# table is an accepted input, and the extras below cover the spellings Qt
# uses for the five overrides above ("Esc", "Del", "PgUp" -- but not
# "PageUp"), so every one of those folds back onto a single form here.
KEY_NAME_ALIASES = {name.casefold(): name for name in KEY_NAMES.values()}
KEY_NAME_ALIASES.update({
    "esc": "Escape",
    "ins": "Insert",
    "del": "Delete",
    "pgup": "Page Up",
    "pgdn": "Page Down",
    "pgdown": "Page Down",
    "pageup": "Page Up",
    "pagedown": "Page Down",
})


def key_name(key) -> str:
    return KEY_NAMES.get(key, "")

from media_core.ffmpeg.effects_catalog import effects_for_branch, categories_for_branch, get_effect
from gui_controls.effect_dialogs import EffectSelectionDialog
from utilities.i18n import N_

_BRANCH_TITLES = {
    "edits": (N_("Add Edit"), N_("Available Edits")),
    "filters": (N_("Add Filter"), N_("Available Filters")),
}


class EffectPickerDialog(EffectSelectionDialog):
    """Batch Converter's category-tree effect picker -- a thin wrapper
    around the shared gui_controls.effect_dialogs.EffectSelectionDialog,
    bound to media_core.ffmpeg.effects_catalog's branch-scoped catalog.
    Parameter configuration happens in EffectEditDialog, not here."""

    def __init__(self, branch: str, parent=None, initial_effect_id: str = None, initial_values: dict = None):
        self.branch = branch
        dialog_title, list_title = _BRANCH_TITLES.get(branch, (N_("Add Effect"), N_("Available Effects")))
        super().__init__(
            entries=effects_for_branch(branch),
            categories_fn=lambda: categories_for_branch(branch),
            get_entry_fn=get_effect,
            parent=parent,
            title=_(dialog_title),
            list_title=_(list_title),
        )

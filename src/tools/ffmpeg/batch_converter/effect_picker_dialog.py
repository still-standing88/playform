from media_core.ffmpeg.effects_catalog import effects_for_branch, categories_for_branch, get_effect
from gui_controls.categorized_effect_picker import CategorizedEffectPickerDialog

_BRANCH_TITLES = {
    "edits": ("Add Edit", "Available Edits"),
    "filters": ("Add Filter", "Available Filters"),
}


class EffectPickerDialog(CategorizedEffectPickerDialog):
    """Batch Converter's category-tree effect picker -- a thin wrapper
    around the shared gui_controls.categorized_effect_picker dialog,
    bound to media_core.ffmpeg.effects_catalog's branch-scoped catalog.
    """

    def __init__(self, branch: str, parent=None, initial_effect_id: str = None, initial_values: dict = None):
        self.branch = branch
        dialog_title, list_title = _BRANCH_TITLES.get(branch, ("Add Effect", "Available Effects"))
        super().__init__(
            entries=effects_for_branch(branch),
            categories_fn=lambda: categories_for_branch(branch),
            get_entry_fn=get_effect,
            parent=parent,
            initial_id=initial_effect_id,
            initial_values=initial_values,
            title=_(dialog_title),
            list_title=_(list_title),
        )

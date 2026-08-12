import os
from utilities.functions import get_app_path


class ToolbarConfig:

    SETTINGS_KEY = "toolbar_config"

    def __init__(self):
        # Legacy path only kept around for the one-shot migration below --
        # the toolbar config itself now lives in app_settings (user.sqlite3).
        self._legacy_config_file = os.path.join(get_app_path(), 'data', 'toolbar_config.json')
        self.default_tools = []

        self.available_tools = {
            'batch_converter': 'Batch Converter',
            'extractor': 'Media Extractor',
            'tag_editor': 'Tag Editor',
            'thumbnail_generator': 'Thumbnail Generator',
            'subtitle_converter': 'Subtitle Converter',
            'subtitle_editor': 'Subtitle Editor'
        }

    def save_config(self, selected_tools: list[str]) -> bool:
        from app_db import app_settings
        return app_settings.set(self.SETTINGS_KEY, {'toolbar_tools': selected_tools})

    def load_config(self) -> list[str]:
        from app_db import app_settings
        from app_db.settings_store import migrate_json_file
        data = migrate_json_file(app_settings, self._legacy_config_file, self.SETTINGS_KEY)
        if not data:
            return self.default_tools.copy()
        return data.get('toolbar_tools', self.default_tools.copy())

    def get_default_tools(self) -> list[str]:
        return self.default_tools.copy()

    def get_available_tools(self) -> dict[str, str]:
        return self.available_tools.copy()


toolbar_config = ToolbarConfig()

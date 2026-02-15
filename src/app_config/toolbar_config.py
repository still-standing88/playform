import json
import os
from typing import Optional
from utilities.functions import get_app_path


class ToolbarConfig:
    
    def __init__(self):
        self.config_file = os.path.join(get_app_path(), 'data', 'toolbar_config.json')
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
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump({'toolbar_tools': selected_tools}, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save toolbar config: {e}")
            return False
    
    def load_config(self) -> list[str]:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    return data.get('toolbar_tools', self.default_tools.copy())
            except Exception as e:
                print(f"Failed to load toolbar config: {e}")
                return self.default_tools.copy()
        return self.default_tools.copy()
    
    def get_default_tools(self) -> list[str]:
        return self.default_tools.copy()
    
    def get_available_tools(self) -> dict[str, str]:
        return self.available_tools.copy()


toolbar_config = ToolbarConfig()

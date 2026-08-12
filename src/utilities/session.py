import json
import os
from typing import Optional
from utilities.functions import get_app_path


class DockPanelSession:
    
    def __init__(self):
        self.session_file = os.path.join(get_app_path(), 'data', 'dock_session.json')
        self.default_config = {
            'recents_favorites': True,
            'explorer': False,
            'player': True,
            'playlists': False,
            'radio': False,
            'podcast': False,
            'debug_console': False,
            'sidebar_hidden': False,
            'controls_minimized': False
        }
    
    def save_session(self, dock_states: dict[str, bool]) -> bool:
        try:
            os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
            with open(self.session_file, 'w') as f:
                json.dump(dock_states, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save dock session: {e}")
            return False
    
    def load_session(self) -> dict[str, bool]:
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load dock session: {e}")
                return self.default_config.copy()
        return self.default_config.copy()
    
    def get_default_config(self) -> dict[str, bool]:
        return self.default_config.copy()


dock_session = DockPanelSession()

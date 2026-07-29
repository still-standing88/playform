import json
import os
from typing import Any, Dict, List, Optional, Tuple, cast


class PlaybackStateManager:
    def __init__(self, data_dir: str):
        self._data_dir = data_dir
        os.makedirs(self._data_dir, exist_ok=True)

        self.bookmarks: Dict[str, List[float]] = {}
        self.last_positions: Dict[str, float] = {}
        self.repeat_loops: Dict[str, List[Tuple[Optional[float], Optional[float]]]] = {}

    @property
    def playback_state_path(self) -> str:
        return os.path.join(self._data_dir, "playback_state.json")

    @property
    def bookmarks_path(self) -> str:
        return os.path.join(self._data_dir, "bookmarks.json")

    @property
    def repeat_loops_path(self) -> str:
        return os.path.join(self._data_dir, "repeat_loops.json")

    @property
    def last_positions_path(self) -> str:
        return os.path.join(self._data_dir, "last_positions.json")

    def load_all(self) -> None:
        if os.path.exists(self.playback_state_path):
            self._load_consolidated()
        else:
            self._migrate_from_separate_files()

    def _load_consolidated(self) -> None:
        data = self._load_json(self.playback_state_path, default={})
        
        self.bookmarks = {}
        self.last_positions = {}
        self.repeat_loops = {}
        
        for file_path, state in data.items():
            if isinstance(state, dict):
                if "bookmarks" in state and isinstance(state["bookmarks"], list):
                    self.bookmarks[file_path] = state["bookmarks"]
                if "last_position" in state and isinstance(state["last_position"], (int, float)):
                    self.last_positions[file_path] = float(state["last_position"])
                if "loops" in state and isinstance(state["loops"], list):
                    self.repeat_loops[file_path] = [tuple(loop) if isinstance(loop, list) else loop for loop in state["loops"]]

    def _migrate_from_separate_files(self) -> None:
        old_bookmarks = cast(Dict[str, List[float]], self._load_json(self.bookmarks_path, default={}))
        old_positions = cast(Dict[str, float], self._load_json(self.last_positions_path, default={}))
        old_loops = cast(
            Dict[str, List[Tuple[Optional[float], Optional[float]]]],
            self._load_json(self.repeat_loops_path, default={}),
        )
        
        self.bookmarks = old_bookmarks
        self.last_positions = old_positions
        self.repeat_loops = old_loops
        
        self._save_consolidated()
        
        try:
            if os.path.exists(self.bookmarks_path):
                os.remove(self.bookmarks_path)
            if os.path.exists(self.last_positions_path):
                os.remove(self.last_positions_path)
            if os.path.exists(self.repeat_loops_path):
                os.remove(self.repeat_loops_path)
        except:
            pass

    def _save_consolidated(self) -> None:
        all_files = set(self.bookmarks.keys()) | set(self.last_positions.keys()) | set(self.repeat_loops.keys())
        
        data = {}
        for file_path in all_files:
            state = {}
            
            if file_path in self.last_positions:
                state["last_position"] = self.last_positions[file_path]
            
            if file_path in self.bookmarks:
                state["bookmarks"] = self.bookmarks[file_path]
            
            if file_path in self.repeat_loops:
                state["loops"] = self.repeat_loops[file_path]
            
            if state:
                data[file_path] = state
        
        self._save_json(self.playback_state_path, data)

    def save_bookmarks(self) -> None:
        self._save_consolidated()

    def load_bookmarks(self) -> None:
        self.load_all()

    def save_repeat_loops(self) -> None:
        self._save_consolidated()

    def load_repeat_loops(self) -> None:
        self.load_all()

    def save_last_positions(self) -> None:
        self._save_consolidated()

    def load_last_positions(self) -> None:
        self.load_all()

    def get_bookmarks(self, file_path: Optional[str]) -> List[float]:
        if not file_path:
            return []
        if file_path not in self.bookmarks:
            return []
        return list(self.bookmarks[file_path])

    def clear_bookmarks(self, file_path: Optional[str]) -> bool:
        if not file_path:
            return False
        if file_path not in self.bookmarks:
            return False
        del self.bookmarks[file_path]
        self.save_bookmarks()
        return True

    def add_bookmark(self, file_path: Optional[str], position: float) -> bool:
        if not file_path:
            return False
        if file_path not in self.bookmarks:
            self.bookmarks[file_path] = []
        self.bookmarks[file_path].append(position)
        self.bookmarks[file_path].sort()
        self.save_bookmarks()
        return True

    def update_bookmark(self, file_path: Optional[str], index: int, position: float) -> bool:
        if not file_path:
            return False
        if file_path not in self.bookmarks:
            return False
        bookmarks = self.bookmarks[file_path]
        if index < 0 or index >= len(bookmarks):
            return False
        bookmarks[index] = position
        bookmarks.sort()
        self.save_bookmarks()
        return True

    def delete_bookmark(self, file_path: Optional[str], index: int) -> bool:
        if not file_path:
            return False
        if file_path not in self.bookmarks:
            return False
        bookmarks = self.bookmarks[file_path]
        if index < 0 or index >= len(bookmarks):
            return False
        del bookmarks[index]
        self.save_bookmarks()
        return True

    def get_loops(self, file_path: Optional[str]) -> List[Tuple[Optional[float], Optional[float]]]:
        if not file_path:
            return []
        if file_path not in self.repeat_loops:
            return []
        return list(self.repeat_loops[file_path])

    def clear_all_loops(self, file_path: Optional[str]) -> bool:
        if not file_path:
            return False
        if file_path not in self.repeat_loops:
            return False
        self.repeat_loops[file_path] = []
        self.save_repeat_loops()
        return True

    def add_loop_start(self, file_path: Optional[str], position: float) -> bool:
        if not file_path:
            return False
        if file_path not in self.repeat_loops:
            self.repeat_loops[file_path] = []
        if self.is_position_in_existing_loop(file_path, position):
            return False
        self.repeat_loops[file_path].append((position, None))
        self.save_repeat_loops()
        return True

    def add_loop_end(self, file_path: Optional[str], position: float, exclude_index: int = -1) -> Optional[int]:
        if not file_path:
            return None
        if file_path not in self.repeat_loops:
            return None
        loops = self.repeat_loops[file_path]
        if not loops:
            return None
        for i in range(len(loops) - 1, -1, -1):
            if loops[i][1] is None:
                loop_start = loops[i][0]
                if loop_start is None or position <= loop_start:
                    return None
                if self.would_loop_intersect(file_path, loop_start, position, exclude_index=i):
                    return None
                loops[i] = (loop_start, position)
                self.save_repeat_loops()
                return i
        return None

    def update_loop(self, file_path: Optional[str], index: int, start: float, end: float) -> bool:
        if not file_path:
            return False
        if file_path not in self.repeat_loops:
            return False
        loops = self.repeat_loops[file_path]
        if index < 0 or index >= len(loops):
            return False
        if start is None or end is None or end <= start:
            return False
        if self.would_loop_intersect(file_path, start, end, exclude_index=index):
            return False
        loops[index] = (start, end)
        self.save_repeat_loops()
        return True

    def delete_loop(self, file_path: Optional[str], index: int) -> bool:
        if not file_path:
            return False
        if file_path not in self.repeat_loops:
            return False
        loops = self.repeat_loops[file_path]
        if index < 0 or index >= len(loops):
            return False
        del loops[index]
        self.save_repeat_loops()
        return True

    def clear_repeat_loop(self, file_path: Optional[str], current_loop_index: int) -> int:
        if not file_path:
            return -1
        if file_path not in self.repeat_loops:
            return -1
        loops = self.repeat_loops[file_path]
        if not loops:
            return -1

        complete_loops = [(i, start, end) for i, (start, end) in enumerate(loops) if start is not None and end is not None]
        if not complete_loops:
            incomplete_loops = [i for i, (start, end) in enumerate(loops) if start is None or end is None]
            if incomplete_loops:
                del loops[incomplete_loops[-1]]
            self.save_repeat_loops()
            return -1

        if current_loop_index == -1 or current_loop_index >= len(complete_loops):
            current_loop_index = len(complete_loops) - 1

        if 0 <= current_loop_index < len(complete_loops):
            actual_index, _, _ = complete_loops[current_loop_index]
            del loops[actual_index]

            complete_count = len([l for l in loops if l[0] is not None and l[1] is not None])
            if complete_count == 0:
                current_loop_index = -1
            else:
                current_loop_index = max(0, min(current_loop_index, complete_count - 1))

        self.save_repeat_loops()
        return current_loop_index

    def is_position_in_existing_loop(self, file_path: Optional[str], position: float) -> bool:
        if not file_path:
            return False
        if file_path not in self.repeat_loops:
            return False
        loops = self.repeat_loops[file_path]
        for loop_start, loop_end in loops:
            if loop_start is not None and loop_end is not None:
                if loop_start <= position <= loop_end:
                    return True
        return False

    def would_loop_intersect(self, file_path: Optional[str], new_start: float, new_end: float, exclude_index: int = -1) -> bool:
        if not file_path:
            return False
        if file_path not in self.repeat_loops:
            return False
        loops = self.repeat_loops[file_path]
        for i, (loop_start, loop_end) in enumerate(loops):
            if i == exclude_index:
                continue
            if loop_start is not None and loop_end is not None:
                if (
                    new_start <= loop_start <= new_end
                    or new_start <= loop_end <= new_end
                    or loop_start <= new_start <= loop_end
                    or loop_start <= new_end <= loop_end
                ):
                    return True
        return False

    def should_loop_playback(
        self,
        file_path: Optional[str],
        current_position: float,
        is_user_seeking: bool,
        last_loop_trigger_time: float,
        last_known_position: float,
    ) -> Tuple[Optional[float], float, float]:
        if not file_path:
            return None, last_loop_trigger_time, last_known_position
        if file_path not in self.repeat_loops:
            return None, last_loop_trigger_time, last_known_position

        if is_user_seeking:
            return None, last_loop_trigger_time, current_position

        import time

        current_time = time.time()
        if current_time - last_loop_trigger_time < 1.0:
            return None, last_loop_trigger_time, current_position

        position_delta = current_position - last_known_position
        if abs(position_delta) > 2.0:
            return None, last_loop_trigger_time, current_position

        loops = self.repeat_loops[file_path]
        for loop_start, loop_end in loops:
            if loop_start is not None and loop_end is not None:
                if last_known_position < loop_end and current_position >= loop_end:
                    if position_delta > 0 and position_delta < 2.0:
                        last_loop_trigger_time = current_time
                        return loop_start, last_loop_trigger_time, loop_start

        return None, last_loop_trigger_time, current_position

    def save_last_position(self, file_path: Optional[str], position: float) -> bool:
        if not file_path:
            return False
        self.last_positions[file_path] = position
        self.save_last_positions()
        return True

    def get_last_position(self, file_path: Optional[str]) -> Optional[float]:
        if not file_path:
            return None
        if file_path not in self.last_positions:
            return None
        pos = self.last_positions[file_path]
        if isinstance(pos, (int, float)) and pos >= 0:
            return float(pos)
        return None

    def _save_json(self, path: str, data: object) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load_json(self, path: str, default: Any) -> Any:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return default

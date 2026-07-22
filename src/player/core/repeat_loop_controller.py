from typing import List, Optional, Tuple


class RepeatLoopController:
    """A-B repeat-loop set/clear/jump/persist logic extracted from PlayerControls.
    Operates directly on the owning PlayerControls' state (_current_file,
    _repeat_loops, _state, _is_user_seeking, ...) rather than duplicating it."""

    def __init__(self, controls):
        self._c = controls

    def set_loop_start(self):
        c = self._c
        if not c._current_file:
            return
        current_pos = float(c.get_seek_position())
        self.set_loop_start_precise(current_pos)

    def set_loop_end(self):
        c = self._c
        if not c._current_file:
            return
        current_pos = float(c.get_seek_position())
        self.set_loop_end_precise(current_pos)

    def set_loop_start_precise(self, position: float):
        c = self._c
        if not c._current_file:
            return

        c._state.repeat_loops = c._repeat_loops
        if c._state.add_loop_start(c._current_file, position):
            c._repeat_loops = c._state.repeat_loops

    def set_loop_end_precise(self, position: float):
        c = self._c
        if not c._current_file:
            return

        c._state.repeat_loops = c._repeat_loops
        loop_index = c._state.add_loop_end(c._current_file, position)
        if loop_index is None:
            return
        c._repeat_loops = c._state.repeat_loops
        c._current_loop_index = loop_index

        loops = c._repeat_loops.get(c._current_file, [])
        loop_start = loops[loop_index][0] if 0 <= loop_index < len(loops) else None
        if loop_start is not None:
            c._is_user_seeking = True
            c.set_seek_position(int(loop_start))
            c.seekChanged.emit(int(loop_start))
            c._is_user_seeking = False

    def clear_repeat_loop(self):
        c = self._c
        if not c._current_file:
            return

        c._state.repeat_loops = c._repeat_loops
        c._current_loop_index = c._state.clear_repeat_loop(c._current_file, c._current_loop_index)
        c._repeat_loops = c._state.repeat_loops

    def clear_all_repeat_loops(self):
        c = self._c
        if not c._current_file:
            return
        c._state.repeat_loops = c._repeat_loops
        if c._state.clear_all_loops(c._current_file):
            c._repeat_loops = c._state.repeat_loops
            c._current_loop_index = -1

    def get_current_loops(self) -> List[Tuple[Optional[float], Optional[float]]]:
        c = self._c
        if not c._current_file:
            return []
        c._state.repeat_loops = c._repeat_loops
        return c._state.get_loops(c._current_file)

    def update_loop_by_index(self, index: int, start: float, end: float):
        c = self._c
        if not c._current_file:
            return False
        c._state.repeat_loops = c._repeat_loops
        ok = c._state.update_loop(c._current_file, index, start, end)
        c._repeat_loops = c._state.repeat_loops
        if ok:
            c._current_loop_index = index
        return ok

    def delete_loop_by_index(self, index: int):
        c = self._c
        if not c._current_file:
            return False
        c._state.repeat_loops = c._repeat_loops
        ok = c._state.delete_loop(c._current_file, index)
        c._repeat_loops = c._state.repeat_loops
        if not ok:
            return False

        loops = c._repeat_loops.get(c._current_file, [])
        complete_count = len([l for l in loops if l[0] is not None and l[1] is not None])
        if complete_count == 0:
            c._current_loop_index = -1
        else:
            c._current_loop_index = max(0, min(c._current_loop_index, complete_count - 1))
        return True

    def should_loop_playback(self, current_position: float) -> Optional[float]:
        c = self._c
        if not c._current_file:
            return None
        c._state.repeat_loops = c._repeat_loops
        loop_pos, c._last_loop_trigger_time, c._last_known_position = c._state.should_loop_playback(
            c._current_file,
            current_position,
            c._is_user_seeking,
            c._last_loop_trigger_time,
            c._last_known_position,
        )
        c._repeat_loops = c._state.repeat_loops
        return loop_pos

    def is_position_in_existing_loop(self, position: float) -> bool:
        c = self._c
        if not c._current_file:
            return False
        c._state.repeat_loops = c._repeat_loops
        return c._state.is_position_in_existing_loop(c._current_file, position)

    def would_loop_intersect(self, new_start: float, new_end: float, exclude_index: int = -1) -> bool:
        c = self._c
        if not c._current_file:
            return False
        c._state.repeat_loops = c._repeat_loops
        return c._state.would_loop_intersect(c._current_file, new_start, new_end, exclude_index=exclude_index)

    def check_loop_position(self, current_position: float):
        c = self._c
        loop_position = self.should_loop_playback(current_position)
        if loop_position is not None:
            c.set_seek_position(int(loop_position))
            c.seekChanged.emit(int(loop_position))

    def check_current_position(self):
        c = self._c
        if c._current_file:
            current_pos = float(c.get_seek_position())
            self.check_loop_position(current_pos)

    def jump_to_previous_loop(self):
        c = self._c
        if not c._current_file or c._current_file not in c._repeat_loops:
            return

        loops = c._repeat_loops[c._current_file]
        complete_loops = [(i, start, end) for i, (start, end) in enumerate(loops) if start is not None and end is not None]

        if not complete_loops:
            return

        if c._current_loop_index == -1 or c._current_loop_index <= 0:
            c._current_loop_index = len(complete_loops) - 1
        else:
            c._current_loop_index -= 1

        _, loop_start, _ = complete_loops[c._current_loop_index]
        if loop_start is not None:
            c._is_user_seeking = True
            c.set_seek_position(int(loop_start))
            c.seekChanged.emit(int(loop_start))
            c._is_user_seeking = False

    def jump_to_next_loop(self):
        c = self._c
        if not c._current_file or c._current_file not in c._repeat_loops:
            return

        loops = c._repeat_loops[c._current_file]
        complete_loops = [(i, start, end) for i, (start, end) in enumerate(loops) if start is not None and end is not None]

        if not complete_loops:
            return

        if c._current_loop_index == -1 or c._current_loop_index >= len(complete_loops) - 1:
            c._current_loop_index = 0
        else:
            c._current_loop_index += 1

        _, loop_start, _ = complete_loops[c._current_loop_index]
        if loop_start is not None:
            c._is_user_seeking = True
            c.set_seek_position(int(loop_start))
            c.seekChanged.emit(int(loop_start))
            c._is_user_seeking = False

    def save_repeat_loops(self):
        c = self._c
        c._state.repeat_loops = c._repeat_loops
        c._state.save_repeat_loops()

    def load_repeat_loops(self):
        c = self._c
        c._state.load_repeat_loops()
        c._repeat_loops = c._state.repeat_loops

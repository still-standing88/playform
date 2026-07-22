class TimelineSyncController:
    """Translates between SegmentTimelineWidget's normalized [0,1] positions
    and PlayerControls' seconds-based bookmark/loop storage, and keeps the
    timeline widget's segments/markers in sync with them. Extracted out of
    PlayerWidget's _update_timeline_from_data/_on_timeline_* handlers. widget
    is the owning PlayerWidget instance."""

    def __init__(self, widget):
        self._widget = widget
        self._timeline_seg_map = {}
        self._timeline_marker_map = {}

    def update_timeline_from_data(self):
        widget = self._widget
        length = None
        try:
            if widget.player and widget.player.primary_instance is not None:
                length = float(widget.player.primary_instance.get_length())
        except Exception:
            length = None

        if not length or length <= 0:

            length = float(widget.player_controls.seek_slider.maximum() or 0)

        loops = widget.player_controls.get_current_loops()
        segments_norm = []
        for start, end in loops:
            if start is None or end is None:
                continue
            if length > 0:
                segments_norm.append((start / length, end / length))

        widget.timeline.setSegments(segments_norm)

        self._timeline_seg_map = {}
        for idx, seg in enumerate(widget.timeline.segments):
            self._timeline_seg_map[seg['id']] = idx

        bookmarks = widget.player_controls.get_bookmarks()
        markers_norm = []
        for pos in bookmarks:
            if length > 0:
                markers_norm.append(pos / length)

        widget.timeline.setMarkers(markers_norm)
        self._timeline_marker_map = {}
        for idx, m in enumerate(widget.timeline.markers):
            self._timeline_marker_map[m['id']] = idx

    def _norm_to_seconds(self, norm: float) -> float:
        widget = self._widget
        try:
            if widget.player and widget.player.primary_instance is not None:
                length = float(widget.player.primary_instance.get_length())
                return norm * length
        except Exception:
            pass
        return norm * float(widget.player_controls.seek_slider.maximum() or 0)

    def _seconds_to_norm(self, sec: float) -> float:
        widget = self._widget
        try:
            if widget.player and widget.player.primary_instance is not None:
                length = float(widget.player.primary_instance.get_length())
                if length > 0:
                    return sec / length
        except Exception:
            pass
        maxv = float(widget.player_controls.seek_slider.maximum() or 1)
        if maxv <= 0:
            return 0.0
        return sec / maxv

    def on_segment_added(self, start_norm: float, end_norm: float):
        widget = self._widget
        start_sec = self._norm_to_seconds(start_norm)
        end_sec = self._norm_to_seconds(end_norm)
        try:
            widget.player_controls.set_loop_start_precise(start_sec)
            widget.player_controls.set_loop_end_precise(end_sec)
        except Exception:
            pass
        self.update_timeline_from_data()

    def on_segment_updated(self, seg_id: int, start_norm: float, end_norm: float):
        widget = self._widget
        if seg_id in self._timeline_seg_map:
            loop_index = self._timeline_seg_map[seg_id]
            start_sec = self._norm_to_seconds(start_norm)
            end_sec = self._norm_to_seconds(end_norm)
            widget.player_controls.update_loop_by_index(loop_index, start_sec, end_sec)
            self.update_timeline_from_data()

    def on_segment_removed(self, seg_id: int):
        widget = self._widget
        if seg_id in self._timeline_seg_map:
            loop_index = self._timeline_seg_map[seg_id]
            widget.player_controls.delete_loop_by_index(loop_index)
            self.update_timeline_from_data()

    def on_segment_selected(self, seg_id: int):
        widget = self._widget
        if seg_id in self._timeline_seg_map:
            widget.player_controls._current_loop_index = self._timeline_seg_map[seg_id]

    def on_marker_added(self, pos_norm: float):
        widget = self._widget
        pos_sec = self._norm_to_seconds(pos_norm)
        widget.player_controls.add_bookmark_at_position(pos_sec)
        self.update_timeline_from_data()

    def on_marker_moved(self, marker_id: int, pos_norm: float):
        widget = self._widget
        if marker_id in self._timeline_marker_map:
            bm_index = self._timeline_marker_map[marker_id]
            pos_sec = self._norm_to_seconds(pos_norm)
            widget.player_controls.update_bookmark_at_index(bm_index, pos_sec)
            self.update_timeline_from_data()

    def on_marker_removed(self, marker_id: int):
        widget = self._widget
        if marker_id in self._timeline_marker_map:
            bm_index = self._timeline_marker_map[marker_id]
            widget.player_controls.delete_bookmark_at(bm_index)
            self.update_timeline_from_data()

    def on_marker_selected(self, marker_id: int):
        widget = self._widget
        if marker_id in self._timeline_marker_map:
            widget.player_controls._current_bookmark_index = self._timeline_marker_map[marker_id]

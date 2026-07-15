import os

from PySide6.QtCore import QThread, Signal


class SearchWorker(QThread):
    """Single, cancellable background thread for Explorer search. Both the
    live filesystem walk and the media-database query run here, off the UI
    thread, so searching a large folder or the whole media catalog can't
    block the GUI. Only one search runs at a time - starting a new one
    cancels and waits out whatever was already running."""

    results_ready = Signal(str, str, list)  # root_path, query, list[str] of file paths
    error = Signal(str, str)  # root_path, message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root_path = None
        self._query = None
        self._extensions = []
        self._use_db = False
        self._cancel = False

    def start_search(self, root_path: str, query: str, extensions, use_db: bool):
        self.cancel()
        self.wait()
        self._root_path = root_path
        self._query = query
        self._extensions = extensions
        self._use_db = use_db
        self._cancel = False
        self.start()

    def cancel(self):
        self._cancel = True

    def run(self):
        root_path, query = self._root_path, self._query
        query_lower = query.lower()
        paths = []

        try:
            if self._use_db:
                import app_db
                root_normalized = os.path.normcase(os.path.normpath(root_path))
                for media_file in app_db.media_db.search_by_filename(query):
                    if self._cancel:
                        return
                    file_normalized = os.path.normcase(os.path.normpath(media_file.path))
                    if file_normalized.startswith(root_normalized):
                        paths.append(media_file.path)
            else:
                for dirpath, _dirnames, filenames in os.walk(root_path):
                    if self._cancel:
                        return
                    for name in filenames:
                        if self._cancel:
                            return
                        if query_lower not in name.lower():
                            continue
                        if os.path.splitext(name)[1].lower() not in self._extensions:
                            continue
                        paths.append(os.path.join(dirpath, name))
        except Exception as e:
            if not self._cancel:
                self.error.emit(root_path, str(e))
            return

        if not self._cancel:
            self.results_ready.emit(root_path, query, paths)

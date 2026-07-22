import os

from utilities import signal_manager
from utilities.functions import get_app_path
from downloader.downloader import Downloader
from app_db.catalog_worker import CatalogWorker
from ..dialogs.downloader_dialog import DownloaderDialog
from ..dialogs.catalog_progress_dialog import CatalogProgressDialog


class SingletonDialogsManager:
    """Downloader and Catalog singleton dialog lifecycle management,
    extracted out of MainWindow. Reads/writes MainWindow's pre-declared
    _shared_downloader/_downloader_dialog/_catalog_worker/_catalog_dialog/
    show_downloader_button/show_catalog_button."""

    def __init__(self, main_window):
        self.main_window = main_window

    # ------------------------------------------------------------------
    # Singleton downloader dialog management
    # ------------------------------------------------------------------
    def get_shared_downloader(self) -> Downloader:
        """Return the singleton Downloader, creating it on first call."""
        mw = self.main_window
        if mw._shared_downloader is None:
            dest = os.path.join(get_app_path(), "downloads")
            mw._shared_downloader = Downloader(destination=dest)
        return mw._shared_downloader

    def open_downloader(self):
        """Open (or raise) the singleton downloader dialog."""
        mw = self.main_window
        if mw._downloader_dialog is not None:
            # Dialog was minimized or still alive - bring it back
            mw._downloader_dialog.show_dialog()
            mw.show_downloader_button.setVisible(False)
            signal_manager.statusbar_message.emit(_("Download Manager opened"))
            return

        # First time (or after close) - create fresh dialog
        dlg = DownloaderDialog(self.get_shared_downloader(), parent=mw)
        dlg.dialog_hidden.connect(self._on_downloader_hidden)
        dlg.dialog_closed.connect(self._on_downloader_closed)
        mw._downloader_dialog = dlg
        dlg.show_dialog()
        mw.show_downloader_button.setVisible(False)
        signal_manager.statusbar_message.emit(_("Download Manager opened"))

    def _on_downloader_hidden(self):
        """Called when dialog hides itself (Minimize button)."""
        mw = self.main_window
        mw.show_downloader_button.setVisible(True)
        signal_manager.statusbar_message.emit(_("Download Manager minimized"))

    def _on_downloader_closed(self):
        """Called when dialog is fully closed so it can be re-created next time."""
        mw = self.main_window
        mw._downloader_dialog = None
        mw.show_downloader_button.setVisible(False)
        signal_manager.statusbar_message.emit(_("Download Manager closed"))

    def show_minimized_downloader(self):
        """Status-bar button: show the minimized dialog."""
        mw = self.main_window
        if mw._downloader_dialog is not None:
            mw._downloader_dialog.show_dialog()
            mw.show_downloader_button.setVisible(False)
            signal_manager.statusbar_message.emit(_("Download Manager restored"))

    # ------------------------------------------------------------------
    # Singleton catalog worker/dialog management
    # ------------------------------------------------------------------
    def get_catalog_worker(self) -> CatalogWorker:
        """Return the singleton CatalogWorker, creating it on first call."""
        mw = self.main_window
        if mw._catalog_worker is None:
            mw._catalog_worker = CatalogWorker(mw)
        return mw._catalog_worker

    def catalog_folder(self, path: str):
        """Enqueue a folder for cataloging and surface the progress dialog."""
        self.get_catalog_worker().enqueue_folder(path)
        self.open_catalog_dialog()

    def rebuild_catalog(self):
        """Clear the entire media database and re-scan every previously
        cataloged folder."""
        import app_db
        roots = app_db.media_db.get_catalog_roots()
        for media in app_db.media_db.get_all_media():
            app_db.media_db.delete_media_file(media.id)
        for root in roots:
            app_db.media_db.remove_catalog_root(root)

        worker = self.get_catalog_worker()
        for root in roots:
            worker.enqueue_folder(root)
        if roots:
            self.open_catalog_dialog()

    def open_catalog_dialog(self):
        """Open (or raise) the singleton cataloging progress dialog."""
        mw = self.main_window
        if mw._catalog_dialog is not None:
            mw._catalog_dialog.show_dialog()
            mw.show_catalog_button.setVisible(False)
            signal_manager.statusbar_message.emit(_("Database Cataloging opened"))
            return

        dlg = CatalogProgressDialog(self.get_catalog_worker(), parent=mw)
        dlg.dialog_hidden.connect(self._on_catalog_hidden)
        dlg.dialog_closed.connect(self._on_catalog_closed)
        mw._catalog_dialog = dlg
        dlg.show_dialog()
        mw.show_catalog_button.setVisible(False)
        signal_manager.statusbar_message.emit(_("Database Cataloging opened"))

    def _on_catalog_hidden(self):
        mw = self.main_window
        mw.show_catalog_button.setVisible(True)
        signal_manager.statusbar_message.emit(_("Database Cataloging minimized"))

    def _on_catalog_closed(self):
        mw = self.main_window
        mw._catalog_dialog = None
        mw.show_catalog_button.setVisible(False)
        signal_manager.statusbar_message.emit(_("Database Cataloging closed"))

    def show_minimized_catalog(self):
        mw = self.main_window
        if mw._catalog_dialog is not None:
            mw._catalog_dialog.show_dialog()
            mw.show_catalog_button.setVisible(False)
            signal_manager.statusbar_message.emit(_("Database Cataloging restored"))

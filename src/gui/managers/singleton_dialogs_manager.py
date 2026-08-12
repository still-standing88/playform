import os

from utilities import signal_manager
from utilities.announcement_categories import AnnouncementCategory
from utilities.functions import get_app_path
from downloader.downloader import Downloader
from app_db.catalog_worker import CatalogWorker
from ..dialogs.downloader_dialog import DownloaderDialog
from ..dialogs.catalog_progress_dialog import CatalogProgressDialog
from ..dialogs.manage_database_dialog import ManageDatabaseDialog


def _announce_downloads(text):
    signal_manager.announce(text, AnnouncementCategory.DOWNLOADS)


def _announce_database(text):
    signal_manager.announce(text, AnnouncementCategory.DATABASE)


class SingletonDialogsManager:
    """Downloader and Catalog singleton dialog lifecycle management,
    extracted out of MainWindow. Reads/writes MainWindow's pre-declared
    _shared_downloader/_downloader_dialog/_catalog_worker/_catalog_dialog/
    _manage_db_dialog/show_downloader_button/show_catalog_button/
    show_manage_db_button.

    The catalog progress dialog is never shown standalone - opening it
    always ensures Manage Database is open first and shows the progress
    dialog on top of it (_ensure_manage_db_dialog). Minimizing or closing
    the progress dialog just hides/closes that one dialog, which naturally
    reveals Manage Database again since it was sitting underneath the whole
    time. Reopening Manage Database while a scan is running brings the
    progress dialog back up too - see open_manage_database.

    Explorer's "Add Current Folder to Database" goes through
    queue_folder_for_catalog instead of catalog_folder - it enqueues without
    forcing any dialog open, so it stays a low-friction background action;
    the user can check progress later via the "Show Cataloging" button.
    """

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
            _announce_downloads(_("Download Manager opened"))
            return

        # First time (or after close) - create fresh dialog
        dlg = DownloaderDialog(self.get_shared_downloader(), parent=mw)
        dlg.dialog_hidden.connect(self._on_downloader_hidden)
        dlg.dialog_closed.connect(self._on_downloader_closed)
        mw._downloader_dialog = dlg
        dlg.show_dialog()
        mw.show_downloader_button.setVisible(False)
        _announce_downloads(_("Download Manager opened"))

    def _on_downloader_hidden(self):
        """Called when dialog hides itself (Minimize button)."""
        mw = self.main_window
        mw.show_downloader_button.setVisible(True)
        _announce_downloads(_("Download Manager minimized"))

    def _on_downloader_closed(self):
        """Called when dialog is fully closed so it can be re-created next time."""
        mw = self.main_window
        mw._downloader_dialog = None
        mw.show_downloader_button.setVisible(False)
        _announce_downloads(_("Download Manager closed"))

    def show_minimized_downloader(self):
        """Status-bar button: show the minimized dialog."""
        mw = self.main_window
        if mw._downloader_dialog is not None:
            mw._downloader_dialog.show_dialog()
            mw.show_downloader_button.setVisible(False)
            _announce_downloads(_("Download Manager restored"))

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
        """Enqueue a folder for cataloging and surface the progress dialog
        on top of Manage Database - used when the user explicitly asked to
        catalog/rescan/rebuild from within Manage Database itself."""
        self.get_catalog_worker().enqueue_folder(path)
        self.open_catalog_dialog()

    def queue_folder_for_catalog(self, path: str):
        """Enqueue a folder without forcing any dialog open - used by
        Explorer's "Add Current Folder to Database" toolbar action, which
        should stay a low-friction background action rather than
        interrupting the user's browsing with a popped-open dialog. The
        progress dialog is still created (just not shown) so "Show
        Cataloging" is immediately available if they want to check on it."""
        mw = self.main_window
        self.get_catalog_worker().enqueue_folder(path)
        self._ensure_catalog_dialog_exists()
        mw.show_catalog_button.setVisible(True)
        _announce_database(
            _("Queued {path} for cataloging").format(path=path)
        )

    def rebuild_catalog(self):
        """Clear the entire media database and re-scan every previously
        cataloged folder."""
        import app_db
        roots = app_db.media_db.get_catalog_roots()
        app_db.media_db.clear_index()
        for root in roots:
            app_db.media_db.remove_catalog_root(root)

        worker = self.get_catalog_worker()
        for root in roots:
            worker.enqueue_folder(root)
        if roots:
            self.open_catalog_dialog()

    def _ensure_catalog_dialog_exists(self) -> CatalogProgressDialog:
        """Creates the singleton progress dialog if needed, without showing
        it - the object needs to exist up front so its signals (including
        the auto-close-on-drain one) are live for a scan that was only
        silently queued."""
        mw = self.main_window
        if mw._catalog_dialog is None:
            dlg = CatalogProgressDialog(self.get_catalog_worker(), parent=mw)
            dlg.dialog_hidden.connect(self._on_catalog_hidden)
            dlg.dialog_closed.connect(self._on_catalog_closed)
            mw._catalog_dialog = dlg
        return mw._catalog_dialog

    def open_catalog_dialog(self):
        """Open (or raise) the singleton cataloging progress dialog, always
        on top of Manage Database - which is created/shown first if it
        isn't already up, so the progress dialog never appears standalone."""
        mw = self.main_window
        self._ensure_manage_db_dialog()
        dlg = self._ensure_catalog_dialog_exists()
        dlg.show_dialog()
        mw.show_catalog_button.setVisible(False)
        _announce_database(_("Database Cataloging opened"))

    def _on_catalog_hidden(self):
        mw = self.main_window
        mw.show_catalog_button.setVisible(True)
        _announce_database(_("Database Cataloging minimized"))

    def _on_catalog_closed(self):
        mw = self.main_window
        mw._catalog_dialog = None
        mw.show_catalog_button.setVisible(False)
        _announce_database(_("Database Cataloging closed"))

    def show_minimized_catalog(self):
        mw = self.main_window
        if mw._catalog_dialog is not None:
            self._ensure_manage_db_dialog()
            mw._catalog_dialog.show_dialog()
            mw.show_catalog_button.setVisible(False)
            _announce_database(_("Database Cataloging restored"))

    # ------------------------------------------------------------------
    # Singleton manage-database dialog management
    # ------------------------------------------------------------------
    def _ensure_manage_db_dialog(self) -> ManageDatabaseDialog:
        """Creates the singleton Manage Database dialog if needed and makes
        sure it's visible. The catalog progress dialog is always shown on
        top of it (see open_catalog_dialog/show_minimized_catalog) - closing
        or minimizing the progress dialog naturally reveals this again,
        since it's already sitting underneath rather than hidden alongside it."""
        mw = self.main_window
        if mw._manage_db_dialog is None:
            dlg = ManageDatabaseDialog(mw, parent=mw)
            dlg.dialog_hidden.connect(self._on_manage_db_hidden)
            dlg.dialog_closed.connect(self._on_manage_db_closed)
            # Keep the folder list/stats live while scans run in the
            # background, whether or not this dialog happens to be visible
            # at the moment a folder finishes.
            worker = self.get_catalog_worker()
            worker.folder_finished.connect(dlg.reload)
            worker.error.connect(lambda *_args: dlg.reload())
            mw._manage_db_dialog = dlg
        if not mw._manage_db_dialog.isVisible():
            mw._manage_db_dialog.show_dialog()
            mw.show_manage_db_button.setVisible(False)
        return mw._manage_db_dialog

    def open_manage_database(self):
        """Open (or raise) the singleton Manage Database dialog. If a
        catalog scan is currently running, also surfaces the catalog
        progress dialog on top of it."""
        mw = self.main_window
        dlg = self._ensure_manage_db_dialog()
        dlg.show_dialog()
        mw.show_manage_db_button.setVisible(False)
        _announce_database(_("Manage Database opened"))

        if mw._catalog_worker is not None and mw._catalog_worker.isRunning():
            self.open_catalog_dialog()

    def _on_manage_db_hidden(self):
        mw = self.main_window
        mw.show_manage_db_button.setVisible(True)
        _announce_database(_("Manage Database minimized"))

    def _on_manage_db_closed(self):
        mw = self.main_window
        mw._manage_db_dialog = None
        mw.show_manage_db_button.setVisible(False)
        _announce_database(_("Manage Database closed"))

    def show_minimized_manage_database(self):
        mw = self.main_window
        if mw._manage_db_dialog is not None:
            mw._manage_db_dialog.show_dialog()
            mw.show_manage_db_button.setVisible(False)
            _announce_database(_("Manage Database restored"))

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..dialogs import SessionDialog, SourceWizard
from ..registries import SessionRegistry, SourceRegistry


class SessionsTab(QWidget):
    """Session list + source pool, each with add/edit/delete. Sessions and
    sources are managed as separate pools; a session references sources
    rather than owning them."""

    sessions_changed = Signal()
    sources_changed = Signal()

    def __init__(self, sessions: SessionRegistry, sources: SourceRegistry, parent=None):
        super().__init__(parent)
        self.sessions = sessions
        self.sources = sources

        layout = QHBoxLayout(self)
        layout.addWidget(self._build_sessions_panel(), 1)
        layout.addWidget(self._build_sources_panel(), 1)

    def _build_sessions_panel(self) -> QWidget:
        box = QGroupBox(_("Sessions"))
        v = QVBoxLayout(box)
        self.session_list = QListWidget()
        self.session_list.itemDoubleClicked.connect(lambda _i: self._edit_session())
        self.session_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.session_list.customContextMenuRequested.connect(self._session_context_menu)
        v.addWidget(self.session_list)

        row = QHBoxLayout()
        add_btn = QPushButton(_("Add session"))
        edit_btn = QPushButton(_("Edit"))
        del_btn = QPushButton(_("Delete"))
        add_btn.clicked.connect(self._add_session)
        edit_btn.clicked.connect(self._edit_session)
        del_btn.clicked.connect(self._delete_session)
        for b in (add_btn, edit_btn, del_btn):
            row.addWidget(b)
        v.addLayout(row)
        self._refresh_sessions()
        return box

    def _build_sources_panel(self) -> QWidget:
        box = QGroupBox(_("Sources"))
        v = QVBoxLayout(box)
        self.source_list = QListWidget()
        self.source_list.itemDoubleClicked.connect(lambda _i: self._edit_source())
        self.source_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.source_list.customContextMenuRequested.connect(self._source_context_menu)
        v.addWidget(self.source_list)

        row = QHBoxLayout()
        add_btn = QPushButton(_("Add source"))
        edit_btn = QPushButton(_("Edit"))
        del_btn = QPushButton(_("Delete"))
        add_btn.clicked.connect(self._add_source)
        edit_btn.clicked.connect(self._edit_source)
        del_btn.clicked.connect(self._delete_source)
        for b in (add_btn, edit_btn, del_btn):
            row.addWidget(b)
        v.addLayout(row)
        self._refresh_sources()
        return box

    def _session_context_menu(self, pos) -> None:
        from PySide6.QtWidgets import QMenu

        item = self.session_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        menu.addAction(_("Edit"), self._edit_session)
        menu.addAction(_("Delete"), self._delete_session)
        menu.exec(self.session_list.mapToGlobal(pos))

    def _source_context_menu(self, pos) -> None:
        from PySide6.QtWidgets import QMenu

        item = self.source_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        menu.addAction(_("Edit"), self._edit_source)
        menu.addAction(_("Delete"), self._delete_source)
        menu.exec(self.source_list.mapToGlobal(pos))

    # -- sessions --
    def _refresh_sessions(self) -> None:
        self.session_list.clear()
        for s in self.sessions.all():
            item = QListWidgetItem(_("{name}  ({count} sources)").format(name=s.name, count=len(s.source_ids)))
            item.setData(Qt.ItemDataRole.UserRole, s.id)
            self.session_list.addItem(item)

    def _add_session(self) -> None:
        dlg = SessionDialog(self.sources, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.sessions.add(dlg.result_session())
            self._refresh_sessions()
            self.sessions_changed.emit()

    def _edit_session(self) -> None:
        item = self.session_list.currentItem()
        if not item:
            return
        session = self.sessions.get(item.data(Qt.ItemDataRole.UserRole))
        dlg = SessionDialog(self.sources, session=session, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.sessions.add(dlg.result_session())
            self._refresh_sessions()
            self.sessions_changed.emit()

    def _delete_session(self) -> None:
        item = self.session_list.currentItem()
        if not item:
            return
        if QMessageBox.question(self, _("Delete session"), _("Remove this session?")) == QMessageBox.StandardButton.Yes:
            self.sessions.remove(item.data(Qt.ItemDataRole.UserRole))
            self._refresh_sessions()
            self.sessions_changed.emit()

    # -- sources --
    def _refresh_sources(self) -> None:
        self.source_list.clear()
        for s in self.sources.all():
            item = QListWidgetItem(f"{s.friendly_name}  -  {s.status_text()}")
            item.setData(Qt.ItemDataRole.UserRole, s.id)
            self.source_list.addItem(item)

    def _add_source(self) -> None:
        wizard = SourceWizard(parent=self)
        if wizard.exec() == QDialog.DialogCode.Accepted:
            self.sources.add(wizard.result_source())
            self._refresh_sources()
            self.sources_changed.emit()

    def _edit_source(self) -> None:
        item = self.source_list.currentItem()
        if not item:
            return
        source = self.sources.get(item.data(Qt.ItemDataRole.UserRole))
        wizard = SourceWizard(edit_source=source, parent=self)
        if wizard.exec() == QDialog.DialogCode.Accepted:
            self.sources.add(wizard.result_source())
            self._refresh_sources()
            self.sources_changed.emit()

    def _delete_source(self) -> None:
        item = self.source_list.currentItem()
        if not item:
            return
        if QMessageBox.question(self, _("Delete source"), _("Remove this source?")) == QMessageBox.StandardButton.Yes:
            self.sources.remove(item.data(Qt.ItemDataRole.UserRole))
            self._refresh_sources()
            self.sources_changed.emit()

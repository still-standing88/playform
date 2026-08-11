"""Sessions + sources, consolidated into one view (no more separate
Sessions/Capture/Settings tabs - see ui.py).

Sources are session-scoped: the source list shows only the sources
belonging to whichever session is selected, and "Add source" attaches the
new source directly to it - there's no separate "assign sources to a
session" step anymore (SessionDialog dropped that checklist).

If no session exists yet, one is created in memory and selected
automatically (not persisted to disk) so Add Source never requires a
"create a session first" detour; it's silently written for real - given an
auto name ("Session N") - the moment its first source is added. An explicit
"New session..." (sessions-list context menu) creates and persists a named
session immediately instead.
"""
from __future__ import annotations

import copy
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from media_core.av_capture.capabilities import CaptureCapabilities

from ..device_status import DeviceStatusChecker
from ..dialogs import SessionDialog, SourceWizard
from ..models import CaptureSource, Session, new_id
from ..registries import SessionRegistry, SourceRegistry
from ..settings import MultiDeviceCaptureSettings

_ROLE_ID = Qt.ItemDataRole.UserRole
_DISCONNECTED_COLOR = QColor(200, 90, 70)


class ConfigureView(QWidget):
    start_capture_requested = Signal(object, list)  # Session, list[CaptureSource]
    settings_requested = Signal()

    def __init__(
        self, sessions: SessionRegistry, sources: SourceRegistry,
        capabilities: CaptureCapabilities, settings: MultiDeviceCaptureSettings, parent=None,
    ):
        super().__init__(parent)
        self.sessions = sessions
        self.sources = sources
        self.capabilities = capabilities
        self.settings = settings
        self._pending_session: Optional[Session] = None

        self.device_checker = DeviceStatusChecker(capabilities, self)
        self.device_checker.checked.connect(self._on_device_status_checked)

        layout = QVBoxLayout(self)

        body = QHBoxLayout()
        body.addWidget(self._build_sessions_panel(), 1)
        body.addWidget(self._build_sources_panel(), 1)
        layout.addLayout(body)

        bottom = QHBoxLayout()
        self.settings_btn = QPushButton(_("Settings"))
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        bottom.addWidget(self.settings_btn)
        bottom.addStretch()
        self.start_btn = QPushButton(_("Start capture"))
        self.start_btn.clicked.connect(self._on_start_clicked)
        bottom.addWidget(self.start_btn)
        layout.addLayout(bottom)

        self._ensure_active_session_exists()
        self.refresh_sessions()

    # -- panel construction -----------------------------------------------

    def _build_sessions_panel(self) -> QWidget:
        box = QGroupBox(_("Sessions"))
        v = QVBoxLayout(box)
        self.session_list = QListWidget()
        self.session_list.itemDoubleClicked.connect(lambda _i: self._edit_selected_session())
        self.session_list.currentItemChanged.connect(lambda *_: self._on_session_selection_changed())
        self.session_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.session_list.customContextMenuRequested.connect(self._session_context_menu)
        v.addWidget(self.session_list)
        return box

    def _build_sources_panel(self) -> QWidget:
        self.sources_box = QGroupBox(_("Sources"))
        v = QVBoxLayout(self.sources_box)
        self.source_list = QListWidget()
        self.source_list.itemDoubleClicked.connect(lambda _i: self._edit_source(self._item_source_id(_i)))
        self.source_list.itemChanged.connect(self._on_source_item_changed)
        self.source_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.source_list.customContextMenuRequested.connect(self._source_context_menu)
        v.addWidget(self.source_list)

        row = QHBoxLayout()
        add_btn = QPushButton(_("Add source"))
        add_btn.clicked.connect(self._add_source)
        row.addWidget(add_btn)
        refresh_btn = QPushButton(_("Refresh status"))
        refresh_btn.setToolTip(_("Check whether each source's device is still connected/available."))
        refresh_btn.clicked.connect(self._check_device_status)
        row.addWidget(refresh_btn)
        v.addLayout(row)
        return self.sources_box

    # -- pending (unsaved) session lifecycle -------------------------------

    def _ensure_active_session_exists(self) -> None:
        if not self.sessions.all() and self._pending_session is None:
            self._pending_session = Session(
                id=new_id(), name=_("Untitled session"), source_ids=[],
                output_dir=self.settings.get("default_output_dir", ""),
                container_format=self.settings.get("default_container", "mkv"),
            )

    def _is_pending(self, session: Session) -> bool:
        return self._pending_session is not None and session.id == self._pending_session.id

    def _promote_pending_session(self, session: Session) -> None:
        """Called the moment a source is first added to the pending
        session - persists it for real under an auto name."""
        if not self._is_pending(session):
            return
        session.name = _("Session {n}").format(n=len(self.sessions.all()) + 1)
        self.sessions.add(session)
        self._pending_session = None

    # -- sessions -----------------------------------------------------

    def _all_sessions_for_display(self) -> list[Session]:
        sessions = list(self.sessions.all())
        if self._pending_session is not None:
            sessions.append(self._pending_session)
        return sessions

    def refresh_sessions(self) -> None:
        current_id = self._selected_session_id()
        self.session_list.blockSignals(True)
        self.session_list.clear()
        for session in self._all_sessions_for_display():
            is_pending = self._is_pending(session)
            label = _("{name}  ({count} sources)").format(name=session.name, count=len(session.source_ids))
            if is_pending:
                label += _("  [unsaved]")
            item = QListWidgetItem(label)
            if is_pending:
                font = item.font()
                font.setItalic(True)
                item.setFont(font)
            item.setData(_ROLE_ID, session.id)
            self.session_list.addItem(item)
        self.session_list.blockSignals(False)

        target_id = current_id or (self._all_sessions_for_display()[0].id if self._all_sessions_for_display() else None)
        self._select_session_id(target_id)
        self._on_session_selection_changed()

    def _selected_session_id(self) -> Optional[str]:
        item = self.session_list.currentItem()
        return item.data(_ROLE_ID) if item else None

    def _select_session_id(self, session_id: Optional[str]) -> None:
        if session_id is None:
            return
        for i in range(self.session_list.count()):
            if self.session_list.item(i).data(_ROLE_ID) == session_id:
                self.session_list.setCurrentRow(i)
                return

    def selected_session(self) -> Optional[Session]:
        session_id = self._selected_session_id()
        if session_id is None:
            return None
        if self._pending_session is not None and session_id == self._pending_session.id:
            return self._pending_session
        return self.sessions.get(session_id)

    def _on_session_selection_changed(self) -> None:
        session = self.selected_session()
        self.sources_box.setTitle(_("Sources - {name}").format(name=session.name) if session else _("Sources"))
        self.refresh_sources()
        self._check_device_status()

    def _session_context_menu(self, pos) -> None:
        item = self.session_list.itemAt(pos)
        menu = QMenu(self)
        if item is None:
            menu.addAction(_("New session..."), self._create_new_session)
            menu.exec(self.session_list.mapToGlobal(pos))
            return

        session_id = item.data(_ROLE_ID)
        session = self._pending_session if (self._pending_session and session_id == self._pending_session.id) else self.sessions.get(session_id)
        if session is None:
            return
        is_pending = self._is_pending(session)

        if is_pending:
            menu.addAction(_("Save session..."), lambda: self._save_pending_session(session))
        else:
            menu.addAction(_("Edit"), lambda: self._edit_session(session))
            menu.addAction(_("Duplicate"), lambda: self._duplicate_session(session))
        menu.addAction(_("Delete"), lambda: self._delete_session(session))
        menu.addSeparator()
        menu.addAction(_("New session..."), self._create_new_session)
        menu.exec(self.session_list.mapToGlobal(pos))

    def _edit_selected_session(self) -> None:
        session = self.selected_session()
        if session is None:
            return
        if self._is_pending(session):
            self._save_pending_session(session)
        else:
            self._edit_session(session)

    def _create_new_session(self) -> None:
        dlg = SessionDialog(
            default_output_dir=self.settings.get("default_output_dir", ""),
            default_container=self.settings.get("default_container", "mkv"), parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            session = dlg.result_session()
            self.sessions.add(session)
            self.refresh_sessions()
            self._select_session_id(session.id)

    def _save_pending_session(self, session: Session) -> None:
        dlg = SessionDialog(session=session, parent=self)
        dlg.name_edit.selectAll()
        if dlg.exec() == QDialog.DialogCode.Accepted:
            saved = dlg.result_session()
            self.sessions.add(saved)
            self._pending_session = None
            self.refresh_sessions()
            self._select_session_id(saved.id)

    def _edit_session(self, session: Session) -> None:
        dlg = SessionDialog(session=session, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.sessions.add(dlg.result_session())
            self.refresh_sessions()
            self._select_session_id(session.id)

    def _duplicate_session(self, session: Session) -> None:
        clone = copy.deepcopy(session)
        clone.id = new_id()
        clone.name = _("{name} (copy)").format(name=session.name)
        self.sessions.add(clone)
        self.refresh_sessions()
        self._select_session_id(clone.id)

    def _delete_session(self, session: Session) -> None:
        if self._is_pending(session):
            self._pending_session = None
        else:
            if QMessageBox.question(self, _("Delete session"), _("Remove this session?")) != QMessageBox.StandardButton.Yes:
                return
            self.sessions.remove(session.id)
        self._ensure_active_session_exists()
        self.refresh_sessions()

    # -- sources (scoped to the selected session) ------------------------

    def _item_source_id(self, item: QListWidgetItem) -> Optional[str]:
        return item.data(_ROLE_ID) if item else None

    def _existing_source_names(self) -> set:
        return {s.friendly_name for s in self.sources.all()}

    def refresh_sources(self) -> None:
        self.source_list.blockSignals(True)
        self.source_list.clear()
        session = self.selected_session()
        if session is None:
            self.source_list.blockSignals(False)
            return
        for source_id in session.source_ids:
            source = self.sources.get(source_id)
            if source is None:
                continue
            item = QListWidgetItem(f"{source.friendly_name}  -  {source.status_text()}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if source.enabled else Qt.CheckState.Unchecked)
            item.setData(_ROLE_ID, source.id)
            self.source_list.addItem(item)
        self.source_list.blockSignals(False)

    def _on_source_item_changed(self, item: QListWidgetItem) -> None:
        source = self.sources.get(self._item_source_id(item))
        if source is None:
            return
        source.enabled = item.checkState() == Qt.CheckState.Checked
        self.sources.add(source)

    def _add_source(self) -> None:
        session = self.selected_session()
        if session is None:
            self._ensure_active_session_exists()
            self.refresh_sessions()
            session = self.selected_session()
        wizard = SourceWizard(self.capabilities, global_settings=self.settings,
                              existing_names=self._existing_source_names(), parent=self)
        if wizard.exec() != QDialog.DialogCode.Accepted:
            return
        source = wizard.result_source()
        self.sources.add(source)
        session.source_ids.append(source.id)
        was_pending = self._is_pending(session)
        self._promote_pending_session(session)
        if not was_pending:
            self.sessions.add(session)  # persist the updated source_ids
        self.refresh_sessions()
        self._select_session_id(session.id)

    def _edit_source(self, source_id: Optional[str]) -> None:
        if source_id is None:
            return
        source = self.sources.get(source_id)
        if source is None:
            return
        wizard = SourceWizard(self.capabilities, edit_source=source, global_settings=self.settings, parent=self)
        if wizard.exec() == QDialog.DialogCode.Accepted:
            self.sources.add(wizard.result_source())
            self.refresh_sources()
            self._check_device_status()

    def _duplicate_source(self, source_id: Optional[str]) -> None:
        source = self.sources.get(source_id) if source_id else None
        session = self.selected_session()
        if source is None or session is None:
            return
        clone = copy.deepcopy(source)
        clone.id = new_id()
        clone.friendly_name = _("{name} (copy)").format(name=source.friendly_name)
        self.sources.add(clone)
        session.source_ids.append(clone.id)
        was_pending = self._is_pending(session)
        self._promote_pending_session(session)
        if not was_pending:
            self.sessions.add(session)
        self.refresh_sessions()
        self._select_session_id(session.id)

    def _remove_source_from_session(self, source_id: Optional[str]) -> None:
        session = self.selected_session()
        if session is None or source_id not in session.source_ids:
            return
        session.source_ids.remove(source_id)
        if not self._is_pending(session):
            self.sessions.add(session)
        self.refresh_sessions()

    def _delete_source_entirely(self, source_id: Optional[str]) -> None:
        if source_id is None:
            return
        if QMessageBox.question(self, _("Delete source"), _("Remove this source from every session and delete it?")) != QMessageBox.StandardButton.Yes:
            return
        for session in self._all_sessions_for_display():
            if source_id in session.source_ids:
                session.source_ids.remove(source_id)
                if not self._is_pending(session):
                    self.sessions.add(session)
        self.sources.remove(source_id)
        self.refresh_sessions()

    def _source_context_menu(self, pos) -> None:
        item = self.source_list.itemAt(pos)
        if item is None:
            return
        source_id = self._item_source_id(item)
        menu = QMenu(self)
        menu.addAction(_("Edit"), lambda: self._edit_source(source_id))
        menu.addAction(_("Duplicate"), lambda: self._duplicate_source(source_id))
        menu.addAction(_("Remove from session"), lambda: self._remove_source_from_session(source_id))
        menu.addSeparator()
        menu.addAction(_("Delete source"), lambda: self._delete_source_entirely(source_id))
        menu.exec(self.source_list.mapToGlobal(pos))

    # -- device presence (non-intrusive: on session-select + manual refresh) --

    def _check_device_status(self) -> None:
        session = self.selected_session()
        if session is None:
            return
        source_list = [self.sources.get(sid) for sid in session.source_ids]
        source_list = [s for s in source_list if s is not None]
        if source_list:
            self.device_checker.check(source_list)

    def _on_device_status_checked(self, presence: dict) -> None:
        for i in range(self.source_list.count()):
            item = self.source_list.item(i)
            source_id = self._item_source_id(item)
            source = self.sources.get(source_id)
            if source is None or source_id not in presence:
                continue
            base_text = f"{source.friendly_name}  -  {source.status_text()}"
            if presence[source_id]:
                item.setText(base_text)
                item.setForeground(self.source_list.palette().text())
            else:
                item.setText(f"{base_text}  -  {_('device not found')}")
                item.setForeground(_DISCONNECTED_COLOR)

    # -- transport handoff --------------------------------------------

    def _on_start_clicked(self) -> None:
        session = self.selected_session()
        if session is None:
            QMessageBox.information(self, _("No session"), _("Select or create a session first."))
            return
        selected = [self.sources.get(sid) for sid in session.source_ids]
        selected = [s for s in selected if s is not None and s.enabled]
        if not selected:
            QMessageBox.information(self, _("No sources"), _("This session has no enabled sources."))
            return
        self.start_capture_requested.emit(session, selected)

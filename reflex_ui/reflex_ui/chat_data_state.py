from __future__ import annotations

import uuid
from typing import Any

import reflex as rx

from reflex_ui.auth_state import AuthState
from reflex_ui.data import auth_crypto, repository
from reflex_ui.data.db import get_pool
from reflex_ui.data.formatting import serialize_session_row, thread_message_from_row


class ChatDataState(AuthState):
    sessions: list[dict[str, str]] = []
    current_session_id: str = ""
    thread_messages: list[dict[str, str]] = []
    sessions_sidebar_collapsed: bool = False
    pending_delete_session_id: str = ""
    is_creating_session: bool = False
    is_deleting_session: bool = False
    current_user_email: str = ""

    def toggle_sessions_sidebar(self):
        self.sessions_sidebar_collapsed = not self.sessions_sidebar_collapsed

    def open_delete_confirm(self, session_id: str):
        self.pending_delete_session_id = session_id

    def cancel_delete_confirm(self):
        self.pending_delete_session_id = ""

    def _thread_from_db_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, str]]:
        return [thread_message_from_row(r) for r in rows]

    @rx.var
    def has_thread_messages(self) -> bool:
        return len(self.thread_messages) > 0

    @rx.var
    def sessions_empty(self) -> bool:
        return len(self.sessions) == 0

    async def login_submit(self):
        await self._login_submit_core()
        if not self.auth_error:
            await self.sync_current_user_profile()
            await self.refresh_sessions()
            if self.sessions and not (self.current_session_id or "").strip():
                await self.select_session(self.sessions[0]["id"])

    async def register_submit(self):
        await self._register_submit_core()
        if not self.auth_error:
            await self.sync_current_user_profile()
            await self.refresh_sessions()
            if self.sessions and not (self.current_session_id or "").strip():
                await self.select_session(self.sessions[0]["id"])

    def logout(self):
        self.sessions = []
        self.current_session_id = ""
        self.thread_messages = []
        self.current_user_email = ""
        self.session_token = ""
        self.auth_error = ""
        self.login_password = ""
        self.register_password = ""
        self.pending_delete_session_id = ""
        self.sessions_sidebar_collapsed = False
        self.auth_panel = "login"
        self.register_terms_accepted = True
        return rx.remove_cookie("scienta_session")

    async def _current_user_id(self) -> uuid.UUID | None:
        return auth_crypto.verify_user_token(self.session_token)

    async def sync_current_user_profile(self):
        user_id = await self._current_user_id()
        if user_id is None:
            self.current_user_email = ""
            return
        try:
            pool = await get_pool()
        except RuntimeError:
            self.current_user_email = ""
            return
        row = await repository.fetch_user_by_id(pool, user_id)
        if not row:
            self.current_user_email = ""
            return
        self.current_user_email = str(row.get("email") or "")

    async def on_index_load(self):
        self.auth_error = ""
        user_id = await self._current_user_id()
        if user_id is None:
            self.sessions = []
            self.current_user_email = ""
            return
        await self.sync_current_user_profile()
        await self.refresh_sessions()
        cid = (self.current_session_id or "").strip()
        if cid:
            try:
                sid = uuid.UUID(cid)
            except ValueError:
                return
            pool = await get_pool()
            rows = await repository.list_messages(pool, user_id, sid)
            self.thread_messages = self._thread_from_db_rows(rows)
            return
        if self.sessions:
            await self.select_session(self.sessions[0]["id"])

    async def refresh_sessions(self):
        user_id = await self._current_user_id()
        if user_id is None:
            self.sessions = []
            return
        pool = await get_pool()
        rows = await repository.list_all_chat_sessions(pool, user_id)
        self.sessions = [serialize_session_row(r) for r in rows]

    async def create_empty_session(self):
        self.auth_error = ""
        user_id = await self._current_user_id()
        if user_id is None:
            self.auth_error = "You must be signed in."
            return
        self.is_creating_session = True
        try:
            pool = await get_pool()
            sid = await repository.create_chat_session(pool, user_id)
            self.current_session_id = str(sid)
            self.thread_messages = []
            await self.refresh_sessions()
        finally:
            self.is_creating_session = False

    async def select_session(self, session_id: str):
        self.auth_error = ""
        user_id = await self._current_user_id()
        if user_id is None:
            return
        try:
            sid = uuid.UUID(session_id)
        except ValueError:
            return
        pool = await get_pool()
        rows = await repository.list_messages(pool, user_id, sid)
        self.current_session_id = str(sid)
        self.thread_messages = self._thread_from_db_rows(rows)

    async def confirm_delete_session(self):
        sid_str = (self.pending_delete_session_id or "").strip()
        if not sid_str:
            return
        self.auth_error = ""
        user_id = await self._current_user_id()
        if user_id is None:
            self.pending_delete_session_id = ""
            return
        try:
            sid = uuid.UUID(sid_str)
        except ValueError:
            self.pending_delete_session_id = ""
            return
        self.is_deleting_session = True
        try:
            pool = await get_pool()
            deleted = await repository.delete_chat_session(pool, user_id, sid)
            if not deleted:
                self.auth_error = "Could not delete that session."
                return
            was_current = self.current_session_id == sid_str
            if was_current:
                self.current_session_id = ""
                self.thread_messages = []
            self.pending_delete_session_id = ""
            await self.refresh_sessions()
            if was_current and self.sessions:
                await self.select_session(self.sessions[0]["id"])
        finally:
            self.is_deleting_session = False

    async def append_persisted_message(
        self,
        role: str,
        content: str,
        model: str | None = None,
        token_usage: dict[str, Any] | None = None,
    ) -> bool:
        user_id = await self._current_user_id()
        if user_id is None or not self.current_session_id:
            return False
        try:
            sid = uuid.UUID(self.current_session_id)
        except ValueError:
            return False
        pool = await get_pool()
        new_id = await repository.insert_message(
            pool,
            user_id,
            sid,
            role=role,
            content=content,
            model=model,
            token_usage=token_usage,
        )
        if new_id is None:
            return False
        rows = await repository.list_messages(pool, user_id, sid)
        self.thread_messages = self._thread_from_db_rows(rows)
        await self.refresh_sessions()
        return True

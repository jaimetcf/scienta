from __future__ import annotations

import reflex as rx

from reflex_ui.data import auth_crypto, repository
from reflex_ui.data.db import get_pool


class AuthState(rx.State):
    session_token: str = rx.Cookie(
        name="scienta_session",
        path="/",
        max_age=60 * 60 * 24 * 7,
        same_site="lax",
    )

    login_email: str = ""
    login_password: str = ""
    register_email: str = ""
    register_password: str = ""
    register_display_name: str = ""
    register_terms_accepted: bool = True
    auth_error: str = ""
    auth_panel: str = "login"

    @rx.var
    def logged_in(self) -> bool:
        return bool(self.session_token and self.session_token.strip())

    def set_login_email(self, v: str):
        self.login_email = v

    def set_login_password(self, v: str):
        self.login_password = v

    def set_register_email(self, v: str):
        self.register_email = v

    def set_register_password(self, v: str):
        self.register_password = v

    def set_register_display_name(self, v: str):
        self.register_display_name = v

    def set_register_terms_accepted(self, v):
        if isinstance(v, bool):
            self.register_terms_accepted = v
        else:
            self.register_terms_accepted = str(v).lower() in ("true", "1", "on", "yes")

    def show_login_panel(self):
        self.auth_panel = "login"
        self.auth_error = ""

    def show_register_panel(self):
        self.auth_panel = "register"
        self.auth_error = ""

    async def _login_submit_core(self):
        self.auth_error = ""
        email = self.login_email.strip()
        password = self.login_password
        if not email or not password:
            self.auth_error = "Email and password are required."
            return
        try:
            pool = await get_pool()
        except RuntimeError as exc:
            self.auth_error = str(exc)
            return
        user_id = await repository.authenticate_user(pool, email, password)
        if user_id is None:
            self.auth_error = "Invalid email or password."
            return
        self.session_token = auth_crypto.issue_user_token(user_id)
        self.login_password = ""

    async def login_submit(self):
        await self._login_submit_core()

    async def _register_submit_core(self):
        self.auth_error = ""
        if not self.register_terms_accepted:
            self.auth_error = "You must agree to the Terms and Conditions."
            return
        email = self.register_email.strip()
        password = self.register_password
        display = self.register_display_name.strip() or None
        if not email or not password:
            self.auth_error = "Email and password are required."
            return
        if len(password) < 8:
            self.auth_error = "Password must be at least 8 characters."
            return
        try:
            pool = await get_pool()
        except RuntimeError as exc:
            self.auth_error = str(exc)
            return
        new_id = await repository.insert_user_safe(pool, email, password, display)
        if new_id is None:
            self.auth_error = "An account with this email already exists."
            return
        self.session_token = auth_crypto.issue_user_token(new_id)
        self.register_password = ""

    async def register_submit(self):
        await self._register_submit_core()

    def logout(self):
        self.session_token = ""
        self.auth_error = ""
        self.auth_panel = "login"
        self.register_terms_accepted = True
        return rx.remove_cookie("scienta_session")

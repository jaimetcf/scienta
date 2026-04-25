"""Login and register cards based on Reflex auth recipes (default variants, no logo image)."""

import reflex as rx

from reflex_ui import style
from reflex_ui.state import State


def _auth_error_block() -> rx.Component:
    return rx.cond(
        State.auth_error != "",
        rx.box(
            rx.text(State.auth_error, size="2", color_scheme="red"),
            margin_top="0.75rem",
            padding="0.5rem",
            border_radius="6px",
            background_color=rx.color("red", 3),
            width="100%",
        ),
    )


def login_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.center(
                rx.heading(
                    "Sign in to your account",
                    size="6",
                    as_="h2",
                    text_align="center",
                    width="100%",
                ),
                direction="column",
                spacing="5",
                width="100%",
            ),
            rx.vstack(
                rx.text(
                    "Email address",
                    size="3",
                    weight="medium",
                    text_align="left",
                    width="100%",
                ),
                rx.input(
                    placeholder="you@example.com",
                    type="email",
                    size="3",
                    width="100%",
                    value=State.login_email,
                    on_change=State.set_login_email,
                    on_key_down=State.login_submit_if_enter,
                ),
                justify="start",
                spacing="2",
                width="100%",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text("Password", size="3", weight="medium"),
                    rx.link("Forgot password?", href="#", size="3"),
                    justify="between",
                    width="100%",
                ),
                rx.input(
                    placeholder="Enter your password",
                    type="password",
                    size="3",
                    width="100%",
                    value=State.login_password,
                    on_change=State.set_login_password,
                    on_key_down=State.login_submit_if_enter,
                ),
                spacing="2",
                width="100%",
            ),
            rx.button(
                "Sign in",
                size="3",
                width="100%",
                on_click=State.login_submit,
            ),
            _auth_error_block(),
            rx.center(
                rx.text("New here?", size="3"),
                rx.button(
                    "Sign up",
                    variant="ghost",
                    size="3",
                    on_click=State.show_register_panel,
                ),
                opacity="0.8",
                spacing="2",
                direction="row",
            ),
            spacing="6",
            width="100%",
        ),
        size="4",
        max_width="28em",
        width="100%",
    )


def register_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.center(
                rx.heading(
                    "Create an account",
                    size="6",
                    as_="h2",
                    text_align="center",
                    width="100%",
                ),
                direction="column",
                spacing="5",
                width="100%",
            ),
            rx.vstack(
                rx.text(
                    "Email address",
                    size="3",
                    weight="medium",
                    text_align="left",
                    width="100%",
                ),
                rx.input(
                    placeholder="you@example.com",
                    type="email",
                    size="3",
                    width="100%",
                    value=State.register_email,
                    on_change=State.set_register_email,
                    on_key_down=State.register_submit_if_enter,
                ),
                justify="start",
                spacing="2",
                width="100%",
            ),
            rx.vstack(
                rx.text(
                    "Password",
                    size="3",
                    weight="medium",
                    text_align="left",
                    width="100%",
                ),
                rx.input(
                    placeholder="At least 8 characters",
                    type="password",
                    size="3",
                    width="100%",
                    value=State.register_password,
                    on_change=State.set_register_password,
                    on_key_down=State.register_submit_if_enter,
                ),
                justify="start",
                spacing="2",
                width="100%",
            ),
            rx.vstack(
                rx.text(
                    "Display name (optional)",
                    size="3",
                    weight="medium",
                    text_align="left",
                    width="100%",
                ),
                rx.input(
                    placeholder="How we greet you",
                    type="text",
                    size="3",
                    width="100%",
                    value=State.register_display_name,
                    on_change=State.set_register_display_name,
                    on_key_down=State.register_submit_if_enter,
                ),
                justify="start",
                spacing="2",
                width="100%",
            ),
            rx.box(
                rx.checkbox(
                    "Agree to Terms and Conditions",
                    checked=State.register_terms_accepted,
                    on_change=State.set_register_terms_accepted,
                    spacing="2",
                ),
                width="100%",
            ),
            rx.button(
                "Register",
                size="3",
                width="100%",
                on_click=State.register_submit,
            ),
            _auth_error_block(),
            rx.center(
                rx.text("Already registered?", size="3"),
                rx.button(
                    "Sign in",
                    variant="ghost",
                    size="3",
                    on_click=State.show_login_panel,
                ),
                opacity="0.8",
                spacing="2",
                direction="row",
            ),
            spacing="6",
            width="100%",
        ),
        size="4",
        max_width="28em",
        width="100%",
    )


def auth_screen() -> rx.Component:
    return rx.center(
        rx.cond(
            State.auth_panel == "register",
            register_form(),
            login_form(),
        ),
        width="100%",
        flex="1",
        min_height="0",
        padding="2rem",
    )


def logged_out_sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.heading("Scienta", size="5", weight="bold"),
            rx.text(
                "Sign in to save chats and manage sessions.",
                size="2",
                color_scheme="gray",
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        width=style.session_sidebar_width,
        min_width=style.session_sidebar_min_width,
        padding="1rem",
        border_right_width="1px",
        border_right_style="solid",
        border_right_color=rx.color("gray", 5),
        background_color=rx.color("gray", 2),
        height="100%",
        min_height="0",
        overflow_y="auto",
    )

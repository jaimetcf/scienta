import reflex as rx

from reflex_ui import style
from reflex_ui.auth_forms import auth_screen, logged_out_sidebar
from reflex_ui.state import LLM_MODEL_CHOICES, State


def _typing_indicator() -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.hstack(
                rx.icon("bot", size=16, color_scheme="gray"),
                rx.spinner(size="1"),
                spacing="2",
                align="center",
            ),
            style=style.typing_style | dict(margin_left="0", margin_right="0"),
        ),
        width="100%",
        justify="center",
        padding_y="8px",
    )


def _user_message(m: dict) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text(
                        m["content"],
                        size="2",
                        style={"white_space": "pre-wrap"},
                    ),
                    rx.icon("user", size=16, color_scheme="gray"),
                    spacing="2",
                    align="start",
                ),
                rx.text(
                    m["time_display"],
                    size="1",
                    color_scheme="gray",
                    style={"opacity": 0.7},
                ),
                align="end",
                spacing="1",
                width="100%",
            ),
            style=style.question_style,
        ),
        width="100%",
        justify="end",
        padding_y="8px",
    )


def _assistant_message(m: dict) -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon("bot", size=16, color_scheme="gray"),
                    rx.markdown(
                        m["content"],
                        use_raw=False,
                        width="100%",
                    ),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
                rx.text(
                    m["time_display"],
                    size="1",
                    color_scheme="gray",
                    style={"opacity": 0.7},
                ),
                align="start",
                spacing="1",
                width="100%",
            ),
            style=style.answer_style,
        ),
        width="100%",
        justify="start",
        padding_y="8px",
    )


def _message_row(m: dict) -> rx.Component:
    return rx.cond(m["role"] == "user", _user_message(m), _assistant_message(m))


def _empty_thread() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.icon("bot", size=48, color_scheme="gray"),
            rx.text(
                "Start a conversation with your AI assistant",
                color_scheme="gray",
                size="3",
            ),
            spacing="3",
            align="center",
        ),
        padding_top="2rem",
        width="100%",
    )


def _delete_modal() -> rx.Component:
    return rx.cond(
        State.pending_delete_session_id != "",
        rx.box(
            rx.center(
                rx.box(
                    rx.heading(
                        "Delete Session",
                        size="5",
                        margin_bottom="0.5rem",
                        color_scheme="gray",
                    ),
                    rx.text(
                        "Are you sure you want to delete this session? This action cannot be undone.",
                        size="2",
                        color_scheme="gray",
                        margin_bottom="1rem",
                    ),
                    rx.hstack(
                        rx.button(
                            "Cancel",
                            variant="outline",
                            color_scheme="gray",
                            on_click=State.cancel_delete_confirm,
                            flex="1",
                        ),
                        rx.button(
                            "Delete",
                            color_scheme="red",
                            on_click=State.confirm_delete_session,
                            loading=State.is_deleting_session,
                            flex="1",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    style=style.delete_modal_panel_style,
                ),
                width="100%",
                height="100%",
            ),
            style=style.delete_modal_overlay_style,
        ),
        rx.box(),
    )


def _session_row(s: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(
                rx.vstack(
                    rx.text(
                        s["title_short"],
                        weight="medium",
                        style={
                            "width": "100%",
                            "overflow": "hidden",
                            "text_overflow": "ellipsis",
                            "white_space": "nowrap",
                        },
                    ),
                    rx.text(
                        s["updated_display"],
                        size="1",
                        color_scheme="gray",
                        style={
                            "width": "100%",
                            "overflow": "hidden",
                            "text_overflow": "ellipsis",
                            "white_space": "nowrap",
                        },
                    ),
                    spacing="0",
                    align="start",
                    width="100%",
                    min_width="0",
                ),
                flex="1",
                min_width="0",
                on_click=State.select_session(s["id"]),
                cursor="pointer",
                padding="12px",
            ),
            rx.button(
                rx.icon("trash-2", size=14),
                on_click=State.open_delete_confirm(s["id"]),
                variant="ghost",
                size="1",
                flex_shrink="0",
            ),
            width="100%",
            min_width="0",
            align="center",
            spacing="0",
        ),
        width="100%",
        min_width="0",
        overflow_x="hidden",
        border_radius="8px",
        padding_right=style.session_row_trash_inset,
        background_color=rx.cond(
            State.current_session_id == s["id"],
            rx.color("accent", 3),
            "transparent",
        ),
        _hover={"background_color": rx.color("gray", 3)},
    )


def _sessions_list_block() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.heading("Chat History", size="4", weight="bold"),
            rx.button(
                rx.icon("chevron-left", size=16),
                on_click=State.toggle_sessions_sidebar,
                variant="ghost",
                size="1",
                title="Collapse sidebar",
            ),
            width="100%",
            min_width="0",
            justify="between",
            align="center",
        ),
        rx.button(
            rx.hstack(
                rx.icon("plus", size=16),
                rx.cond(
                    State.is_creating_session,
                    rx.text("Creating..."),
                    rx.text("New Chat"),
                ),
                spacing="2",
                align="center",
            ),
            on_click=State.create_empty_session,
            disabled=State.is_creating_session,
            loading=State.is_creating_session,
            width="100%",
            style=style.button_style,
        ),
        rx.box(
            rx.cond(
                State.sessions_empty,
                rx.center(
                    rx.vstack(
                        rx.icon("message-square", size=32, color_scheme="gray"),
                        rx.text("No conversations yet", color_scheme="gray"),
                        rx.text("Start a new chat to begin", size="1", color_scheme="gray"),
                        spacing="1",
                        align="center",
                    ),
                    padding="1rem",
                ),
                rx.vstack(
                    rx.foreach(State.sessions, _session_row),
                    spacing="1",
                    width="100%",
                    min_width="0",
                    align="stretch",
                ),
            ),
            flex="1",
            min_height="0",
            min_width="0",
            width="100%",
            overflow_y="auto",
            overflow_x="hidden",
        ),
        spacing="3",
        align="stretch",
        width="100%",
        min_width="0",
        flex="1",
        min_height="0",
        overflow_x="hidden",
    )


def _sessions_sidebar_expanded() -> rx.Component:
    return rx.box(
        rx.vstack(
            _sessions_list_block(),
            spacing="3",
            align="stretch",
            width="100%",
            min_width="0",
            height="100%",
            min_height="0",
            overflow_x="hidden",
        ),
        width=style.session_sidebar_width,
        min_width=style.session_sidebar_min_width,
        max_width=style.session_sidebar_max_width,
        border_right_width="1px",
        border_right_style="solid",
        border_right_color=rx.color("gray", 5),
        background_color=rx.color("gray", 2),
        height="100%",
        min_height="0",
        overflow_x="hidden",
        padding="1rem",
        box_sizing="border-box",
    )


def _sessions_sidebar_collapsed() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.button(
                rx.icon("chevron-right", size=18),
                on_click=State.toggle_sessions_sidebar,
                variant="ghost",
                title="Expand sidebar",
            ),
            rx.button(
                rx.icon("plus", size=18),
                on_click=State.create_empty_session,
                disabled=State.is_creating_session,
                loading=State.is_creating_session,
                variant="ghost",
                title="New chat",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("log-out", size=18),
                on_click=State.logout,
                variant="ghost",
                title="Sign out",
            ),
            align="center",
            width="100%",
            height="100%",
            min_height="0",
            padding_y="1rem",
            spacing="2",
        ),
        width=style.session_sidebar_collapsed_width,
        flex_shrink="0",
        border_right_width="1px",
        border_right_style="solid",
        border_right_color=rx.color("gray", 5),
        background_color=rx.color("gray", 2),
        height="100%",
        min_height="0",
    )


def _left_sidebar() -> rx.Component:
    return rx.cond(
        State.logged_in,
        rx.cond(
            State.sessions_sidebar_collapsed,
            _sessions_sidebar_collapsed(),
            _sessions_sidebar_expanded(),
        ),
        logged_out_sidebar(),
    )


def _header_user_menu() -> rx.Component:
    return rx.dropdown_menu.root(
        rx.dropdown_menu.trigger(
            rx.button(
                rx.hstack(
                    rx.text(
                        State.current_user_email,
                        size="2",
                        color_scheme="gray",
                        style={
                            "max_width": "14rem",
                            "overflow": "hidden",
                            "text_overflow": "ellipsis",
                            "white_space": "nowrap",
                        },
                    ),
                    rx.icon("chevron-down", size=16, color_scheme="gray"),
                    spacing="2",
                    align="center",
                ),
                variant="ghost",
                height="auto",
                padding="0.5rem",
                radius="medium",
            ),
        ),
        rx.dropdown_menu.content(
            rx.box(
                rx.text(
                    State.current_user_email,
                    size="2",
                    color_scheme="gray",
                ),
                padding_x="1rem",
                padding_y="0.5rem",
                border_bottom_width="1px",
                border_bottom_style="solid",
                border_bottom_color=rx.color("gray", 4),
                width="100%",
            ),
            rx.dropdown_menu.item(
                rx.hstack(
                    rx.icon("log-out", size=16, color_scheme="gray"),
                    rx.text("Sign out", size="2", color_scheme="gray"),
                    spacing="2",
                    align="center",
                    width="100%",
                ),
                on_select=State.logout,
            ),
            side="bottom",
            align="end",
            variant="solid",
            min_width="14rem",
        ),
    )


def _header() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.heading("Chat with AI", size="6", weight="bold"),
            rx.spacer(),
            rx.hstack(
                rx.select(
                    LLM_MODEL_CHOICES,
                    value=State.llm_model,
                    on_change=State.set_llm_model,
                    disabled=State.is_loading,
                    width="12rem",
                    variant="surface",
                    size="2",
                    radius="medium",
                ),
                _header_user_menu(),
                spacing="6",
                align="center",
            ),
            width="100%",
            justify="between",
            align="center",
            spacing="3",
        ),
        style=style.header_bar_style,
    )


def _action_bar() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.box(
                rx.input(
                    value=State.question,
                    placeholder="Type your message...",
                    on_change=State.set_question,
                    on_key_down=State.submit_if_enter,
                    disabled=State.chat_input_disabled,
                    style=style.input_style,
                ),
                flex="1",
                min_width="0",
                width="100%",
            ),
            rx.button(
                rx.icon("send", size=20),
                on_click=State.answer,
                disabled=State.ask_disabled,
                loading=State.is_loading,
                min_width="3rem",
                style=style.button_style,
            ),
            width="100%",
            align="center",
            spacing="3",
            padding="1rem",
            border_top_width="1px",
            border_top_style="solid",
            border_top_color=rx.color("gray", 5),
        ),
        width="100%",
        flex_shrink="0",
    )


def _messages_area() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.cond(
                State.has_thread_messages,
                rx.foreach(State.thread_messages, _message_row),
                _empty_thread(),
            ),
            rx.cond(State.show_typing_indicator, _typing_indicator()),
            spacing="0",
            width="100%",
            align="stretch",
            padding="1rem",
        ),
        id=style.chat_scroll_area_id,
        style=style.chat_scroll_style,
    )


def _main_chat_column() -> rx.Component:
    return rx.box(
        rx.vstack(
            _header(),
            _messages_area(),
            _action_bar(),
            spacing="0",
            width="100%",
            align="stretch",
            flex="1",
            min_height="0",
        ),
        style=style.chat_column_wrapper_style,
        flex="1",
        min_width="0",
        min_height="0",
    )


def index() -> rx.Component:
    return rx.box(
        rx.hstack(
            _left_sidebar(),
            rx.box(
                rx.cond(State.logged_in, _main_chat_column(), auth_screen()),
                flex="1",
                min_width="0",
                min_height="0",
                display="flex",
                flex_direction="column",
            ),
            width="100%",
            flex="1",
            min_height="0",
            align="stretch",
        ),
        _delete_modal(),
        style=style.page_shell_style,
        padding_y=style.page_padding_y,
    )


app = rx.App()
app.add_page(index, on_load=State.on_index_load)

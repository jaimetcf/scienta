import reflex as rx

# Common style base
shadow = "rgba(0, 0, 0, 0.15) 0px 2px 8px"
chat_margin = "20%"
# Main chat column (header + messages + input): 30% wider than the original 48rem cap.
chat_column_max_width = "62.4rem"
page_padding_y = "2rem"

# Left session panel (expanded: 50% wider than the former 16rem / 14rem).
session_sidebar_width = "24rem"
session_sidebar_min_width = "21rem"
session_sidebar_max_width = "24rem"
# Collapsed strip: 20% narrower than the prior 4.5rem rail.
session_sidebar_collapsed_width = "3.6rem"
# Space between session-row trash control and the right edge of the row container.
session_row_trash_inset = "0.625rem"

# Delete-session confirmation (Radix theme colors + app shadow).
delete_modal_overlay_style = dict(
    position="fixed",
    top="0",
    left="0",
    right="0",
    bottom="0",
    z_index="9999",
    background_color=rx.color("black", 12, alpha=True),
)
delete_modal_panel_style = dict(
    background_color=rx.color("gray", 2),
    border_width="1px",
    border_style="solid",
    border_color=rx.color("gray", 6),
    border_radius="8px",
    padding="1.5rem",
    max_width="24rem",
    width="100%",
    margin_x="1rem",
    box_shadow=shadow,
)

# Chat layout: messages scroll; input row stays above the bottom inset.
chat_scroll_area_id = "chat-scroll"
chat_scroll_style = dict(
    flex="1",
    min_height="0",
    width="100%",
    overflow_y="auto",
    overflow_x="hidden",
)
page_shell_style = dict(
    width="100%",
    height="100dvh",
    box_sizing="border-box",
    display="flex",
    flex_direction="column",
    overflow="hidden",
)
chat_column_wrapper_style = dict(
    width="100%",
    max_width=chat_column_max_width,
    margin_x="auto",
    flex="1",
    min_height="0",
    display="flex",
    flex_direction="column",
)
header_bar_style = dict(
    width="100%",
    flex_shrink="0",
    padding_bottom="0.75rem",
    margin_bottom="0.25rem",
    border_bottom_width="1px",
    border_bottom_style="solid",
    border_bottom_color=rx.color("gray", 6),
)
message_style = dict(
    padding="1em",
    border_radius="5px",
    margin_y="0.5em",
    box_shadow=shadow,
    # User / assistant bubbles: 30% wider than the original 30em cap.
    max_width="39em",
    display="inline-block",
)

# Styles for questions and answers
question_style = message_style | dict(
    margin_left=chat_margin,
    background_color=rx.color("gray", 4),
)
answer_style = message_style | dict(
    margin_right=chat_margin,
    background_color=rx.color("accent", 8),
    display="block",
    overflow_x="auto",
    text_align="left",
)

typing_style = message_style | dict(
    margin_left=chat_margin,
    background_color=rx.color("gray", 4),
)

# Styles for input elements
input_style = dict(
    border_width="1px",
    padding="0.5em",
    box_shadow=shadow,
    width="100%",
    min_width="0",
)
button_style = dict(
    background_color=rx.color("accent", 10),
    box_shadow=shadow,
    cursor="pointer",
    transition="background-color 0.15s ease, box-shadow 0.15s ease, transform 0.1s ease",
    _hover=dict(
        background_color=rx.color("accent", 9),
        box_shadow="rgba(0, 0, 0, 0.2) 0px 4px 12px",
        transform="translateY(-1px)",
    ),
    _active=dict(
        background_color=rx.color("accent", 11),
        box_shadow="rgba(0, 0, 0, 0.2) 0px 1px 4px inset",
        transform="translateY(1px)",
    ),
)

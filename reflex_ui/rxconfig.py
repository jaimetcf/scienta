import reflex as rx

config = rx.Config(
    app_name="reflex_ui",
    app_module_import="reflex_ui.index",
    show_built_with_reflex=False,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ],
)
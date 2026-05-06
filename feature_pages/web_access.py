import os

import streamlit as st
import streamlit.components.v1 as components

from app_config import WEB_PAGES
from styles import page_header


def render() -> None:
    page_name = st.session_state.get("selected_page_name", "")
    config = WEB_PAGES.get(page_name, {})
    url = _page_url(page_name, config)
    note = config.get("note", "")

    page_header(page_name or "Web Access", "Open operational web tools inside the dispatch workspace.")

    if not url:
        st.warning("No URL is configured for this page yet.")
        return

    col1, col2 = st.columns([3, 1])
    col1.caption(note or url)
    col2.link_button("Open Site", url, use_container_width=True)

    if page_name == "Whatsapp":
        if url == "https://web.whatsapp.com/":
            st.warning(
                "WhatsApp Web blocks embedded frames outside WhatsApp-owned domains. "
                "Use Open Site, or add a working WHATSAPP_EMBED_URL secret from the iframe source used on your website."
            )
            return
        components.html(
            f"""
            <iframe
                src="{url}"
                style="width:100%; height:86vh; border:0;"
                allow="clipboard-read; clipboard-write; camera; microphone; fullscreen; display-capture"
                referrerpolicy="no-referrer-when-downgrade">
            </iframe>
            """,
            height=900,
            scrolling=True,
        )
    else:
        components.iframe(url, height=820, scrolling=True)
    st.caption("Some websites block embedded frames. If this area is blank or refuses to load, use Open Site.")


def _page_url(page_name: str, config: dict) -> str:
    if page_name == "Whatsapp":
        custom_url = _secret("WHATSAPP_EMBED_URL")
        if custom_url:
            return custom_url
    return config.get("url", "")


def _secret(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    try:
        return str(st.secrets.get(name, ""))
    except Exception:
        return ""

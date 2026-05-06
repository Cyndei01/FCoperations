import importlib

import streamlit as st

from app_config import APP_NAME, APP_URL, COMPANY_NAME, PAGES, WEBSITE_URL
from styles import apply_global_styles


st.set_page_config(
    page_title=APP_NAME,
    page_icon="F&C",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_styles()

enabled_pages = [page for page in PAGES if page.get("enabled")]
page_names = [page["name"] for page in enabled_pages]

with st.sidebar:
    st.markdown(
        f"""
        <div class="fc-brand-block">
            <div class="fc-brand-mark">
                <div class="fc-brand-logo">F&C</div>
                <div class="fc-brand-name">{COMPANY_NAME}</div>
            </div>
            <div class="fc-brand-subtitle">Internal fleet operations</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    selected_page_name = st.radio("Navigation", page_names, label_visibility="collapsed")
    st.markdown("---")
    st.caption(APP_URL.replace("https://", ""))
    st.caption(WEBSITE_URL.replace("https://", ""))

selected_page = next(page for page in enabled_pages if page["name"] == selected_page_name)
st.session_state["selected_page_name"] = selected_page_name
page_module = importlib.import_module(selected_page["module"])
page_module.render()

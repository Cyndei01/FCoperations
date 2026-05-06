import os

import streamlit as st

from app_config import OWNER_SETTINGS, PAGES
from feature_pages.upload_pay_sheets import render_upload_manager
from services.supabase import supabase_config_status, supabase_ready, test_supabase_connection, upload_file
from styles import page_header


def render() -> None:
    page_header("Settings", "Owner-editable defaults are centralized in app_config.py.")

    if not _settings_unlocked():
        _render_settings_login()
        return

    tab_upload, tab_knowledge, tab_supabase, tab_settings = st.tabs(
        ["Upload Pay Sheets", "Knowledge Files", "Supabase", "Owner Settings"]
    )

    with tab_upload:
        render_upload_manager()

    with tab_knowledge:
        _render_knowledge_files()

    with tab_supabase:
        _render_supabase_settings()

    with tab_settings:
        _render_owner_settings()


def _settings_unlocked() -> bool:
    if not _settings_password():
        return True
    return bool(st.session_state.get("settings_unlocked"))


def _render_settings_login() -> None:
    st.info("Settings are protected. Enter the settings password to make changes.")
    with st.form("settings_password_form"):
        password = st.text_input("Settings password", type="password")
        submitted = st.form_submit_button("Unlock Settings")
    if submitted:
        if password == _settings_password():
            st.session_state["settings_unlocked"] = True
            st.rerun()
        st.error("Invalid settings password.")


def _settings_password() -> str:
    return os.getenv("SETTINGS_PASSWORD") or os.getenv("APP_PASSWORD", "")


def _render_knowledge_files() -> None:
    st.write("Upload reference files that should inform the Sprinter Heat Map and Relocation Finder.")
    uploaded_files = st.file_uploader(
        "Knowledge files",
        type=["txt", "md", "csv", "xlsx", "pdf"],
        accept_multiple_files=True,
    )
    if uploaded_files:
        stored = []
        for uploaded_file in uploaded_files:
            content = uploaded_file.getvalue()
            stored.append(
                {
                    "name": uploaded_file.name,
                    "type": uploaded_file.name.rsplit(".", 1)[-1].lower(),
                    "size": uploaded_file.size,
                    "content": content,
                }
            )
            if supabase_ready():
                ok, message = upload_file(uploaded_file.name, content, "knowledge-files")
                if ok:
                    st.caption(f"Saved {uploaded_file.name} to Supabase: {message}")
                else:
                    st.warning(message)
        st.session_state["knowledge_files"] = stored
        st.success(f"Stored {len(stored)} knowledge file(s) for this session.")

    knowledge_files = st.session_state.get("knowledge_files", [])
    if knowledge_files:
        st.dataframe(
            [
                {
                    "File": item["name"],
                    "Type": item["type"].upper(),
                    "Size KB": round(item["size"] / 1024, 1),
                }
                for item in knowledge_files
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.caption("These files are stored in the current app session. Persistent storage can be added with Supabase.")
    else:
        st.info("No knowledge files uploaded yet.")


def _render_supabase_settings() -> None:
    status = supabase_config_status()
    st.dataframe(
        [
            {"Setting": "SUPABASE_URL", "Configured": status["url"]},
            {"Setting": "SUPABASE_SERVICE_ROLE_KEY", "Configured": status["service_role_key"]},
            {"Setting": "SUPABASE_ANON_KEY", "Configured": status["anon_key"]},
            {"Setting": "Storage bucket", "Configured": status["bucket"]},
        ],
        use_container_width=True,
        hide_index=True,
    )
    if st.button("Test Supabase Connection", use_container_width=True):
        ok, message = test_supabase_connection()
        if ok:
            st.success(message)
        else:
            st.error(message)
    st.caption("Add Supabase secrets in Streamlit Cloud. Files are uploaded to private Supabase Storage when configured.")


def _render_owner_settings() -> None:
    split = OWNER_SETTINGS["revenue_split"]
    col1, col2, col3 = st.columns(3)
    col1.metric("Company Revenue Split", f"{split['company_percent']}%")
    col2.metric("Driver Revenue Split", f"{split['driver_percent']}%")
    col3.metric("Relocation Limit", f"{OWNER_SETTINGS['relocation_distance_limit_miles']} mi")

    st.subheader("Weather Sensitivity")
    st.write(OWNER_SETTINGS["weather_sensitivity"].title())

    st.subheader("Enabled Pages")
    st.dataframe(
        [{"Page": page["name"], "Enabled": page["enabled"]} for page in PAGES],
        use_container_width=True,
        hide_index=True,
    )

    st.info("To reorder, hide, or show pages, edit PAGES in app_config.py.")

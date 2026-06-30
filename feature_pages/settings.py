import os

import pandas as pd
import streamlit as st

from app_config import OWNER_SETTINGS, PAGES
from feature_pages.upload_pay_sheets import render_upload_manager
from services.load_parser import get_session_load_history, origin_market_summary, parse_load_history_file
from services.manufacturing_locations import (
    load_manufacturing_locations,
    parse_manufacturing_locations,
    save_manufacturing_locations,
)
from services.supabase import (
    download_file,
    download_knowledge_manifest,
    supabase_ready,
    upload_knowledge_file,
    upload_parsed_load_history,
)
from styles import page_header


def render() -> None:
    page_header("Settings", "Owner-editable defaults are centralized in app_config.py.")

    if not _settings_unlocked():
        _render_settings_login()
        return

    tab_upload, tab_knowledge, tab_settings = st.tabs(
        ["Optional Pay Sheets", "Knowledge Files", "Owner Settings"]
    )

    with tab_upload:
        render_upload_manager()

    with tab_knowledge:
        _render_knowledge_files()

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
    return os.getenv("SETTINGS_PASSWORD") or os.getenv("APP_PASSWORD", "") or _secret("SETTINGS_PASSWORD") or _secret("APP_PASSWORD")


def _render_knowledge_files() -> None:
    st.write("Upload reference files that should inform the Sprinter Heat Map and Relocation Finder.")
    st.caption(
        "CSV or Excel historical load files are saved as the baseline outbound history. "
        "CSV, Excel, and text-based PDF files with manufacturing plant city/state details are also parsed into relocation density."
    )
    _load_saved_knowledge_manifest()
    _load_saved_manufacturing_locations()
    _load_saved_historical_knowledge_files()
    if not supabase_ready():
        st.warning("Supabase is not configured, so knowledge files will disappear after refresh.")

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
                ok, message = upload_knowledge_file(uploaded_file.name, content)
                if ok:
                    st.caption(f"Saved {uploaded_file.name} to Supabase: {message}")
                else:
                    st.warning(message)
            parsed_locations = parse_manufacturing_locations(uploaded_file.name, content)
            if not parsed_locations.empty:
                existing_locations = st.session_state.get("manufacturing_locations")
                if isinstance(existing_locations, pd.DataFrame) and not existing_locations.empty:
                    parsed_locations = pd.concat(
                        [existing_locations, parsed_locations],
                        ignore_index=True,
                    ).drop_duplicates()
                st.session_state["manufacturing_locations"] = parsed_locations
                if supabase_ready():
                    ok, message = save_manufacturing_locations(parsed_locations)
                    if ok:
                        st.caption(f"Saved {len(parsed_locations):,} parsed manufacturing locations.")
                    else:
                        st.warning(message)
            parsed_loads = parse_load_history_file(uploaded_file.name, content)
            if not parsed_loads.empty:
                existing_loads = get_session_load_history(st)
                combined_loads = _merge_load_history(existing_loads, parsed_loads)
                st.session_state["load_history"] = combined_loads
                st.session_state["load_history_source"] = "Knowledge files"
                if supabase_ready():
                    ok, message = upload_parsed_load_history(combined_loads)
                    if ok:
                        st.caption(f"Saved {len(combined_loads):,} historical loads for future sessions.")
                    else:
                        st.warning(message)
        saved_manifest = download_knowledge_manifest() if supabase_ready() else []
        st.session_state["knowledge_files"] = saved_manifest or stored
        st.success(f"Stored {len(stored)} knowledge file(s) for this session.")

    current_loads = get_session_load_history(st)
    if not current_loads.empty:
        summary = origin_market_summary(current_loads)
        st.subheader("Saved Historical Load History")
        col1, col2, col3 = st.columns(3)
        col1.metric("Loads", f"{len(current_loads):,}")
        col2.metric("Origin Markets", f"{current_loads['origin_market'].nunique():,}")
        col3.metric("Top Origin", summary.iloc[0]["origin_market"] if not summary.empty else "None")
        st.caption("This saved outbound history powers the Sprinter Heat Map and Relocation Finder. Weekly pay-sheet uploads are optional.")

    manufacturing_locations = st.session_state.get("manufacturing_locations")
    if isinstance(manufacturing_locations, pd.DataFrame) and not manufacturing_locations.empty:
        st.subheader("Parsed Manufacturing Locations")
        col1, col2 = st.columns(2)
        col1.metric("Facilities Parsed", f"{len(manufacturing_locations):,}")
        col2.metric("Markets", f"{manufacturing_locations['market'].nunique():,}")
        st.dataframe(
            manufacturing_locations.head(100),
            use_container_width=True,
            hide_index=True,
        )

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
        st.caption("These files are stored in the current app session and saved to Supabase when configured.")
    else:
        st.info("No knowledge files uploaded yet.")


def _load_saved_knowledge_manifest() -> None:
    if st.session_state.get("knowledge_files") or not supabase_ready():
        return
    saved_files = download_knowledge_manifest()
    if saved_files:
        st.session_state["knowledge_files"] = saved_files


def _load_saved_manufacturing_locations() -> None:
    if isinstance(st.session_state.get("manufacturing_locations"), pd.DataFrame):
        return
    locations = load_manufacturing_locations(st)
    if not locations.empty:
        st.session_state["manufacturing_locations"] = locations


def _load_saved_historical_knowledge_files() -> None:
    if not supabase_ready() or not get_session_load_history(st).empty:
        return

    knowledge_files = st.session_state.get("knowledge_files", [])
    parsed_tables = []
    for item in knowledge_files:
        file_type = str(item.get("type", "")).lower()
        if file_type not in {"csv", "xlsx"}:
            continue
        path = item.get("path")
        if not path:
            continue
        ok, payload = download_file(path)
        if not ok or not isinstance(payload, bytes):
            continue
        parsed_loads = parse_load_history_file(str(item.get("name", "knowledge file")), payload)
        if not parsed_loads.empty:
            parsed_tables.append(parsed_loads)

    if not parsed_tables:
        return

    loads = _merge_load_history(pd.DataFrame(), pd.concat(parsed_tables, ignore_index=True))
    st.session_state["load_history"] = loads
    st.session_state["load_history_source"] = "Knowledge files"
    upload_parsed_load_history(loads)


def _merge_load_history(existing_loads: pd.DataFrame, new_loads: pd.DataFrame) -> pd.DataFrame:
    tables = []
    if isinstance(existing_loads, pd.DataFrame) and not existing_loads.empty:
        tables.append(existing_loads)
    if isinstance(new_loads, pd.DataFrame) and not new_loads.empty:
        tables.append(new_loads)
    if not tables:
        return pd.DataFrame()
    return (
        pd.concat(tables, ignore_index=True)
        .drop_duplicates(
            subset=["order_number", "origin_market", "destination_market", "pay", "loaded_miles"],
            keep="first",
        )
        .reset_index(drop=True)
    )


def _secret(name: str) -> str:
    try:
        return str(st.secrets.get(name, ""))
    except Exception:
        return ""


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

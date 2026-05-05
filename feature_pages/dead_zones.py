import pandas as pd
import streamlit as st

from services.load_parser import dead_zone_summary, get_session_load_history
from styles import page_header


def render() -> None:
    page_header("Dead Zones", "Flag areas with weak outbound opportunities.")

    loads = get_session_load_history(st)
    if not loads.empty:
        source = st.session_state.get("load_history_source", "uploaded pay sheet")
        st.success(f"Using parsed load history from {source}.")
        zones = dead_zone_summary(loads)

        high_risk_count = int((zones["risk"] == "High").sum())
        col1, col2, col3 = st.columns(3)
        col1.metric("Markets Reviewed", f"{len(zones):,}")
        col2.metric("High Risk Dead Zones", f"{high_risk_count:,}")
        col3.metric("Weakest Reload Market", zones.iloc[0]["market"])

        display = zones.rename(
            columns={
                "market": "Market",
                "inbound_loads": "Inbound Loads",
                "outbound_loads": "Outbound Loads",
                "outbound_ratio": "Outbound / Inbound",
                "risk": "Risk",
                "suggested_action": "Suggested Action",
            }
        )
        st.dataframe(display.head(30), use_container_width=True, hide_index=True)
        st.caption("Dead Zones compare where drivers delivered against how often that market produced outbound loads in your history.")
        return

    st.info("Upload your Excel load history on the Upload Pay Sheets page to calculate real dead zones.")
    data = pd.DataFrame(
        [
            {"Market": "El Paso, TX", "Outbound Score": "Low", "Suggested Action": "Avoid unless pre-booked"},
            {"Market": "Jackson, MS", "Outbound Score": "Low", "Suggested Action": "Relocate within limit"},
            {"Market": "Memphis, TN", "Outbound Score": "Watch", "Suggested Action": "Confirm reload first"},
        ]
    )
    st.dataframe(data, use_container_width=True, hide_index=True)

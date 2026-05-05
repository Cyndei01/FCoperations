import pandas as pd
import streamlit as st

from services.load_parser import get_session_load_history, origin_market_summary
from styles import page_header


def render() -> None:
    page_header("Hot Markets", "Identify markets with strong load volume and pricing.")

    loads = get_session_load_history(st)
    if not loads.empty:
        source = st.session_state.get("load_history_source", "uploaded pay sheet")
        st.success(f"Using parsed load history from {source}.")
        summary = origin_market_summary(loads)

        col1, col2, col3 = st.columns(3)
        col1.metric("Loads Parsed", f"{len(loads):,}")
        col2.metric("Origin Markets", f"{loads['origin_market'].nunique():,}")
        col3.metric("Top Origin", summary.iloc[0]["origin_market"])

        display = summary.rename(
            columns={
                "origin_market": "Origin Market",
                "loads": "Load Count",
                "average_pay": "Average Pay",
                "total_pay": "Total Pay",
                "average_loaded_miles": "Avg Loaded Miles",
                "average_empty_miles": "Avg Empty Miles",
                "priority": "Priority",
            }
        )
        st.dataframe(display.head(25), use_container_width=True, hide_index=True)
        return

    st.info("Upload your Excel load history on the Upload Pay Sheets page to calculate real hot markets.")
    data = pd.DataFrame(
        [
            {"Market": "Atlanta, GA", "Load Volume": "High", "Rate Trend": "+8%", "Priority": "High"},
            {"Market": "Dallas, TX", "Load Volume": "High", "Rate Trend": "+6%", "Priority": "High"},
            {"Market": "Columbus, OH", "Load Volume": "Medium", "Rate Trend": "+4%", "Priority": "Medium"},
        ]
    )
    st.dataframe(data, use_container_width=True, hide_index=True)

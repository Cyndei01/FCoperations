import streamlit as st

from feature_pages._shared import sample_lane_table
from services.load_parser import get_session_load_history, lane_summary
from styles import page_header


def render() -> None:
    page_header("Best Lanes", "Rank lanes by rate quality, distance, and operational fit.")

    loads = get_session_load_history(st)
    if not loads.empty:
        source = st.session_state.get("load_history_source", "uploaded pay sheet")
        st.success(f"Using parsed load history from {source}.")
        lanes = lane_summary(loads)
        min_loads = st.slider("Minimum historical loads", min_value=1, max_value=10, value=2)
        lanes = lanes[lanes["loads"] >= min_loads]

        if lanes.empty:
            st.warning("No lanes match the selected minimum load count.")
            return

        col1, col2, col3 = st.columns(3)
        col1.metric("Lane Pairs", f"{len(lanes):,}")
        col2.metric("Best Lane", f"{lanes.iloc[0]['origin_market']} to {lanes.iloc[0]['destination_market']}")
        col3.metric("Best Lane Loads", f"{int(lanes.iloc[0]['loads']):,}")

        display = lanes.rename(
            columns={
                "origin_market": "Origin",
                "destination_market": "Destination",
                "loads": "Load Count",
                "average_pay": "Average Pay",
                "total_pay": "Total Pay",
                "average_loaded_miles": "Avg Loaded Miles",
                "average_empty_miles": "Avg Empty Miles",
                "average_driving_hours": "Avg Driving Hours",
                "pay_per_loaded_mile": "Pay / Loaded Mile",
                "reliability": "Reliability",
                "lane_score": "Lane Score",
            }
        )
        st.dataframe(display.head(30), use_container_width=True, hide_index=True)
        st.caption("Lane Score favors repeat frequency and pay per loaded mile, with a penalty for empty miles.")
        return

    st.info("Upload your Excel load history on the Upload Pay Sheets page to calculate real best lanes.")
    st.dataframe(sample_lane_table(), use_container_width=True, hide_index=True)

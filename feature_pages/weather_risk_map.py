import pandas as pd
import streamlit as st

from app_config import LIVE_DATA, OWNER_SETTINGS
from services.live_sources import weather_table_for_markets
from services.load_parser import get_session_load_history, origin_market_summary
from styles import page_header


def render() -> None:
    sensitivity = OWNER_SETTINGS["weather_sensitivity"]
    page_header("Weather Risk Map", "Review weather exposure for active lanes and markets.")

    st.metric("Weather Sensitivity", sensitivity.title())

    loads = get_session_load_history(st)
    if not loads.empty:
        summary = origin_market_summary(loads)
        default_markets = summary["origin_market"].head(LIVE_DATA["max_live_markets"]).tolist()
        selected_markets = st.multiselect(
            "Markets to check",
            summary["origin_market"].tolist(),
            default=default_markets,
            max_selections=10,
        )

        if st.button("Refresh Live Weather", use_container_width=True):
            if selected_markets:
                with st.spinner("Pulling live weather from the National Weather Service..."):
                    st.session_state["live_weather_table"] = weather_table_for_markets(selected_markets)
            else:
                st.warning("Select at least one market.")

        weather_table = st.session_state.get("live_weather_table")
        if isinstance(weather_table, pd.DataFrame) and not weather_table.empty:
            high_risk = int((weather_table["Risk"] == "High").sum())
            medium_risk = int((weather_table["Risk"] == "Medium").sum())
            col1, col2, col3 = st.columns(3)
            col1.metric("Markets Checked", f"{len(weather_table):,}")
            col2.metric("High Risk", f"{high_risk:,}")
            col3.metric("Medium Risk", f"{medium_risk:,}")
            st.dataframe(weather_table, use_container_width=True, hide_index=True)
            st.caption("Live weather uses free National Weather Service data. Geocoding is cached to keep public API use light.")
        else:
            st.info("Upload load history, select markets, then refresh live weather.")
        return

    st.info("Upload load history first to check weather risk for your actual freight markets.")
    data = pd.DataFrame(
        [
            {"Lane": "Chicago to Nashville", "Risk": "Medium", "Reason": "Heavy rain"},
            {"Lane": "Dallas to Atlanta", "Risk": "Low", "Reason": "Clear"},
            {"Lane": "Denver to Kansas City", "Risk": "High", "Reason": "Winter conditions"},
        ]
    )
    st.dataframe(data, use_container_width=True, hide_index=True)

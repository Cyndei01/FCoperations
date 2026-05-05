import pandas as pd
import requests
import streamlit as st

from app_config import FREE_FREIGHT_SOURCES
from feature_pages._shared import owner_setting_summary
from services.live_sources import geocode_market
from services.load_parser import get_session_load_history, origin_market_summary
from styles import page_header


def render() -> None:
    page_header("Live Freight Map", "Monitor active freight markets and lane opportunities.")
    owner_setting_summary()

    loads = get_session_load_history(st)
    if not loads.empty:
        summary = origin_market_summary(loads)
        mapped_markets = _markets_to_map(summary.head(20))

        if not mapped_markets.empty:
            st.subheader("Internal Historical Freight Signal")
            st.map(mapped_markets, latitude="lat", longitude="lon", size="loads")
            st.dataframe(
                summary.rename(
                    columns={
                        "origin_market": "Origin Market",
                        "loads": "Historical Loads",
                        "average_pay": "Average Pay",
                        "average_loaded_miles": "Avg Loaded Miles",
                        "average_empty_miles": "Avg Empty Miles",
                        "priority": "Priority",
                    }
                ).head(20),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Historical markets are parsed, but live geocoding was unavailable for the map.")
    else:
        st.info("Upload load history first to map F&C's historical origin markets.")

    st.markdown('<div class="fc-section"></div>', unsafe_allow_html=True)
    st.subheader("External Free Freight Signals")
    st.caption("These are useful free-to-view sources. Automatic pulling depends on whether the provider exposes a public API or public data files.")
    st.dataframe(pd.DataFrame(FREE_FREIGHT_SOURCES), use_container_width=True, hide_index=True)

    for source in FREE_FREIGHT_SOURCES:
        st.link_button(f"Open {source['name']}", source["url"], use_container_width=False)


def _markets_to_map(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in summary.iterrows():
        try:
            location = geocode_market(row["origin_market"])
        except requests.RequestException:
            location = None
        if not location:
            continue
        rows.append(
            {
                "market": row["origin_market"],
                "loads": int(row["loads"]),
                "lat": location["lat"],
                "lon": location["lon"],
            }
        )
    return pd.DataFrame(rows)


def _placeholder_map() -> None:
    map_data = pd.DataFrame(
        [
            {"lat": 33.7490, "lon": -84.3880, "market": "Atlanta", "loads": 42},
            {"lat": 41.8781, "lon": -87.6298, "market": "Chicago", "loads": 35},
            {"lat": 29.7604, "lon": -95.3698, "market": "Houston", "loads": 29},
            {"lat": 32.7767, "lon": -96.7970, "market": "Dallas", "loads": 38},
        ]
    )
    st.map(map_data, latitude="lat", longitude="lon", size="loads")
    st.dataframe(map_data, use_container_width=True, hide_index=True)

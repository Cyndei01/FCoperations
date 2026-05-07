import pandas as pd
import streamlit as st

from app_config import LIVE_DATA, MARKET_INTELLIGENCE_SOURCES
from services.live_sources import weather_table_for_markets
from services.load_parser import dead_zone_summary, get_session_load_history, lane_summary, origin_market_summary
from services.manufacturing_locations import load_manufacturing_locations
from services.market_intelligence import (
    TREND_ADJUSTMENTS,
    apply_market_intelligence,
    default_market_intelligence,
    normalize_market_intelligence,
)
from services.sprinter_heatmap import build_sprinter_heat_map
from styles import page_header


def render() -> None:
    page_header(
        "Sprinter Heat Map",
        "Rank outbound markets using F&C load history plus free industrial, warehouse, and automotive-density signals.",
    )

    loads = get_session_load_history(st)
    if loads.empty:
        st.info("Upload your Excel pay sheet history first. The heat map uses your actual pickup history as the strongest signal.")
        return

    st.caption(f"Load history source: {st.session_state.get('load_history_source', 'Current session')}. Parsed loads: {len(loads):,}.")
    _render_knowledge_file_status()
    knowledge_locations = load_manufacturing_locations(st)
    if not knowledge_locations.empty:
        st.caption(
            f"Knowledge density active: {len(knowledge_locations):,} plants/distribution centers "
            f"across {knowledge_locations['market'].nunique():,} markets."
        )

    col1, col2 = st.columns(2)
    market_limit = col1.slider("Markets to score", min_value=5, max_value=30, value=15)
    radius_miles = col2.slider("Industrial search radius", min_value=10, max_value=75, value=35, step=5)
    include_industrial_density = st.checkbox(
        "Add public industrial-density enrichment",
        value=False,
        help="Slower. Uses free OpenStreetMap/Overpass calls for the top few markets only.",
    )
    industrial_market_limit = 0
    if include_industrial_density:
        industrial_market_limit = st.slider("Markets to enrich with public industrial data", min_value=1, max_value=8, value=3)

    if st.button("Build / Refresh Heat Map", use_container_width=True):
        status = st.empty()
        progress = st.progress(0)

        def update_progress(done: int, total: int, market: str) -> None:
            status.write(f"Scoring {market} ({done} of {total})")
            progress.progress(done / total)

        with st.spinner("Building sprinter opportunity heat map..."):
            try:
                st.session_state["sprinter_heat_map"] = build_sprinter_heat_map(
                    loads,
                    market_limit,
                    radius_miles,
                    include_industrial_density,
                    industrial_market_limit,
                    knowledge_locations,
                    update_progress,
                )
                status.write("Heat map complete.")
            except Exception as error:
                status.empty()
                st.error("The heat map could not be generated.")
                st.exception(error)
                return

    heat_map = st.session_state.get("sprinter_heat_map")
    if isinstance(heat_map, pd.DataFrame) and not heat_map.empty:
        intelligence = st.session_state.get("market_intelligence")
        if isinstance(intelligence, pd.DataFrame):
            heat_map = apply_market_intelligence(heat_map, intelligence)

    tab_map, tab_origins, tab_dead_zones, tab_lanes, tab_weather, tab_intel = st.tabs(
        ["Outbound Score", "Hot Origins", "Dead Zones", "Best Lanes", "Weather Risk", "Market Intelligence"]
    )

    with tab_map:
        _render_outbound_score(heat_map)

    with tab_origins:
        _render_hot_origins(loads)

    with tab_dead_zones:
        _render_dead_zones(loads)

    with tab_lanes:
        _render_best_lanes(loads)

    with tab_weather:
        _render_weather_risk(loads)

    with tab_intel:
        _render_market_intelligence()


def _render_outbound_score(heat_map: object) -> None:
    if not isinstance(heat_map, pd.DataFrame) or heat_map.empty:
        st.info("Click Build / Refresh Heat Map above to score your top origin markets.")
        return

    heat_map = _normalize_heat_map_display_columns(heat_map)
    mapped = heat_map.dropna(subset=["lat", "lon"]).copy()
    if not mapped.empty:
        st.map(mapped, latitude="lat", longitude="lon", size="map_size")

    best = heat_map.iloc[0]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Best Market", best["market"])
    col1.caption(str(best.get("market_temperature", "")))
    col2.metric("Opportunity Score", f"{best['opportunity_score']:.1f}")
    col3.metric("Historical Loads", f"{int(best['historical_loads']):,}")
    col4.metric("Industrial Points", f"{int(best['industrial_points']):,}")

    display = heat_map.rename(columns=_heat_map_columns())
    st.dataframe(
        display[
            [
                "Market",
                "Opportunity Score",
                "Market Temperature",
                "Confidence",
                "Base Score",
                "Market Intel Adjustment",
                "Historical Loads",
                "PPM",
                "Avg Loaded Miles",
                "Repeat Facilities",
                "Knowledge Plant/DC Points",
                "Industrial / Warehouse Points",
                "Auto / Distribution Matches",
                "Density Source",
                "Market Intel Notes",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Score uses F&C pickup frequency, average pay, repeat pickup facilities, parsed knowledge-file plant/DC locations, market intelligence, and optional free OpenStreetMap industrial/warehouse/automotive density."
    )


def _render_knowledge_file_status() -> None:
    knowledge_files = st.session_state.get("knowledge_files", [])
    if knowledge_files:
        st.caption(
            f"Knowledge files stored for reference: {len(knowledge_files)}. "
            "Manufacturing/distribution files with city/state details add density; pay sheets add load history."
        )


def _normalize_heat_map_display_columns(heat_map: pd.DataFrame) -> pd.DataFrame:
    normalized = heat_map.copy()
    if "base_opportunity_score" not in normalized.columns:
        normalized["base_opportunity_score"] = normalized.get("opportunity_score", 0)
    if "market_intel_adjustment" not in normalized.columns:
        normalized["market_intel_adjustment"] = 0.0
    if "market_intel_notes" not in normalized.columns:
        normalized["market_intel_notes"] = ""
    if "knowledge_manufacturing_points" not in normalized.columns:
        normalized["knowledge_manufacturing_points"] = 0
    if "market_temperature" not in normalized.columns:
        normalized["market_temperature"] = normalized.get("opportunity_score", 0).apply(_temperature_label)
    if "density_source" not in normalized.columns:
        normalized["density_source"] = "History only"
    return normalized


def _temperature_label(score: object) -> str:
    if pd.isna(score):
        return "Cold"
    score_value = float(score or 0)
    if score_value >= 70:
        return "Hot"
    if score_value >= 45:
        return "Warm"
    if score_value >= 20:
        return "Watch"
    return "Cold"


def _render_hot_origins(loads: pd.DataFrame) -> None:
    summary = origin_market_summary(loads).rename(
        columns={
            "origin_market": "Origin Market",
            "loads": "Historical Loads",
            "average_pay": "Avg Pay",
            "total_pay": "Total Pay",
            "average_loaded_miles": "Avg Loaded Miles",
            "average_empty_miles": "Avg Empty Miles",
            "priority": "Priority",
        }
    )
    st.dataframe(summary.head(40), use_container_width=True, hide_index=True)
    st.caption("Hot Origins are the markets where F&C has historically picked up the most sprinter/LTL loads.")


def _render_dead_zones(loads: pd.DataFrame) -> None:
    zones = dead_zone_summary(loads).rename(
        columns={
            "market": "Market",
            "inbound_loads": "Inbound Loads",
            "outbound_loads": "Outbound Loads",
            "outbound_ratio": "Outbound / Inbound",
            "risk": "Risk",
            "suggested_action": "Suggested Action",
        }
    )
    st.dataframe(zones.head(40), use_container_width=True, hide_index=True)
    st.caption("Dead Zones compare delivery frequency against historical outbound pickup frequency.")


def _render_best_lanes(loads: pd.DataFrame) -> None:
    min_loads = st.slider("Minimum historical loads for lane view", min_value=1, max_value=10, value=2)
    lanes = lane_summary(loads)
    lanes = lanes[lanes["loads"] >= min_loads]

    if lanes.empty:
        st.warning("No lanes match the selected minimum load count.")
        return

    display = lanes.rename(
        columns={
            "origin_market": "Origin",
            "destination_market": "Destination",
            "loads": "Load Count",
            "average_pay": "Avg Pay",
            "total_pay": "Total Pay",
            "average_loaded_miles": "Avg Loaded Miles",
            "average_empty_miles": "Avg Empty Miles",
            "average_driving_hours": "Avg Driving Hours",
            "pay_per_loaded_mile": "Pay / Loaded Mile",
            "reliability": "Reliability",
            "lane_score": "Lane Score",
        }
    )
    st.dataframe(display.head(40), use_container_width=True, hide_index=True)
    st.caption("Best Lanes favors repeat frequency first, then pay quality and operational fit.")


def _render_weather_risk(loads: pd.DataFrame) -> None:
    summary = origin_market_summary(loads)
    default_markets = summary["origin_market"].head(LIVE_DATA["max_live_markets"]).tolist()
    selected_markets = st.multiselect(
        "Markets to check",
        summary["origin_market"].tolist(),
        default=default_markets,
        max_selections=10,
    )

    if st.button("Refresh Weather Risk", use_container_width=True):
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
        st.info("Select markets, then refresh live weather.")


def _render_market_intelligence() -> None:
    st.caption("Use free public reports as score adjustments. This keeps the heat map honest without scraping paid SONAR data.")
    st.dataframe(pd.DataFrame(MARKET_INTELLIGENCE_SOURCES), use_container_width=True, hide_index=True)

    current_signals = st.session_state.get("market_intelligence")
    if not isinstance(current_signals, pd.DataFrame):
        current_signals = default_market_intelligence()

    edited_signals = st.data_editor(
        current_signals,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Trend": st.column_config.SelectboxColumn(
                "Trend",
                options=list(TREND_ADJUSTMENTS.keys()),
                required=True,
            ),
            "Score Adjustment": st.column_config.NumberColumn(
                "Score Adjustment",
                min_value=-25,
                max_value=25,
                step=1,
            ),
        },
    )
    st.session_state["market_intelligence"] = normalize_market_intelligence(edited_signals)

    for source in MARKET_INTELLIGENCE_SOURCES:
        st.link_button(f"Open {source['name']}", source["url"])


def _heat_map_columns() -> dict[str, str]:
    return {
        "market": "Market",
        "historical_loads": "Historical Loads",
        "average_pay": "Avg Pay",
        "pay_per_mile": "PPM",
        "average_loaded_miles": "Avg Loaded Miles",
        "average_empty_miles": "Avg Empty Miles",
        "repeat_facilities": "Repeat Facilities",
        "knowledge_manufacturing_points": "Knowledge Plant/DC Points",
        "industrial_points": "Industrial / Warehouse Points",
        "automotive_points": "Auto / Distribution Matches",
        "opportunity_score": "Opportunity Score",
        "market_temperature": "Market Temperature",
        "base_opportunity_score": "Base Score",
        "market_intel_adjustment": "Market Intel Adjustment",
        "market_intel_notes": "Market Intel Notes",
        "density_source": "Density Source",
        "confidence": "Confidence",
    }

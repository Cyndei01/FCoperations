import pandas as pd
import streamlit as st

from app_config import OWNER_SETTINGS
from services.google_maps import google_maps_ready
from services.mapbox import mapbox_ready
from services.load_parser import get_session_load_history, origin_market_summary
from services.momentum import momentum_driver_location_options, momentum_ready
from services.relocation import RELOCATION_MODEL_VERSION, build_relocation_recommendations
from styles import page_header


def render() -> None:
    default_limit = OWNER_SETTINGS["relocation_distance_limit_miles"]
    page_header("Relocation Finder", "Rank reposition markets using distance, F&C history, and industrial density.")

    loads = get_session_load_history(st)
    if not loads.empty:
        _render_knowledge_file_status()
        summary = _relocation_candidate_summary(loads)
        market_options = summary["origin_market"].tolist()
        st.subheader("Relocation Search")
        selected_van, start_market, start_source = _driver_start_market_selector(market_options)
        use_relocation_limit = st.checkbox("Use relocation distance limit", value=False)
        relocation_limit = None
        if use_relocation_limit:
            relocation_limit = st.number_input(
                "Relocation distance limit",
                min_value=25,
                max_value=1500,
                value=int(default_limit),
                step=25,
            )
        target_count = 15
        use_live_distance = True
        current_context = {
            "van": selected_van,
            "start_market": start_market,
            "start_source": start_source,
            "use_relocation_limit": bool(use_relocation_limit),
            "relocation_limit": int(relocation_limit) if relocation_limit is not None else None,
            "target_count": int(target_count),
            "use_live_distance": bool(use_live_distance),
            "model_version": RELOCATION_MODEL_VERSION,
        }

        heat_map = st.session_state.get("sprinter_heat_map")
        if not isinstance(heat_map, pd.DataFrame):
            heat_map = None

        if st.button("Find Best Reposition Markets", use_container_width=True):
            with st.spinner("Ranking reposition options..."):
                st.session_state["relocation_recommendations"] = build_relocation_recommendations(
                    start_market,
                    summary,
                    heat_map,
                    int(relocation_limit) if relocation_limit is not None else None,
                    target_count,
                    use_live_distance,
                )
                st.session_state["relocation_context"] = current_context

        recommendations = st.session_state.get("relocation_recommendations")
        if not isinstance(recommendations, pd.DataFrame) or recommendations.empty:
            st.info("Click Find Best Reposition Markets to rank outbound options. Build the Sprinter Heat Map first for stronger recommendations.")
            return

        context = st.session_state.get("relocation_context", {})
        if context != current_context:
            st.warning("Relocation inputs changed. Click Find Best Reposition Markets again to update the recommendation.")
            return

        best = recommendations.iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Van", context.get("van") or selected_van or "Manual")
        col2.metric("Start Market", context.get("start_market") or start_market)
        col3.metric("Top Option", best["origin_market"])
        col4.metric("Distance", _format_distance(best.get("distance_miles")))
        st.caption(f"Start source: {context.get('start_source') or start_source}")
        st.success("Three relocation options ordered as practical stepping moves.")

        display = recommendations.rename(
            columns={
                "origin_market": "Target Market",
                "loads": "Historical Loads",
                "ppm": "PPM",
                "heat_score": "Heat Score",
                "confidence": "Confidence",
                "industrial_points": "Industrial / Warehouse Points",
                "automotive_points": "Automotive / Manufacturing Points",
                "distance_miles": "Distance Miles",
                "drive_minutes": "Drive Minutes",
                "distance_source": "Distance Source",
                "traffic_condition": "Traffic",
                "weather_risk": "Weather Risk",
                "weather_summary": "Weather Summary",
                "dispatch_note": "Dispatch Note",
                "distance_score": "Distance Score",
                "history_score": "History Score",
                "density_score": "Density Score",
                "relocation_score": "Relocation Score",
                "priority": "Priority",
                "recommendation": "Recommendation",
                "reason": "Reason",
            }
        )
        display.insert(0, "Option", [f"Option {index}" for index in range(1, len(display) + 1)])

        columns = [
            "Option",
            "Target Market",
            "Historical Loads",
            "Industrial / Warehouse Points",
            "Automotive / Manufacturing Points",
            "PPM",
            "Distance Miles",
            "Drive Minutes",
            "Distance Source",
            "Traffic",
            "Weather Risk",
            "Weather Summary",
            "Relocation Score",
            "Distance Score",
            "History Score",
            "Density Score",
            "Dispatch Note",
            "Recommendation",
            "Reason",
        ]
        st.dataframe(
            display[columns],
            use_container_width=True,
            hide_index=True,
        )
        if mapbox_ready():
            routing_provider = "Mapbox traffic-aware matrix"
        elif google_maps_ready():
            routing_provider = "Google Maps traffic-aware routing"
        else:
            routing_provider = "estimated/free fallback distance"
        st.caption(
            "Selects three options using distance first, historical F&C load frequency second, and manufacturing/industrial density third. "
            "Traffic and weather are checked only for the final three options so ranking stays fast. "
            f"Current distance provider: {routing_provider}."
        )
        return

    data = pd.DataFrame(
        [
            {"Current Market": "Jackson, MS", "Target Market": "Memphis, TN", "Distance": 209, "Recommendation": "Approved"},
            {"Current Market": "El Paso, TX", "Target Market": "Dallas, TX", "Distance": 635, "Recommendation": "Outside limit"},
            {"Current Market": "Mobile, AL", "Target Market": "Atlanta, GA", "Distance": 328, "Recommendation": "Review"},
        ]
    )
    st.dataframe(data, use_container_width=True, hide_index=True)


def _driver_start_market_selector(market_options: list[str]) -> tuple[str, str, str]:
    start_source = st.radio(
        "Reposition from",
        ["Current GPS/manual location", "Future delivery location"],
        horizontal=True,
    )

    if start_source == "Future delivery location":
        selected_van = _van_selector()
        future_market = st.selectbox("Future delivery market", market_options)
        custom_future_market = st.text_input("Or type future city/state", placeholder="Example: Columbus, OH")
        return selected_van, custom_future_market.strip() or future_market, "Future delivery location"

    if momentum_ready():
        assets = momentum_driver_location_options()
        if isinstance(assets, pd.DataFrame) and not assets.empty:
            asset_labels = [
                _asset_label(row)
                for _, row in assets.iterrows()
            ]
            selected_asset = st.selectbox("Van number / Momentum unit", asset_labels)
            asset_row = assets.iloc[asset_labels.index(selected_asset)]
            location_text = _asset_market(asset_row)
            if location_text:
                st.caption(f"Momentum location: {location_text}")
                manual_override = st.checkbox("Override Momentum location", value=False)
                if not manual_override:
                    return selected_asset, location_text, "Momentum GPS"

    manual_van = _van_selector()
    manual_market = st.selectbox("Driver current market", market_options)
    custom_market = st.text_input("Or type current city/state", placeholder="Example: Lima, OH")
    return manual_van, custom_market.strip() or manual_market, "Manual current location"


def _render_knowledge_file_status() -> None:
    knowledge_files = st.session_state.get("knowledge_files", [])
    if knowledge_files:
        st.caption(f"Knowledge files available for relocation context: {len(knowledge_files)}")


def _van_selector() -> str:
    return st.text_input("Van number", placeholder="Example: Van 36")


def _asset_label(row: pd.Series) -> str:
    unit = row.get("unit") or row.get("name") or row.get("asset_id")
    driver = row.get("driver")
    status = row.get("status")
    parts = [str(unit)]
    if driver:
        parts.append(str(driver))
    if status:
        parts.append(str(status))
    return " - ".join(parts)


def _asset_market(row: pd.Series) -> str:
    city = str(row.get("city") or "").strip()
    state = str(row.get("state") or "").strip()
    if city and state:
        return f"{city.title()}, {state.upper()}"
    return ""


def _relocation_candidate_summary(loads: pd.DataFrame) -> pd.DataFrame:
    outbound = origin_market_summary(loads)
    if outbound.empty or "destination_market" not in loads.columns:
        return outbound

    destination_markets = (
        loads["destination_market"]
        .dropna()
        .astype(str)
        .str.strip()
    )
    destination_markets = destination_markets[destination_markets != ""].drop_duplicates()
    existing = set(outbound["origin_market"].astype(str))
    additions = [
        {
            "origin_market": market,
            "loads": 0,
            "average_pay": 0.0,
            "total_pay": 0.0,
            "average_loaded_miles": 0.0,
            "average_empty_miles": 0.0,
            "priority": "Density candidate",
        }
        for market in destination_markets
        if market not in existing
    ]
    if not additions:
        return outbound
    return pd.concat([outbound, pd.DataFrame(additions)], ignore_index=True, sort=False)


def _format_distance(distance: object) -> str:
    if pd.isna(distance):
        return "Unavailable"
    return f"{float(distance):.0f} mi"

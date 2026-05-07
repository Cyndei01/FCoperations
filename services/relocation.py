from __future__ import annotations

import pandas as pd
import requests

from services.google_maps import google_maps_ready, route_metrics
from services.live_sources import weather_for_market
from services.manufacturing_locations import add_manufacturing_location_density
from services.mapbox import mapbox_ready, route_metrics as mapbox_route_metrics
from services.market_distance import estimated_distance_detail


RELOCATION_MODEL_VERSION = "fast-no-network-ranking-v14"


def build_relocation_recommendations(
    current_market: str,
    origin_summary: pd.DataFrame,
    heat_map: pd.DataFrame | None,
    relocation_limit: int | None,
    target_count: int,
    use_live_distance: bool,
    knowledge_locations: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if origin_summary.empty:
        return pd.DataFrame()

    targets = origin_summary.copy()
    targets["ppm"] = targets.apply(_pay_per_mile, axis=1)
    targets = _merge_heat_map_signals(targets, heat_map)
    targets = targets[targets["origin_market"].apply(lambda market: _normalize_market(market) != _normalize_market(current_market))]
    targets = targets.sort_values(
        ["loads", "industrial_points", "automotive_points", "heat_score", "average_pay"],
        ascending=[False, False, False, False, False],
        na_position="last",
    )
    targets = targets.head(min(max(target_count * 20, 150), 250)).copy()
    targets = add_manufacturing_location_density(targets, knowledge_locations)

    targets = _add_estimated_distance_metrics(current_market, targets)

    targets["movement_direction"] = "Data-ranked"
    targets["within_limit"] = targets["distance_miles"].apply(
        lambda distance: _within_limit(distance, relocation_limit)
    )
    targets = _add_relocation_scores(targets, relocation_limit)
    targets["recommendation"] = targets.apply(
        lambda row: _recommendation(row, current_market, relocation_limit),
        axis=1,
    )
    targets["reason"] = targets.apply(_reason, axis=1)

    selected = _select_three_options(targets, target_count)
    return _add_live_advisories(current_market, selected, use_live_distance)


def _pay_per_mile(row: pd.Series) -> float:
    loaded_miles = float(row.get("average_loaded_miles") or 0)
    if loaded_miles <= 0:
        return 0.0
    return round(float(row.get("average_pay") or 0) / loaded_miles, 2)


def _merge_heat_map_signals(targets: pd.DataFrame, heat_map: pd.DataFrame | None) -> pd.DataFrame:
    enriched = targets.copy()
    if isinstance(heat_map, pd.DataFrame) and not heat_map.empty and "market" in heat_map.columns:
        heat_columns = [
            column
            for column in [
                "market",
                "industrial_points",
                "automotive_points",
                "repeat_facilities",
                "opportunity_score",
                "confidence",
            ]
            if column in heat_map.columns
        ]
        signals = heat_map[heat_columns].rename(
            columns={
                "market": "origin_market",
                "opportunity_score": "heat_score",
            }
        )
        drop_columns = [column for column in signals.columns if column in enriched.columns and column != "origin_market"]
        enriched = enriched.drop(columns=drop_columns, errors="ignore").merge(signals, on="origin_market", how="left")

    for column in ["industrial_points", "automotive_points", "repeat_facilities", "heat_score"]:
        if column not in enriched.columns:
            enriched[column] = 0
        enriched[column] = pd.to_numeric(enriched[column], errors="coerce").fillna(0)
    if "confidence" not in enriched.columns:
        enriched["confidence"] = "History"
    enriched["confidence"] = enriched["confidence"].fillna("History")
    return enriched


def _add_estimated_distance_metrics(current_market: str, targets: pd.DataFrame) -> pd.DataFrame:
    enriched = targets.copy()
    destination_markets = enriched["origin_market"].tolist()
    distances = []
    distance_sources = []
    for market in destination_markets:
        distance, source = estimated_distance_detail(current_market, market, allow_geocode=False)
        distances.append(distance)
        distance_sources.append(source)

    enriched["distance_miles"] = distances
    enriched["drive_minutes"] = None
    enriched["distance_source"] = distance_sources
    enriched["traffic_condition"] = ""
    return enriched


def _add_live_advisories(current_market: str, selected: pd.DataFrame, use_live_distance: bool) -> pd.DataFrame:
    enriched = selected.copy()
    destination_markets = enriched["origin_market"].tolist()
    if not use_live_distance:
        enriched["weather_risk"] = "Not checked"
        enriched["weather_summary"] = "Skipped for fast ranking"
        enriched["weather_details"] = ""
        enriched["dispatch_note"] = "Fast ranking: review live conditions before dispatch"
        return _dispatch_order(enriched)

    live_metrics: dict[str, dict] = {}
    live_metrics = _live_route_metrics(current_market, destination_markets)

    weather_rows = {market: _weather_advisory(market) for market in destination_markets}

    for index, row in enriched.iterrows():
        market = row["origin_market"]
        route = live_metrics.get(market)
        if route:
            enriched.at[index, "distance_miles"] = route["distance_miles"]
            enriched.at[index, "drive_minutes"] = route.get("drive_minutes")
            enriched.at[index, "distance_source"] = route["distance_source"]
            enriched.at[index, "traffic_condition"] = route.get("traffic_condition", "")
        weather = weather_rows.get(market, {})
        enriched.at[index, "weather_risk"] = weather.get("risk", "Unknown")
        enriched.at[index, "weather_summary"] = weather.get("summary", "Unavailable")
        enriched.at[index, "weather_details"] = weather.get("details", "")
        enriched.at[index, "dispatch_note"] = _dispatch_note(enriched.loc[index])

    return _dispatch_order(enriched)


def _live_route_metrics(current_market: str, destination_markets: list[str]) -> dict[str, dict]:
    try:
        mapbox_metrics = mapbox_route_metrics(current_market, destination_markets) if mapbox_ready() else {}
    except requests.RequestException:
        mapbox_metrics = {}
    if mapbox_metrics:
        return mapbox_metrics

    try:
        return route_metrics(current_market, destination_markets) if google_maps_ready() else {}
    except requests.RequestException:
        return {}


def _weather_advisory(market: str) -> dict[str, str]:
    try:
        weather = weather_for_market(market)
    except Exception as error:
        return {
            "risk": "Unknown",
            "summary": "Unavailable",
            "details": f"Weather unavailable: {error}",
        }
    return {
        "risk": str(weather.get("Risk", "Unknown")),
        "summary": str(weather.get("Forecast", "Unavailable")),
        "details": str(weather.get("Details", "")),
    }


def _dispatch_note(row: pd.Series) -> str:
    notes = []
    if row.get("traffic_condition"):
        notes.append(str(row.get("traffic_condition")))
    weather_risk = row.get("weather_risk")
    if weather_risk == "High":
        notes.append("Review weather before dispatch")
    elif weather_risk == "Medium":
        notes.append("Monitor weather")
    return "; ".join(notes) if notes else "Clear advisory"


def _add_relocation_scores(targets: pd.DataFrame, relocation_limit: int | None) -> pd.DataFrame:
    scored = targets.copy()
    max_loads = max(float(scored["loads"].max() or 0), 1.0)
    max_industrial = max(float(scored["industrial_points"].max() or 0), 1.0)
    max_automotive = max(float(scored["automotive_points"].max() or 0), 1.0)
    max_repeat = max(float(scored["repeat_facilities"].max() or 0), 1.0)
    known_distances = pd.to_numeric(scored["distance_miles"], errors="coerce").dropna()
    max_distance = max(float(known_distances.max()) if not known_distances.empty else 0, 1.0)

    scored["distance_score"] = scored["distance_miles"].apply(
        lambda distance: _distance_score(distance, max_distance, relocation_limit)
    )
    scored["history_score"] = scored["loads"].apply(lambda loads: min(float(loads or 0) / max_loads * 25, 25))
    industrial_score = scored["industrial_points"].apply(
        lambda points: min(float(points or 0) / max_industrial * 10, 10)
    )
    automotive_score = scored["automotive_points"].apply(
        lambda points: min(float(points or 0) / max_automotive * 4, 4)
    )
    repeat_score = scored["repeat_facilities"].apply(
        lambda repeats: min(float(repeats or 0) / max_repeat * 1, 1)
    )
    scored["density_score"] = industrial_score + automotive_score + repeat_score
    scored["relocation_score"] = (
        scored["distance_score"] + scored["history_score"] + scored["density_score"]
    ).round(1)
    return scored


def _distance_score(distance: object, max_distance: float, relocation_limit: int | None) -> float:
    if pd.isna(distance):
        return -30
    distance_value = float(distance)
    score = max(60 - distance_value / 20, 0)
    if relocation_limit and distance_value > relocation_limit:
        score -= 25
    return round(score, 1)


def _recommendation(row: pd.Series, current_market: str, relocation_limit: int | None) -> str:
    if _normalize_market(str(row["origin_market"])) == _normalize_market(current_market):
        return "Stay / search local"
    distance = row.get("distance_miles")
    if pd.isna(distance):
        return "Distance unavailable"
    if relocation_limit is None:
        return "Reposition candidate"
    if float(distance) <= relocation_limit:
        return "Reposition candidate"
    return "Outside relocation limit"


def _reason(row: pd.Series) -> str:
    pieces = [
        f"{int(row.get('loads') or 0)} historical outbound loads",
        f"{int(row.get('industrial_points') or 0)} industrial/warehouse points",
        f"{int(row.get('automotive_points') or 0)} automotive/manufacturing points",
        f"${float(row.get('ppm') or 0):.2f}/mi",
    ]
    distance = row.get("distance_miles")
    if pd.notna(distance):
        pieces.append(f"{float(distance):.0f} mi away")
        source = row.get("distance_source")
        if source:
            pieces.append(str(source))
    else:
        pieces.append("distance unavailable")
    drive_minutes = row.get("drive_minutes")
    if pd.notna(drive_minutes):
        pieces.append(f"{float(drive_minutes):.0f} min drive")
    return "; ".join(pieces)


def _select_three_options(targets: pd.DataFrame, target_count: int) -> pd.DataFrame:
    viable = targets.copy()
    if "distance_miles" in viable.columns:
        with_distance = viable[viable["distance_miles"].notna()].copy()
        if not with_distance.empty:
            viable = with_distance
            within_limit = viable[viable["within_limit"] == True].copy()
            if not within_limit.empty:
                viable = within_limit

    viable = viable.sort_values(
        ["relocation_score", "loads", "industrial_points", "automotive_points", "distance_miles"],
        ascending=[False, False, False, False, True],
        na_position="last",
    )
    selected_rows = []
    used_states: set[str] = set()
    for index, row in viable.iterrows():
        state = _state_code(str(row.get("origin_market", "")))
        if state in used_states:
            continue
        selected_rows.append(index)
        if state:
            used_states.add(state)
        if len(selected_rows) == 3:
            break

    if len(selected_rows) < 3:
        for index, _row in viable.iterrows():
            if index in selected_rows:
                continue
            selected_rows.append(index)
            if len(selected_rows) == 3:
                break

    selected = _dispatch_order(viable.loc[selected_rows]) if selected_rows else viable.head(0)
    if len(selected) >= 3:
        return selected

    fallback = targets[~targets.index.isin(selected.index)].sort_values(
        ["relocation_score", "loads", "industrial_points"],
        ascending=[False, False, False],
    )
    return pd.concat([selected, fallback]).head(min(3, target_count))


def _within_limit(distance: object, relocation_limit: int | None) -> bool | None:
    if relocation_limit is None:
        return True
    if pd.isna(distance):
        return None
    return float(distance) <= relocation_limit


def _normalize_market(market: str) -> str:
    if "," not in market:
        return market.strip().title()
    city, state = market.rsplit(",", 1)
    return f"{city.strip().title()}, {state.strip().upper()}"


def _state_code(market: str) -> str:
    if "," not in market:
        return ""
    return market.rsplit(",", 1)[1].strip().upper()


def _dispatch_order(selected: pd.DataFrame) -> pd.DataFrame:
    ordered = selected.copy()
    ordered = ordered.sort_values(
        ["distance_miles", "relocation_score"],
        ascending=[True, False],
        na_position="last",
    )
    return ordered

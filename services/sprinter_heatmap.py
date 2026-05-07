from __future__ import annotations

import re
import time
from typing import Any

import pandas as pd
import requests
import streamlit as st

from app_config import LIVE_DATA
from services.live_sources import geocode_market
from services.load_parser import origin_market_summary
from services.manufacturing_locations import add_manufacturing_location_density


AUTOMOTIVE_KEYWORDS = re.compile(
    r"auto|automotive|vehicle|motor|parts|tire|tyre|wheel|transmission|"
    r"engine|battery|logistics|distribution|warehouse|manufactur|industrial",
    re.IGNORECASE,
)


def build_sprinter_heat_map(
    loads: pd.DataFrame,
    market_limit: int,
    radius_miles: int,
    include_industrial_density: bool,
    industrial_market_limit: int,
    knowledge_locations: pd.DataFrame | None = None,
    progress_callback=None,
) -> pd.DataFrame:
    if loads.empty:
        return pd.DataFrame()

    summary = _candidate_market_summary(loads, knowledge_locations, market_limit)
    max_loads = max(float(summary["loads"].max()), 1.0)
    max_pay = max(float(summary["average_pay"].max()), 1.0)
    max_knowledge_points = max(float(summary.get("knowledge_manufacturing_points", pd.Series([0])).max() or 0), 1.0)

    rows: list[dict[str, Any]] = []
    for position, (_, market_row) in enumerate(summary.iterrows(), start=1):
        market = market_row["origin_market"]
        if progress_callback:
            progress_callback(position, len(summary), market)

        location = _safe_geocode(market)
        if include_industrial_density and location and position <= industrial_market_limit:
            density = industrial_density_for_market(market, radius_miles)
        else:
            density = _empty_density(market)
        knowledge_points = int(market_row.get("knowledge_manufacturing_points") or 0)
        density["industrial_points"] += knowledge_points
        density["automotive_points"] += knowledge_points
        repeat_facilities = _repeat_facility_count(loads, market)

        history_score = float(market_row["loads"]) / max_loads * 45
        pay_score = float(market_row["average_pay"]) / max_pay * 15
        density_score = min(density["industrial_points"], 80) / 80 * 20
        automotive_score = min(density["automotive_points"], 25) / 25 * 8
        knowledge_score = min(knowledge_points / max_knowledge_points * 17, 17)
        repeat_facility_score = min(repeat_facilities, 10) / 10 * 5
        opportunity_score = history_score + pay_score + density_score + automotive_score + knowledge_score + repeat_facility_score

        rows.append(
            {
                "market": market,
                "lat": location["lat"] if location else None,
                "lon": location["lon"] if location else None,
                "historical_loads": int(market_row["loads"]),
                "average_pay": float(market_row["average_pay"]),
                "average_loaded_miles": float(market_row["average_loaded_miles"]),
                "pay_per_mile": _pay_per_mile(market_row),
                "average_empty_miles": float(market_row["average_empty_miles"]),
                "repeat_facilities": repeat_facilities,
                "knowledge_manufacturing_points": knowledge_points,
                "industrial_points": density["industrial_points"],
                "automotive_points": density["automotive_points"],
                "opportunity_score": round(opportunity_score, 1),
                "market_temperature": _market_temperature(opportunity_score),
                "confidence": _confidence_label(location, density),
                "density_source": _density_source_label(include_industrial_density, position, industrial_market_limit, density, knowledge_points),
                "map_size": max(round(opportunity_score * 350), 800),
            }
        )
        time.sleep(0.05)

    heat_map = pd.DataFrame(rows)
    if heat_map.empty:
        return heat_map

    return heat_map.sort_values("opportunity_score", ascending=False).head(market_limit)


def _candidate_market_summary(loads: pd.DataFrame, knowledge_locations: pd.DataFrame | None, market_limit: int) -> pd.DataFrame:
    summary = origin_market_summary(loads)
    summary = add_manufacturing_location_density(summary, knowledge_locations)
    if not isinstance(knowledge_locations, pd.DataFrame) or knowledge_locations.empty:
        return summary.head(market_limit).copy()

    existing = set(summary["origin_market"].astype(str))
    knowledge_counts = (
        knowledge_locations["market"]
        .dropna()
        .astype(str)
        .str.strip()
        .value_counts()
    )
    additions = [
        {
            "origin_market": market,
            "loads": 0,
            "average_pay": 0.0,
            "total_pay": 0.0,
            "average_loaded_miles": 0.0,
            "average_empty_miles": 0.0,
            "priority": "Knowledge market",
            "knowledge_manufacturing_points": int(count),
            "industrial_points": int(count),
            "automotive_points": int(count),
        }
        for market, count in knowledge_counts.items()
        if market not in existing
    ]
    if additions:
        summary = pd.concat([summary, pd.DataFrame(additions)], ignore_index=True, sort=False)

    for column in ["knowledge_manufacturing_points", "industrial_points", "automotive_points"]:
        if column not in summary.columns:
            summary[column] = 0
        summary[column] = pd.to_numeric(summary[column], errors="coerce").fillna(0)

    summary["candidate_score"] = (
        summary["loads"].rank(method="dense", ascending=False)
        + summary["knowledge_manufacturing_points"].rank(method="dense", ascending=False)
    )
    historical = summary.sort_values(["loads", "knowledge_manufacturing_points"], ascending=False).head(market_limit)
    knowledge = summary.sort_values(["knowledge_manufacturing_points", "loads"], ascending=False).head(market_limit)
    return pd.concat([historical, knowledge]).drop_duplicates(subset=["origin_market"]).copy()


@st.cache_data(ttl=60 * 60 * 24 * 7, show_spinner=False)
def industrial_density_for_market(market: str, radius_miles: int) -> dict[str, Any]:
    location = _safe_geocode(market)
    if not location:
        return _empty_density(market)

    radius_meters = int(radius_miles * 1609.344)
    query = f"""
    [out:json][timeout:12];
    (
      nwr(around:{radius_meters},{location["lat"]},{location["lon"]})["name"~"auto|automotive|parts|warehouse|distribution|logistics|manufactur",i];
      nwr(around:{radius_meters},{location["lat"]},{location["lon"]})["building"~"warehouse|industrial|factory|manufacture"];
    );
    out center tags 100;
    """

    try:
        response = requests.post(
            LIVE_DATA["overpass_url"],
            data={"data": query},
            timeout=15,
            headers={"User-Agent": LIVE_DATA["user_agent"]},
        )
        response.raise_for_status()
        elements = response.json().get("elements", [])
    except (requests.RequestException, ValueError):
        return _empty_density(market, source_available=False)

    automotive_points = 0
    for element in elements:
        tags = element.get("tags", {})
        tag_text = " ".join(str(value) for value in tags.values())
        if AUTOMOTIVE_KEYWORDS.search(tag_text):
            automotive_points += 1

    return {
        "market": market,
        "industrial_points": len(elements),
        "automotive_points": automotive_points,
        "source_available": True,
    }


def _safe_geocode(market: str) -> dict[str, Any] | None:
    try:
        return geocode_market(market)
    except requests.RequestException:
        return None


def _repeat_facility_count(loads: pd.DataFrame, market: str) -> int:
    market_loads = loads[loads["origin_market"] == market]
    if market_loads.empty or "origin_facility" not in market_loads.columns:
        return 0
    facility_counts = market_loads["origin_facility"].dropna().astype(str).str.strip().value_counts()
    return int((facility_counts >= 2).sum())


def _pay_per_mile(market_row: pd.Series) -> float:
    loaded_miles = float(market_row["average_loaded_miles"])
    if loaded_miles <= 0:
        return 0.0
    return round(float(market_row["average_pay"]) / loaded_miles, 2)


def _confidence_label(location: dict[str, Any] | None, density: dict[str, Any]) -> str:
    if location and density["source_available"]:
        return "High"
    if location:
        return "Medium"
    return "Low"


def _density_source_label(
    include_industrial_density: bool,
    position: int,
    industrial_market_limit: int,
    density: dict[str, Any],
    knowledge_points: int,
) -> str:
    sources = []
    if knowledge_points:
        sources.append("Knowledge files")
    if not include_industrial_density:
        return ", ".join(sources) if sources else "History only"
    if position > industrial_market_limit:
        sources.append("OSM skipped")
    elif not density["source_available"]:
        sources.append("OSM unavailable")
    else:
        sources.append("OpenStreetMap")
    return ", ".join(sources)


def _empty_density(market: str, source_available: bool = True) -> dict[str, Any]:
    return {
        "market": market,
        "industrial_points": 0,
        "automotive_points": 0,
        "source_available": source_available,
    }


def _market_temperature(score: float) -> str:
    if score >= 70:
        return "Hot"
    if score >= 45:
        return "Warm"
    if score >= 20:
        return "Watch"
    return "Cold"

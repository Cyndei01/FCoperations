from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

from services.market_distance import MARKET_COORDINATES


MAPBOX_GEOCODE_URL = "https://api.mapbox.com/search/geocode/v6/forward"
MAPBOX_MATRIX_URL = "https://api.mapbox.com/directions-matrix/v1/mapbox/driving-traffic"
REQUEST_TIMEOUT_SECONDS = 20


def mapbox_ready() -> bool:
    return bool(_access_token())


def route_metrics(origin_market: str, destination_markets: list[str]) -> dict[str, dict[str, Any]]:
    if not mapbox_ready() or not destination_markets:
        return {}

    markets = [origin_market] + destination_markets[:9]
    coordinates = []
    for market in markets:
        coordinate = _market_coordinate(market)
        if coordinate is None:
            return {}
        coordinates.append(coordinate)

    coordinate_path = ";".join(f"{lon},{lat}" for lat, lon in coordinates)
    response = requests.get(
        f"{MAPBOX_MATRIX_URL}/{coordinate_path}",
        params={
            "sources": "0",
            "destinations": ";".join(str(index) for index in range(1, len(coordinates))),
            "annotations": "duration,distance",
            "access_token": _access_token(),
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    distances = payload.get("distances", [[]])[0]
    durations = payload.get("durations", [[]])[0]

    metrics: dict[str, dict[str, Any]] = {}
    for index, market in enumerate(destination_markets[:9]):
        distance_meters = distances[index] if index < len(distances) else None
        duration_seconds = durations[index] if index < len(durations) else None
        if distance_meters is None:
            continue
        metrics[market] = {
            "distance_miles": round(float(distance_meters) / 1609.344, 1),
            "drive_minutes": round(float(duration_seconds) / 60, 1) if duration_seconds is not None else None,
            "distance_source": "Mapbox traffic",
            "traffic_condition": "Traffic-aware",
        }
    return metrics


def _market_coordinate(market: str) -> tuple[float, float] | None:
    known = MARKET_COORDINATES.get(_normalize_market(market))
    if known:
        return known

    response = requests.get(
        MAPBOX_GEOCODE_URL,
        params={
            "q": f"{market}, United States",
            "country": "us",
            "limit": 1,
            "autocomplete": "false",
            "access_token": _access_token(),
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    features = response.json().get("features", [])
    if not features:
        return None
    coordinates = features[0].get("geometry", {}).get("coordinates", [])
    if len(coordinates) < 2:
        return None
    lon, lat = coordinates[:2]
    return float(lat), float(lon)


def _normalize_market(market: str) -> str:
    if "," not in market:
        return market.strip().title()
    city, state = market.rsplit(",", 1)
    return f"{city.strip().title()}, {state.strip().upper()}"


def _access_token() -> str:
    value = os.getenv("MAPBOX_ACCESS_TOKEN")
    if value:
        return value
    try:
        return str(st.secrets.get("MAPBOX_ACCESS_TOKEN", ""))
    except Exception:
        return ""

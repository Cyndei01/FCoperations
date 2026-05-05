from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests


GOOGLE_ROUTES_MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
REQUEST_TIMEOUT_SECONDS = 20


def google_maps_ready() -> bool:
    return bool(_api_key())


def route_metrics(origin_market: str, destination_markets: list[str]) -> dict[str, dict[str, Any]]:
    if not google_maps_ready() or not destination_markets:
        return {}

    payload = {
        "origins": [{"waypoint": {"address": origin_market}}],
        "destinations": [{"waypoint": {"address": market}} for market in destination_markets],
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        "departureTime": datetime.now(timezone.utc).isoformat(),
    }
    response = requests.post(
        GOOGLE_ROUTES_MATRIX_URL,
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": _api_key(),
            "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,status,condition",
        },
    )
    response.raise_for_status()
    rows = response.json()
    metrics: dict[str, dict[str, Any]] = {}

    for row in rows:
        destination_index = row.get("destinationIndex")
        if destination_index is None or destination_index >= len(destination_markets):
            continue
        destination = destination_markets[destination_index]
        distance_meters = row.get("distanceMeters")
        duration_seconds = _duration_to_seconds(row.get("duration"))
        if distance_meters is None:
            continue
        metrics[destination] = {
            "distance_miles": round(float(distance_meters) / 1609.344, 1),
            "drive_minutes": round(duration_seconds / 60, 1) if duration_seconds is not None else None,
            "distance_source": "Google Maps",
            "traffic_condition": row.get("condition", ""),
        }
    return metrics


def _duration_to_seconds(duration: str | None) -> float | None:
    if not duration:
        return None
    if duration.endswith("s"):
        try:
            return float(duration[:-1])
        except ValueError:
            return None
    return None


def _api_key() -> str:
    return os.getenv("GOOGLE_MAPS_API_KEY", "")

from __future__ import annotations

import time
from typing import Any

import pandas as pd
import requests
import streamlit as st

from app_config import LIVE_DATA


REQUEST_TIMEOUT_SECONDS = 12


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def geocode_market(market: str) -> dict[str, Any] | None:
    params = {
        "q": f"{market}, USA",
        "format": "json",
        "limit": 1,
        "countrycodes": "us",
    }
    response = _get(LIVE_DATA["nominatim_url"], params=params)
    results = response.json()
    if not results:
        return None

    result = results[0]
    return {
        "market": market,
        "lat": float(result["lat"]),
        "lon": float(result["lon"]),
        "display_name": result.get("display_name", market),
    }


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def route_distance_miles(origin_market: str, destination_market: str) -> float | None:
    try:
        origin = geocode_market(origin_market)
        destination = geocode_market(destination_market)
    except requests.RequestException:
        return None

    if not origin or not destination:
        return None

    coordinate_path = f"{origin['lon']},{origin['lat']};{destination['lon']},{destination['lat']}"
    url = f"{LIVE_DATA['osrm_route_url']}/{coordinate_path}"
    try:
        response = _get(url, params={"overview": "false", "alternatives": "false", "steps": "false"})
    except requests.RequestException:
        return None

    routes = response.json().get("routes", [])
    if not routes:
        return None
    meters = routes[0].get("distance")
    if meters is None:
        return None
    return round(float(meters) / 1609.344, 1)


@st.cache_data(ttl=60 * 30, show_spinner=False)
def weather_for_market(market: str) -> dict[str, Any]:
    try:
        location = geocode_market(market)
    except requests.RequestException as error:
        return _weather_error(market, f"Live weather unavailable: {error}")

    if not location:
        return _weather_error(market, "Could not geocode market.")

    point = f"{location['lat']:.4f},{location['lon']:.4f}"
    alerts = _active_alerts_for_point(point)
    forecast = _forecast_for_point(point)
    risk = _weather_risk(alerts, forecast)

    return {
        "Market": market,
        "Risk": risk,
        "Active Alerts": len(alerts),
        "Forecast": forecast.get("shortForecast", "Unavailable"),
        "Temperature": forecast.get("temperature", "Unavailable"),
        "Wind": forecast.get("windSpeed", "Unavailable"),
        "Details": _weather_details(alerts, forecast),
        "Latitude": location["lat"],
        "Longitude": location["lon"],
    }


def weather_table_for_markets(markets: list[str]) -> pd.DataFrame:
    rows = []
    for market in markets:
        rows.append(weather_for_market(market))
        time.sleep(0.15)
    return pd.DataFrame(rows)


def add_route_distances(origin_market: str, targets: pd.DataFrame, limit: int) -> pd.DataFrame:
    enriched = targets.head(limit).copy()
    distances = []
    for target_market in enriched["origin_market"]:
        if target_market == origin_market:
            distances.append(0.0)
        else:
            distances.append(route_distance_miles(origin_market, target_market))
        time.sleep(0.15)

    enriched["live_distance_miles"] = distances
    return enriched


def _active_alerts_for_point(point: str) -> list[dict[str, Any]]:
    try:
        response = _get(f"{LIVE_DATA['nws_api_url']}/alerts/active", params={"point": point})
        return response.json().get("features", [])
    except requests.RequestException:
        return []


def _forecast_for_point(point: str) -> dict[str, Any]:
    try:
        point_response = _get(f"{LIVE_DATA['nws_api_url']}/points/{point}")
        forecast_url = point_response.json()["properties"]["forecast"]
        forecast_response = _get(forecast_url)
        periods = forecast_response.json().get("properties", {}).get("periods", [])
        return periods[0] if periods else {}
    except (KeyError, IndexError, requests.RequestException):
        return {}


def _weather_risk(alerts: list[dict[str, Any]], forecast: dict[str, Any]) -> str:
    if alerts:
        severe_events = {"Tornado Warning", "Severe Thunderstorm Warning", "Winter Storm Warning", "Ice Storm Warning"}
        alert_events = {alert.get("properties", {}).get("event", "") for alert in alerts}
        if alert_events.intersection(severe_events):
            return "High"
        return "Medium"

    forecast_text = " ".join(
        [
            str(forecast.get("shortForecast", "")),
            str(forecast.get("detailedForecast", "")),
            str(forecast.get("windSpeed", "")),
        ]
    ).lower()
    high_terms = ["snow", "ice", "thunderstorm", "heavy rain", "freezing", "blizzard"]
    medium_terms = ["rain", "fog", "wind", "showers"]
    if any(term in forecast_text for term in high_terms):
        return "High"
    if any(term in forecast_text for term in medium_terms):
        return "Medium"
    return "Low"


def _weather_details(alerts: list[dict[str, Any]], forecast: dict[str, Any]) -> str:
    if alerts:
        event = alerts[0].get("properties", {}).get("event")
        headline = alerts[0].get("properties", {}).get("headline")
        return headline or event or "Active weather alert"
    return forecast.get("detailedForecast", "No current forecast detail available.")


def _weather_error(market: str, reason: str) -> dict[str, Any]:
    return {
        "Market": market,
        "Risk": "Unknown",
        "Active Alerts": 0,
        "Forecast": "Unavailable",
        "Temperature": "Unavailable",
        "Wind": "Unavailable",
        "Details": reason,
        "Latitude": None,
        "Longitude": None,
    }


def _get(url: str, params: dict[str, Any] | None = None) -> requests.Response:
    response = requests.get(
        url,
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={
            "User-Agent": LIVE_DATA["user_agent"],
            "Accept": "application/geo+json, application/json",
        },
    )
    response.raise_for_status()
    return response

from __future__ import annotations

import re
from typing import Any

import pandas as pd
import requests
import streamlit as st

from app_config import ARCGIS_MARKET_DENSITY, LIVE_DATA
from services.live_sources import geocode_market


REQUEST_TIMEOUT_SECONDS = 6
LAYER_URL_PATTERN = re.compile(r"https?://[^\"'\s]+/(?:FeatureServer|MapServer)(?:/\d+)?", re.IGNORECASE)


def arcgis_density_enabled() -> bool:
    return bool(ARCGIS_MARKET_DENSITY.get("enabled"))


def add_arcgis_density(targets: pd.DataFrame, market_limit: int | None = None) -> pd.DataFrame:
    if targets.empty or not arcgis_density_enabled():
        return targets

    enriched = targets.copy()
    market_limit = market_limit or int(ARCGIS_MARKET_DENSITY.get("market_limit", 75))
    radius_miles = int(ARCGIS_MARKET_DENSITY.get("radius_miles", 50))
    markets = enriched["origin_market"].head(market_limit).astype(str).tolist()
    density_by_market = {
        market: arcgis_density_for_market(market, radius_miles)
        for market in markets
    }

    enriched["external_industrial_points"] = enriched["origin_market"].map(
        lambda market: density_by_market.get(str(market), {}).get("points", 0)
    )
    enriched["external_density_source"] = enriched["origin_market"].map(
        lambda market: density_by_market.get(str(market), {}).get("source", "Not checked")
    )
    enriched["external_industrial_points"] = pd.to_numeric(
        enriched["external_industrial_points"], errors="coerce"
    ).fillna(0)
    enriched["industrial_points"] = (
        _numeric_column(enriched, "industrial_points")
        + enriched["external_industrial_points"]
    )
    return enriched


def _numeric_column(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(0, index=df.index, dtype=float)
    return pd.to_numeric(df[column], errors="coerce").fillna(0)


@st.cache_data(ttl=60 * 60 * 24 * 7, show_spinner=False)
def arcgis_density_for_market(market: str, radius_miles: int) -> dict[str, Any]:
    layers = _dashboard_layer_urls()
    if not layers:
        return {"market": market, "points": 0, "source": "ArcGIS unavailable"}

    try:
        location = geocode_market(market)
    except requests.RequestException:
        location = None
    if not location:
        return {"market": market, "points": 0, "source": "ArcGIS geocode unavailable"}

    total = 0
    checked_layers = 0
    for layer_url in layers[: int(ARCGIS_MARKET_DENSITY.get("max_layers", 10))]:
        count = _layer_count_near_market(layer_url, location["lat"], location["lon"], radius_miles)
        if count is None:
            continue
        total += count
        checked_layers += 1

    source = "BGA ArcGIS dashboard" if checked_layers else "ArcGIS layers unavailable"
    return {"market": market, "points": total, "source": source, "layers_checked": checked_layers}


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def _dashboard_layer_urls() -> list[str]:
    item_id = str(ARCGIS_MARKET_DENSITY.get("dashboard_item_id", "")).strip()
    portal_url = str(ARCGIS_MARKET_DENSITY.get("portal_url", "")).rstrip("/")
    if not item_id or not portal_url:
        return []

    data_url = f"{portal_url}/sharing/rest/content/items/{item_id}/data"
    try:
        response = requests.get(
            data_url,
            params={"f": "json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": LIVE_DATA["user_agent"]},
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return []

    urls = sorted({_normalize_layer_url(url) for url in _extract_layer_urls(data)})
    return [url for url in urls if url]


def _extract_layer_urls(value: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() == "url" and isinstance(item, str):
                urls.extend(LAYER_URL_PATTERN.findall(item))
            else:
                urls.extend(_extract_layer_urls(item))
    elif isinstance(value, list):
        for item in value:
            urls.extend(_extract_layer_urls(item))
    elif isinstance(value, str):
        urls.extend(LAYER_URL_PATTERN.findall(value))
    return urls


def _normalize_layer_url(url: str) -> str:
    cleaned = url.rstrip("/")
    if re.search(r"/(?:FeatureServer|MapServer)$", cleaned, re.IGNORECASE):
        return f"{cleaned}/0"
    return cleaned


def _layer_count_near_market(layer_url: str, lat: float, lon: float, radius_miles: int) -> int | None:
    try:
        response = requests.get(
            f"{layer_url}/query",
            params={
                "f": "json",
                "where": "1=1",
                "returnCountOnly": "true",
                "geometry": f"{lon},{lat}",
                "geometryType": "esriGeometryPoint",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "distance": radius_miles,
                "units": "esriSRUnit_StatuteMile",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": LIVE_DATA["user_agent"]},
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return None
    if "count" not in payload:
        return None
    return int(payload.get("count") or 0)

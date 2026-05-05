from __future__ import annotations

import os
import base64
import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests
import streamlit as st

from app_config import MOMENTUM


REQUEST_TIMEOUT_SECONDS = 15


def momentum_config_status() -> dict[str, bool]:
    tenant_id = _tenant_id()
    return {
        "base_url": bool(_base_url()),
        "tenant_id": bool(tenant_id),
        "token_or_credentials": bool(_token() or ((_email() or _username()) and _password())),
    }


def momentum_ready() -> bool:
    status = momentum_config_status()
    return all(status.values())


@st.cache_data(ttl=60 * 5, show_spinner=False)
def fetch_momentum_assets() -> pd.DataFrame:
    if not momentum_ready():
        return pd.DataFrame()

    response = _request("GET", f"/v1/tenant/{_tenant_id()}/asset")
    payload = response.json()
    assets = _extract_collection(payload)
    rows = [_normalize_asset(asset) for asset in assets]
    return pd.DataFrame([row for row in rows if row])


def test_momentum_connection() -> tuple[bool, str]:
    try:
        assets = fetch_momentum_assets()
    except requests.RequestException as error:
        return False, f"Momentum request failed: {error}"
    except ValueError as error:
        return False, f"Momentum response was not valid JSON: {error}"

    if assets.empty:
        return True, "Connected, but no assets were returned or recognized."
    return True, f"Connected. Found {len(assets)} assets."


def momentum_driver_location_options() -> pd.DataFrame:
    assets = fetch_momentum_assets()
    if assets.empty:
        return assets
    return assets.sort_values(["unit", "name"], na_position="last")


def _request(method: str, path: str, **kwargs) -> requests.Response:
    token = _token() or _signin_token()
    headers = kwargs.pop("headers", {})
    headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
    )
    response = requests.request(
        method,
        f"{_base_url()}{path}",
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
        **kwargs,
    )
    response.raise_for_status()
    return response


@st.cache_data(ttl=60 * 30, show_spinner=False)
def _signin_token() -> str:
    response = requests.post(
        f"{_base_url()}/v1/signin",
        json={"emailAddress": _email() or _username(), "password": _password()},
        timeout=REQUEST_TIMEOUT_SECONDS,
        headers={"Accept": "*/*", "Content-Type": "application/json-patch+json"},
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, str):
        return payload
    token = _find_first(payload, ["token", "jwt", "accessToken", "access_token", "idToken"])
    if not token:
        raise requests.RequestException("Sign-in succeeded but no JWT token field was found.")
    return str(token)


def _normalize_asset(asset: dict[str, Any]) -> dict[str, Any]:
    unit = _find_first(asset, ["unit", "unitNumber", "vehicleNumber", "name", "displayName", "assetName"])
    lat = _find_first(asset, ["latitude", "lat"])
    lon = _find_first(asset, ["longitude", "lng", "lon"])
    coordinates = _find_first(asset, ["coordinates"])
    if isinstance(coordinates, list) and len(coordinates) >= 2:
        lat = lat or coordinates[0]
        lon = lon or coordinates[1]

    nested_location = _find_first(asset, ["location", "lastLocation", "position", "gps"])
    if isinstance(nested_location, dict):
        lat = lat or _find_first(nested_location, ["latitude", "lat"])
        lon = lon or _find_first(nested_location, ["longitude", "lng", "lon"])

    fleet_status = _find_first(asset, ["fleetStatus"])
    status = _find_first(asset, ["status", "operatingStatus", "ignitionStatus"])
    if isinstance(fleet_status, dict):
        status = _find_first(fleet_status, ["fleetStatusType", "status"]) or status

    last_seen = _find_first(
        asset,
        ["lastUpdatedDate", "lastUpdated", "lastReportDate", "lastEventDate", "updatedAt", "timestamp"],
    )
    return {
        "asset_id": _find_first(asset, ["id", "assetId"]),
        "unit": str(unit or ""),
        "name": str(_find_first(asset, ["name", "displayName", "assetName"]) or unit or ""),
        "driver": str(_find_first(asset, ["driverName", "employeeName", "assignedEmployeeName"]) or ""),
        "lat": _to_float(lat),
        "lon": _to_float(lon),
        "city": str(_find_first(asset, ["city", "lastCity"]) or ""),
        "state": str(_find_first(asset, ["state", "lastState"]) or ""),
        "status": str(status or ""),
        "last_seen": str(last_seen or ""),
        "loaded_at": datetime.now(timezone.utc).isoformat(),
    }


def _extract_collection(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ["data", "items", "results", "assets", "value"]:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return [payload]


def _find_first(data: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in data and data[key] not in [None, ""]:
            return data[key]
    lowered = {str(key).lower(): value for key, value in data.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value not in [None, ""]:
            return value
    return None


def _to_float(value: Any) -> float | None:
    if value in [None, ""]:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _base_url() -> str:
    return os.getenv(MOMENTUM["base_url_env"], "").rstrip("/")


def _tenant_id() -> str:
    configured_tenant = os.getenv(MOMENTUM["tenant_id_env"], "")
    if configured_tenant:
        return configured_tenant

    token = _token()
    if not token and ((_email() or _username()) and _password() and _base_url()):
        try:
            token = _signin_token()
        except requests.RequestException:
            return ""

    return _tenant_from_token(token)


def _token() -> str:
    return os.getenv(MOMENTUM["token_env"], "")


def _username() -> str:
    return os.getenv(MOMENTUM["username_env"], "")


def _email() -> str:
    return os.getenv(MOMENTUM["email_env"], "")


def _password() -> str:
    return os.getenv(MOMENTUM["password_env"], "")


def _tenant_from_token(token: str) -> str:
    if not token or token.count(".") < 2:
        return ""
    try:
        payload_part = token.split(".")[1]
        payload_part += "=" * (-len(payload_part) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_part))
    except (ValueError, json.JSONDecodeError):
        return ""
    return str(_find_first(claims, ["TenantId", "tenantId", "tenant_id"]) or "")

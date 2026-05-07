from __future__ import annotations

import re
from io import BytesIO
from typing import Any

import pandas as pd
import streamlit as st

from services.supabase import download_file, upload_file


MANUFACTURING_LOCATIONS_PATH = "knowledge-files/manufacturing-locations/latest.csv"
STATE_PATTERN = re.compile(r"\b([A-Z]{2})\b")


def parse_manufacturing_locations(file_name: str, content: bytes) -> pd.DataFrame:
    file_type = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if file_type == "csv":
        raw = pd.read_csv(BytesIO(content))
    elif file_type == "xlsx":
        raw = pd.read_excel(BytesIO(content))
    else:
        return pd.DataFrame()
    return _normalize_locations(raw)


def save_manufacturing_locations(locations: pd.DataFrame) -> tuple[bool, str]:
    if locations.empty:
        return False, "No manufacturing locations to save."
    csv_bytes = locations.to_csv(index=False).encode("utf-8")
    return upload_file(
        "latest.csv",
        csv_bytes,
        "knowledge-files/manufacturing-locations",
        MANUFACTURING_LOCATIONS_PATH,
    )


def load_manufacturing_locations(st_module=st) -> pd.DataFrame:
    session_locations = st_module.session_state.get("manufacturing_locations")
    if isinstance(session_locations, pd.DataFrame) and not session_locations.empty:
        return session_locations

    ok, payload = download_file(MANUFACTURING_LOCATIONS_PATH)
    if not ok:
        return pd.DataFrame()
    try:
        locations = pd.read_csv(BytesIO(payload))
    except Exception:
        return pd.DataFrame()
    if not locations.empty:
        st_module.session_state["manufacturing_locations"] = locations
    return locations


def add_manufacturing_location_density(targets: pd.DataFrame, locations: pd.DataFrame | None) -> pd.DataFrame:
    if targets.empty or not isinstance(locations, pd.DataFrame) or locations.empty:
        return targets

    enriched = targets.copy()
    market_counts = (
        locations["market"]
        .dropna()
        .astype(str)
        .str.strip()
        .value_counts()
        .to_dict()
    )
    enriched["knowledge_manufacturing_points"] = enriched["origin_market"].map(
        lambda market: int(market_counts.get(_normalize_market(str(market)), 0))
    )
    enriched["industrial_points"] = (
        pd.to_numeric(enriched.get("industrial_points", 0), errors="coerce").fillna(0)
        + enriched["knowledge_manufacturing_points"]
    )
    enriched["automotive_points"] = (
        pd.to_numeric(enriched.get("automotive_points", 0), errors="coerce").fillna(0)
        + enriched["knowledge_manufacturing_points"]
    )
    return enriched


def _normalize_locations(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()

    df = raw.dropna(how="all").copy()
    df.columns = [str(column).strip() for column in df.columns]
    city_column = _find_column(df, ["city", "town", "municipality"])
    state_column = _find_column(df, ["state", "st", "province"])
    location_column = _find_column(df, ["location", "address", "plant location", "city/state", "city state"])
    name_column = _find_column(df, ["company", "plant", "facility", "manufacturer", "name", "supplier"])

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        city = _clean(row.get(city_column, "")) if city_column else ""
        state = _state_code(row.get(state_column, "")) if state_column else ""
        if (not city or not state) and location_column:
            parsed_city, parsed_state = _parse_location_text(row.get(location_column, ""))
            city = city or parsed_city
            state = state or parsed_state
        if not city or not state:
            continue
        rows.append(
            {
                "facility": _clean(row.get(name_column, "")) if name_column else "",
                "city": city.title(),
                "state": state.upper(),
                "market": f"{city.title()}, {state.upper()}",
                "source": "Knowledge file",
            }
        )
    return pd.DataFrame(rows).drop_duplicates()


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    normalized = {str(column).strip().lower(): column for column in df.columns}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    for column in df.columns:
        column_text = str(column).strip().lower()
        if any(candidate in column_text for candidate in candidates):
            return column
    return None


def _parse_location_text(value: Any) -> tuple[str, str]:
    text = _clean(value)
    if not text:
        return "", ""
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if len(parts) >= 2:
        state = _state_code(parts[-1])
        city = parts[-2]
        if city and state:
            return city, state
    match = STATE_PATTERN.search(text.upper())
    if match:
        state = match.group(1)
        city = text[: match.start()].strip(" ,-")
        if city:
            return city, state
    return "", ""


def _state_code(value: Any) -> str:
    text = _clean(value).upper()
    if len(text) == 2 and text.isalpha():
        return text
    match = STATE_PATTERN.search(text)
    return match.group(1) if match else ""


def _clean(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_market(market: str) -> str:
    if "," not in market:
        return market.strip().title()
    city, state = market.rsplit(",", 1)
    return f"{city.strip().title()}, {state.strip().upper()}"

from __future__ import annotations

import re
from typing import Any

import pandas as pd


CITY_STATE_PATTERN = re.compile(r"^[A-Z .'-]+,\s*[A-Z]{2}$")


def parse_pay_sheet_loads(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    clean_df = df.fillna("")

    for index in range(len(clean_df) - 1):
        load_row = clean_df.iloc[index]
        city_row = clean_df.iloc[index + 1]

        origin = _clean_text(city_row.get("From", ""))
        destination = _clean_text(city_row.get("To", ""))
        pay = _parse_money(load_row.get("Pay", ""))

        if not (_looks_like_market(origin) and _looks_like_market(destination)):
            continue

        if pay <= 0:
            continue

        rows.append(
            {
                "driver": _clean_text(load_row.get("Vehicle", "")),
                "truck": _clean_text(city_row.get("Vehicle", "")),
                "order_number": _clean_text(load_row.get("Order #", "")),
                "trip_number": _clean_text(city_row.get("Order #", "")),
                "origin_market": _normalize_market(origin),
                "destination_market": _normalize_market(destination),
                "origin_facility": _clean_text(load_row.get("From", "")),
                "destination_facility": _clean_text(load_row.get("To", "")),
                "loaded_miles": _parse_miles(load_row.get("Loaded", "")),
                "empty_miles": _parse_miles(city_row.get("Loaded", "")),
                "trip_hours": _parse_hours(load_row.get("Trip Time", "")),
                "driving_hours": _parse_hours(city_row.get("Trip Time", "")),
                "pay": pay,
                "status": _clean_text(city_row.get("Pay", "")),
            }
        )

    return pd.DataFrame(rows)


def origin_market_summary(loads: pd.DataFrame) -> pd.DataFrame:
    if loads.empty:
        return pd.DataFrame()

    summary = (
        loads.groupby("origin_market", dropna=False)
        .agg(
            loads=("order_number", "count"),
            average_pay=("pay", "mean"),
            total_pay=("pay", "sum"),
            average_loaded_miles=("loaded_miles", "mean"),
            average_empty_miles=("empty_miles", "mean"),
        )
        .reset_index()
        .sort_values(["loads", "average_pay"], ascending=[False, False])
    )
    summary["priority"] = summary["loads"].apply(_priority_from_load_count)
    summary["average_pay"] = summary["average_pay"].round(2)
    summary["total_pay"] = summary["total_pay"].round(2)
    summary["average_loaded_miles"] = summary["average_loaded_miles"].round(1)
    summary["average_empty_miles"] = summary["average_empty_miles"].round(1)
    return summary


def lane_summary(loads: pd.DataFrame) -> pd.DataFrame:
    if loads.empty:
        return pd.DataFrame()

    summary = (
        loads.groupby(["origin_market", "destination_market"], dropna=False)
        .agg(
            loads=("order_number", "count"),
            average_pay=("pay", "mean"),
            total_pay=("pay", "sum"),
            average_loaded_miles=("loaded_miles", "mean"),
            average_empty_miles=("empty_miles", "mean"),
            average_driving_hours=("driving_hours", "mean"),
        )
        .reset_index()
    )
    summary["pay_per_loaded_mile"] = summary.apply(
        lambda row: row["average_pay"] / row["average_loaded_miles"] if row["average_loaded_miles"] else 0,
        axis=1,
    )
    summary["reliability"] = summary["loads"].apply(_lane_reliability)
    summary["lane_score"] = (
        summary["loads"] * 10
        + summary["average_pay"] / 100
        + summary["pay_per_loaded_mile"].clip(upper=8) * 3
        - summary["average_empty_miles"].fillna(0) / 25
    )
    summary = summary.sort_values(["loads", "lane_score", "average_pay"], ascending=[False, False, False])
    return _round_summary_numbers(summary)


def dead_zone_summary(loads: pd.DataFrame) -> pd.DataFrame:
    if loads.empty:
        return pd.DataFrame()

    inbound = loads.groupby("destination_market").size().rename("inbound_loads")
    outbound = loads.groupby("origin_market").size().rename("outbound_loads")
    summary = (
        pd.concat([inbound, outbound], axis=1)
        .fillna(0)
        .reset_index()
        .rename(columns={"index": "market"})
    )
    summary["inbound_loads"] = summary["inbound_loads"].astype(int)
    summary["outbound_loads"] = summary["outbound_loads"].astype(int)
    summary["outbound_ratio"] = summary.apply(
        lambda row: row["outbound_loads"] / row["inbound_loads"] if row["inbound_loads"] else 0,
        axis=1,
    )
    summary["risk"] = summary["outbound_ratio"].apply(_dead_zone_risk)
    summary["suggested_action"] = summary["risk"].map(
        {
            "High": "Pre-book reload or reposition quickly",
            "Medium": "Confirm outbound options before delivery",
            "Watch": "Monitor, but reload history exists",
        }
    )
    summary = summary[summary["inbound_loads"] >= 2]
    summary = summary.sort_values(["outbound_ratio", "inbound_loads"], ascending=[True, False])
    return _round_summary_numbers(summary)


def get_session_load_history(st_module) -> pd.DataFrame:
    loads = st_module.session_state.get("load_history")
    if isinstance(loads, pd.DataFrame):
        return loads
    return pd.DataFrame()


def _priority_from_load_count(load_count: int) -> str:
    if load_count >= 25:
        return "High"
    if load_count >= 10:
        return "Medium"
    return "Watch"


def _dead_zone_risk(outbound_ratio: float) -> str:
    if outbound_ratio < 0.35:
        return "High"
    if outbound_ratio < 0.75:
        return "Medium"
    return "Watch"


def _lane_reliability(load_count: int) -> str:
    if load_count >= 5:
        return "Repeat Lane"
    if load_count >= 2:
        return "Developing"
    return "One-Off"


def _round_summary_numbers(summary: pd.DataFrame) -> pd.DataFrame:
    rounded = summary.copy()
    for column in rounded.select_dtypes(include="number").columns:
        if column.endswith("loads") or column == "loads":
            continue
        rounded[column] = rounded[column].round(2)
    return rounded


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\xa0", " ").strip()


def _normalize_market(value: str) -> str:
    cleaned = _clean_text(value).upper()
    if "," not in cleaned:
        return cleaned.title()
    city, state = cleaned.rsplit(",", 1)
    return f"{city.strip().title()}, {state.strip().upper()}"


def _looks_like_market(value: str) -> bool:
    return bool(CITY_STATE_PATTERN.match(_clean_text(value).upper()))


def _parse_money(value: Any) -> float:
    text = _clean_text(value)
    if not text:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    numeric = re.sub(r"[^0-9.-]", "", text)
    if not numeric:
        return 0.0
    try:
        return float(numeric)
    except ValueError:
        return 0.0


def _parse_miles(value: Any) -> float:
    return _parse_number(value)


def _parse_hours(value: Any) -> float:
    return _parse_number(value)


def _parse_number(value: Any) -> float:
    text = _clean_text(value)
    if not text:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    numeric = re.sub(r"[^0-9.-]", "", text)
    if not numeric:
        return 0.0
    try:
        return float(numeric)
    except ValueError:
        return 0.0

from __future__ import annotations

import re
from io import BytesIO
from typing import Any

import pandas as pd


CITY_STATE_PATTERN = re.compile(r"^[A-Z .'-]+,\s*[A-Z]{2}$")


def parse_load_history_file(file_name: str, content: bytes) -> pd.DataFrame:
    file_type = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if file_type == "csv":
        tables = [pd.read_csv(BytesIO(content))]
    elif file_type == "xlsx":
        workbook = pd.ExcelFile(BytesIO(content))
        tables = [_read_excel_sheet(workbook, sheet_name) for sheet_name in workbook.sheet_names]
    else:
        return pd.DataFrame()

    parsed_tables = [parse_pay_sheet_loads(table) for table in tables if isinstance(table, pd.DataFrame)]
    parsed_tables = [table for table in parsed_tables if not table.empty]
    if not parsed_tables:
        return pd.DataFrame()

    loads = pd.concat(parsed_tables, ignore_index=True)
    return loads.drop_duplicates(
        subset=["order_number", "origin_market", "destination_market", "pay", "loaded_miles"],
        keep="first",
    ).reset_index(drop=True)


def _read_excel_sheet(workbook: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    raw = pd.read_excel(workbook, sheet_name=sheet_name, header=None)
    header_row_index = _find_header_row(raw)
    if header_row_index is None:
        return pd.read_excel(workbook, sheet_name=sheet_name)

    headers = raw.iloc[header_row_index].fillna("").astype(str).str.strip()
    table = raw.iloc[header_row_index + 1 :].copy()
    table.columns = headers
    return table.dropna(how="all")


def _find_header_row(df: pd.DataFrame) -> int | None:
    expected_headers = {
        "vehicle",
        "stops",
        "order #",
        "from",
        "to",
        "loaded",
        "trip time",
        "pay",
        "origin",
        "origin market",
        "outbound location",
        "pickup location",
        "destination",
        "delivery location",
        "loaded miles",
        "rate",
    }
    for index, row in df.head(25).iterrows():
        values = {str(value).strip().lower() for value in row.dropna()}
        if len(values.intersection(expected_headers)) >= 3:
            return int(index)
    return None


def parse_pay_sheet_loads(df: pd.DataFrame) -> pd.DataFrame:
    standard_loads = _parse_standard_load_table(df)
    if not standard_loads.empty:
        return standard_loads

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


def _parse_standard_load_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    clean_df = df.dropna(how="all").copy()
    clean_df.columns = [str(column).strip() for column in clean_df.columns]
    origin_column = _find_column(
        clean_df,
        [
            "origin_market",
            "origin",
            "pickup market",
            "pickup",
            "pickup city",
            "pickup location",
            "from market",
            "from",
            "outbound market",
            "outbound location",
        ],
    )
    destination_column = _find_column(
        clean_df,
        [
            "destination_market",
            "destination",
            "delivery market",
            "delivery",
            "delivery city",
            "delivery location",
            "to market",
            "to",
        ],
    )
    if not origin_column:
        return pd.DataFrame()

    origin_city_column = _find_column(clean_df, ["origin city", "pickup city", "from city", "city"])
    origin_state_column = _find_column(clean_df, ["origin state", "pickup state", "from state", "state"])
    destination_city_column = _find_column(clean_df, ["destination city", "delivery city", "to city"])
    destination_state_column = _find_column(clean_df, ["destination state", "delivery state", "to state"])
    pay_column = _find_column(clean_df, ["pay", "rate", "revenue", "gross", "amount"])
    loaded_miles_column = _find_column(clean_df, ["loaded_miles", "loaded miles", "loaded", "miles", "distance"])
    empty_miles_column = _find_column(clean_df, ["empty_miles", "empty miles", "deadhead"])
    order_column = _find_column(clean_df, ["order_number", "order #", "order", "load id", "load number"])
    driver_column = _find_column(clean_df, ["driver", "vehicle", "van", "truck", "unit"])
    origin_facility_column = _find_column(clean_df, ["origin facility", "pickup facility", "shipper", "from facility"])
    destination_facility_column = _find_column(clean_df, ["destination facility", "delivery facility", "receiver", "consignee", "to facility"])

    rows: list[dict[str, Any]] = []
    for row_index, row in clean_df.iterrows():
        origin = _market_from_row(row, origin_column, origin_city_column, origin_state_column)
        destination = _market_from_row(row, destination_column, destination_city_column, destination_state_column)
        if not _looks_like_market(origin):
            continue
        if not _looks_like_market(destination):
            destination = ""
        pay = _parse_money(row.get(pay_column, "")) if pay_column else 0.0
        loaded_miles = _parse_miles(row.get(loaded_miles_column, "")) if loaded_miles_column else 0.0
        rows.append(
            {
                "driver": _clean_text(row.get(driver_column, "")) if driver_column else "",
                "truck": _clean_text(row.get(driver_column, "")) if driver_column else "",
                "order_number": _clean_text(row.get(order_column, "")) if order_column else f"row-{row_index}",
                "trip_number": "",
                "origin_market": _normalize_market(origin),
                "destination_market": _normalize_market(destination) if destination else "",
                "origin_facility": _clean_text(row.get(origin_facility_column, "")) if origin_facility_column else "",
                "destination_facility": _clean_text(row.get(destination_facility_column, "")) if destination_facility_column else "",
                "loaded_miles": loaded_miles,
                "empty_miles": _parse_miles(row.get(empty_miles_column, "")) if empty_miles_column else 0.0,
                "trip_hours": 0.0,
                "driving_hours": 0.0,
                "pay": pay,
                "status": "Imported history",
            }
        )
    return pd.DataFrame(rows)


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


def _market_from_row(row: pd.Series, market_column: str | None, city_column: str | None, state_column: str | None) -> str:
    if market_column:
        value = _clean_text(row.get(market_column, ""))
        if _looks_like_market(value):
            return value
    city = _clean_text(row.get(city_column, "")) if city_column else ""
    state = _clean_text(row.get(state_column, "")) if state_column else ""
    if city and state:
        return f"{city}, {state}"
    if market_column:
        return _clean_text(row.get(market_column, ""))
    return ""


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
    try:
        from services.supabase import download_parsed_load_history

        saved_loads = download_parsed_load_history()
        if isinstance(saved_loads, pd.DataFrame) and not saved_loads.empty:
            st_module.session_state["load_history"] = saved_loads
            st_module.session_state["load_history_source"] = "Supabase saved load history"
            return saved_loads
    except Exception:
        return pd.DataFrame()
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

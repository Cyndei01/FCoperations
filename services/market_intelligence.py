from __future__ import annotations

import pandas as pd


TREND_ADJUSTMENTS = {
    "Strong Increase": 12,
    "Moderate Increase": 6,
    "Neutral": 0,
    "Moderate Decrease": -6,
    "Strong Decrease": -12,
}


def default_market_intelligence() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Market": "National",
                "Source": "OOIDA Monthly Market Update",
                "Trend": "Neutral",
                "Score Adjustment": 0,
                "Notes": "Update this after reviewing the latest monthly report.",
            },
            {
                "Market": "",
                "Source": "FreightWaves SONAR / Market Updates",
                "Trend": "Neutral",
                "Score Adjustment": 0,
                "Notes": "Add market-specific OTVI/OTRI/headhaul notes here.",
            },
        ]
    )


def normalize_market_intelligence(signals: pd.DataFrame) -> pd.DataFrame:
    if signals.empty:
        return default_market_intelligence()

    normalized = signals.copy()
    for column in ["Market", "Source", "Trend", "Notes"]:
        if column not in normalized.columns:
            normalized[column] = ""

    normalized["Trend"] = normalized["Trend"].replace("", "Neutral")
    normalized["Score Adjustment"] = normalized.apply(_score_adjustment, axis=1)
    return normalized


def apply_market_intelligence(heat_map: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
    if heat_map.empty:
        return heat_map

    normalized_signals = normalize_market_intelligence(signals)
    adjusted = heat_map.copy()
    adjusted["market_intel_adjustment"] = 0.0
    adjusted["market_intel_notes"] = ""

    national_adjustment = _national_adjustment(normalized_signals)
    adjusted["market_intel_adjustment"] += national_adjustment

    for _, signal in normalized_signals.iterrows():
        market = str(signal.get("Market", "")).strip()
        if not market or market.lower() == "national":
            continue

        mask = adjusted["market"].str.lower() == market.lower()
        if not mask.any():
            continue

        adjustment = float(signal.get("Score Adjustment", 0) or 0)
        note = str(signal.get("Notes", "")).strip()
        adjusted.loc[mask, "market_intel_adjustment"] += adjustment
        if note:
            adjusted.loc[mask, "market_intel_notes"] = note

    adjusted["base_opportunity_score"] = adjusted["opportunity_score"]
    adjusted["opportunity_score"] = (adjusted["opportunity_score"] + adjusted["market_intel_adjustment"]).round(1)
    adjusted["map_size"] = adjusted["opportunity_score"].clip(lower=1).mul(350).round().clip(lower=800)
    return adjusted.sort_values("opportunity_score", ascending=False)


def _national_adjustment(signals: pd.DataFrame) -> float:
    national = signals[signals["Market"].astype(str).str.strip().str.lower() == "national"]
    if national.empty:
        return 0.0
    return float(national["Score Adjustment"].sum())


def _score_adjustment(row: pd.Series) -> float:
    explicit = row.get("Score Adjustment")
    if pd.notna(explicit) and str(explicit).strip() != "":
        try:
            return float(explicit)
        except ValueError:
            pass
    return float(TREND_ADJUSTMENTS.get(row.get("Trend", "Neutral"), 0))

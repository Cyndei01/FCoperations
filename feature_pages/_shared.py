import pandas as pd
import streamlit as st

from app_config import OWNER_SETTINGS


def owner_setting_summary() -> None:
    split = OWNER_SETTINGS["revenue_split"]
    st.info(
        "Owner controls: "
        f"{split['company_percent']}/{split['driver_percent']} revenue split, "
        f"{OWNER_SETTINGS['relocation_distance_limit_miles']} mile relocation limit, "
        f"{OWNER_SETTINGS['weather_sensitivity']} weather sensitivity."
    )


def sample_lane_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Origin": "Atlanta, GA", "Destination": "Dallas, TX", "Rate": "$2,450", "Miles": 781, "Status": "Strong"},
            {"Origin": "Chicago, IL", "Destination": "Nashville, TN", "Rate": "$1,650", "Miles": 472, "Status": "Stable"},
            {"Origin": "Houston, TX", "Destination": "Phoenix, AZ", "Rate": "$2,300", "Miles": 1175, "Status": "Watch"},
            {"Origin": "Charlotte, NC", "Destination": "Columbus, OH", "Rate": "$1,425", "Miles": 430, "Status": "Strong"},
        ]
    )

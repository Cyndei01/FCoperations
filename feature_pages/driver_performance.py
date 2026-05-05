import pandas as pd
import streamlit as st

from app_config import OWNER_SETTINGS
from styles import page_header


def render() -> None:
    split = OWNER_SETTINGS["revenue_split"]
    page_header("Driver Performance", "Track driver revenue, lane quality, and operational consistency.")

    col1, col2 = st.columns(2)
    col1.metric("Company Split", f"{split['company_percent']}%")
    col2.metric("Driver Split", f"{split['driver_percent']}%")

    data = pd.DataFrame(
        [
            {"Driver": "Driver A", "Loads": 18, "Revenue": "$42,500", "On-Time": "96%"},
            {"Driver": "Driver B", "Loads": 15, "Revenue": "$35,900", "On-Time": "93%"},
            {"Driver": "Driver C", "Loads": 21, "Revenue": "$48,700", "On-Time": "98%"},
        ]
    )
    st.dataframe(data, use_container_width=True, hide_index=True)

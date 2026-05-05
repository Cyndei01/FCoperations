import pandas as pd
import streamlit as st

from styles import page_header


def render() -> None:
    page_header("Momentum GPS", "Placeholder for fleet positioning and Momentum GPS integration.")

    data = pd.DataFrame(
        [
            {"Unit": "Truck 104", "Location": "Atlanta, GA", "Status": "Available"},
            {"Unit": "Truck 117", "Location": "Dallas, TX", "Status": "Loaded"},
            {"Unit": "Truck 122", "Location": "Chicago, IL", "Status": "Available"},
        ]
    )
    st.dataframe(data, use_container_width=True, hide_index=True)

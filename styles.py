import streamlit as st

from app_config import BRAND_COLORS


def apply_global_styles() -> None:
    colors = BRAND_COLORS
    st.markdown(
        f"""
        <style>
        :root {{
            --fc-navy: {colors["navy"]};
            --fc-navy-light: {colors["navy_light"]};
            --fc-yellow: {colors["yellow"]};
            --fc-grey: {colors["grey"]};
            --fc-grey-dark: {colors["grey_dark"]};
            --fc-black: {colors["black"]};
            --fc-white: {colors["white"]};
        }}

        .stApp {{
            background: linear-gradient(180deg, #f7f9fc 0%, var(--fc-white) 220px);
            color: var(--fc-black);
        }}

        .block-container {{
            max-width: 1280px;
            padding-top: 1.25rem;
            padding-bottom: 3rem;
        }}

        [data-testid="stSidebar"] {{
            background: var(--fc-navy);
            border-right: 4px solid var(--fc-yellow);
        }}

        [data-testid="stSidebar"] * {{
            color: var(--fc-white);
        }}

        [data-testid="stSidebar"] [role="radiogroup"] label {{
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 6px;
            margin-bottom: 0.35rem;
            padding: 0.35rem 0.5rem;
        }}

        [data-testid="stSidebar"] [role="radiogroup"] label:hover {{
            background: rgba(243, 196, 0, 0.16);
            border-color: rgba(243, 196, 0, 0.55);
        }}

        [data-testid="stSidebar"] button {{
            border-radius: 6px;
        }}

        h1, h2, h3 {{
            color: var(--fc-navy);
            letter-spacing: 0;
        }}

        h1 {{
            font-size: 2rem;
        }}

        div[data-testid="stMetric"] {{
            background: var(--fc-white);
            border: 1px solid #d9dee5;
            border-top: 4px solid var(--fc-yellow);
            border-radius: 6px;
            padding: 0.75rem 1rem;
            box-shadow: 0 8px 18px rgba(11, 31, 58, 0.06);
        }}

        div[data-testid="stDataFrame"] {{
            border: 1px solid #d9dee5;
            border-radius: 6px;
            overflow: hidden;
        }}

        .fc-page-kicker {{
            color: var(--fc-yellow);
            font-size: 0.9rem;
            margin-bottom: 0.25rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-weight: 700;
        }}

        .fc-brand-block {{
            border-bottom: 1px solid rgba(255, 255, 255, 0.16);
            margin-bottom: 1rem;
            padding-bottom: 1rem;
        }}

        .fc-brand-mark {{
            align-items: center;
            display: flex;
            gap: 0.65rem;
            margin-bottom: 0.35rem;
        }}

        .fc-brand-logo {{
            align-items: center;
            background: var(--fc-yellow);
            border-radius: 4px;
            color: var(--fc-navy);
            display: flex;
            font-weight: 900;
            height: 2.1rem;
            justify-content: center;
            width: 2.1rem;
        }}

        .fc-brand-name {{
            color: var(--fc-white);
            font-size: 1.1rem;
            font-weight: 800;
            line-height: 1.1;
        }}

        .fc-brand-subtitle {{
            color: rgba(255, 255, 255, 0.72);
            font-size: 0.82rem;
        }}

        .fc-page-header {{
            background: var(--fc-navy);
            border-bottom: 5px solid var(--fc-yellow);
            border-radius: 6px;
            margin-bottom: 1.25rem;
            padding: 1.15rem 1.35rem 1.25rem;
        }}

        .fc-page-header h1 {{
            color: var(--fc-white);
            margin: 0.15rem 0 0.35rem;
        }}

        .fc-page-header p {{
            color: rgba(255, 255, 255, 0.78);
            font-size: 0.98rem;
            margin: 0;
        }}

        .fc-section {{
            border-top: 1px solid #e5e7eb;
            margin-top: 1.5rem;
            padding-top: 1rem;
        }}

        .stButton > button,
        .stDownloadButton > button,
        .stFormSubmitButton > button {{
            background: var(--fc-navy);
            border: 1px solid var(--fc-navy);
            border-radius: 6px;
            color: var(--fc-white);
            font-weight: 600;
        }}

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        .stFormSubmitButton > button:hover {{
            background: var(--fc-navy-light);
            border-color: var(--fc-navy-light);
            color: var(--fc-white);
        }}

        .stTabs [data-baseweb="tab-highlight"] {{
            background-color: var(--fc-yellow);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <section class="fc-page-header">
            <div class="fc-page-kicker">F&C Packaging</div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

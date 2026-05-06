import pandas as pd
import streamlit as st

from services.load_parser import origin_market_summary, parse_pay_sheet_loads
from services.supabase import supabase_ready, upload_file
from styles import page_header


def _read_tabular_upload(uploaded_file, file_type: str) -> tuple[str | None, pd.DataFrame]:
    if file_type == "csv":
        return None, pd.read_csv(uploaded_file)

    excel_file = pd.ExcelFile(uploaded_file)
    selected_sheet = st.selectbox("Workbook sheet", excel_file.sheet_names)
    raw_df = pd.read_excel(excel_file, sheet_name=selected_sheet, header=None)

    header_row_index = _find_header_row(raw_df)
    if header_row_index is None:
        return selected_sheet, raw_df.dropna(how="all")

    headers = raw_df.iloc[header_row_index].fillna("").astype(str).str.strip()
    df = raw_df.iloc[header_row_index + 1 :].copy()
    df.columns = headers
    return selected_sheet, df.dropna(how="all")


def _find_header_row(df: pd.DataFrame) -> int | None:
    expected_headers = {"vehicle", "stops", "order #", "from", "to", "loaded", "trip time", "pay"}
    for index, row in df.head(20).iterrows():
        values = {str(value).strip().lower() for value in row.dropna()}
        if len(values.intersection(expected_headers)) >= 4:
            return int(index)
    return None


def render() -> None:
    page_header("Upload Pay Sheets", "Import driver pay sheets for internal review and reporting.")
    render_upload_manager()


def render_upload_manager() -> None:
    uploaded_file = st.file_uploader("Upload PDF, CSV, or Excel pay sheet", type=["pdf", "csv", "xlsx"])
    if uploaded_file:
        file_type = uploaded_file.name.rsplit(".", 1)[-1].lower()
        file_content = uploaded_file.getvalue()
        st.success(f"Received {uploaded_file.name}.")
        st.write(f"File type: {file_type.upper()}")
        st.write(f"File size: {uploaded_file.size / 1024:.1f} KB")
        if supabase_ready():
            ok, message = upload_file(uploaded_file.name, file_content, "pay-sheets")
            if ok:
                st.caption(f"Saved to Supabase: {message}")
            else:
                st.warning(message)

        if file_type == "pdf":
            st.info("PDF upload is ready. Text extraction and payroll validation can be added as the next step.")
        else:
            try:
                sheet_name, df = _read_tabular_upload(uploaded_file, file_type)
                populated_rows = len(df)
                populated_columns = len(df.columns)

                col1, col2, col3 = st.columns(3)
                col1.metric("Rows Found", f"{populated_rows:,}")
                col2.metric("Columns Found", f"{populated_columns:,}")
                col3.metric("Sheet", sheet_name or "CSV")

                st.subheader("Upload Preview")
                st.dataframe(df.head(100), use_container_width=True, hide_index=True)

                loads = parse_pay_sheet_loads(df)
                st.session_state["load_history"] = loads
                st.session_state["load_history_source"] = uploaded_file.name

                st.subheader("Parsed Load History")
                if loads.empty:
                    st.warning("No structured load records were found yet. The raw upload preview is available above.")
                else:
                    summary = origin_market_summary(loads)
                    load_col1, load_col2, load_col3 = st.columns(3)
                    load_col1.metric("Loads Parsed", f"{len(loads):,}")
                    load_col2.metric("Origin Markets", f"{loads['origin_market'].nunique():,}")
                    load_col3.metric("Top Origin", summary.iloc[0]["origin_market"])

                    st.dataframe(loads.head(100), use_container_width=True, hide_index=True)
                    st.caption("This parsed load history now powers Hot Markets and Relocation Finder for this session.")
            except Exception as error:
                st.error("The file uploaded, but the app could not preview it yet.")
                st.exception(error)
    else:
        st.write("Upload a pay sheet to begin.")

    st.markdown('<div class="fc-section"></div>', unsafe_allow_html=True)
    st.subheader("Expected Workflow")
    st.write("Upload files, validate totals, review exceptions, then export payroll-ready summaries.")

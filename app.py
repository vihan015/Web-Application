"""Data Explorer: a generic dashboard for any tabular dataset. Run with: streamlit run app.py"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import streamlit as st

from src import ui, views
from src.filters import render_filters
from src.kpi_setup import render_kpi_setup
from src.kpis import kpi_cards
from src.loader import DataLoadError, excel_sheets, get_extension, load_dataframe
from src.preprocessing import (CATEGORY_MISSING_OPTIONS, NUMERIC_MISSING_OPTIONS, DataValidationError, preprocess)
from src.profiling import build_schema

DTA_DIR = Path(__file__).parent / "data"
SAMPLES = {"Retail orders": "retail_orders.csv", "Employees": "employees.csv"}

st.set_page_config(page_title="Data Explorer", layout="wide", initial_sidebar_state="expanded")
ui.inject_css()


@st.cache_data(show_spinner="Reading file", max_entries=8)
def cached_load(name, content, sheet):
    return load_dataframe(name, content, sheet)


@st.cache_data(show_spinner="Cleaning data", max_entries=8)
def cached_clean(df, remove_duplicates, numeric_missing, category_missing):
    return preprocess(df, remove_duplicates, numeric_missing, category_missing)


def sidebar_source():
    """Return (name, content, sheet) for the active dataset, or None."""
    ui.sidebar_brand()
    ui.sidebar_label("Data")
    upload = st.sidebar.file_uploader("Dataset", type=["csv", "xlsx", "json"], label_visibility="collapsed")
    st.sidebar.caption("Or try a sample")
    for label, filename in SAMPLES.items():
        if st.sidebar.button(label, key=f"sample_{filename}") and (DATA_DIR / filename).exists():
            st.session_state["sample"] = filename
    if upload is not None:
        st.session_state["sample"] = None
        name, content = upload.name, upload.getvalue()
    elif st.session_state.get("sample"):
        name = st.session_state["sample"]
        content = (DATA_DIR / name).read_bytes()
    else:
        return None
    sheet = None
    if get_extension(name) == "xlsx":
        sheets = excel_sheets(content)
        sheet = st.sidebar.selectbox("Sheet", sheets) if len(sheets) > 1 else sheets[0]
    return name, content, sheet


def main():
    source = sidebar_source()
    if source is None:
        ui.empty_state()
        return
    name, content, sheet = source

    try:
        raw = cached_load(name, content, sheet)
    except DataLoadError as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # noqa: BLE001 - surface any parser failure to the user
        st.error(f"Unexpected error while reading the file: {exc}")
        return

    sig = hashlib.md5(content + str(sheet).encode()).hexdigest()[:8]
    ui.sidebar_label("Setup")
    with st.sidebar.expander("Data cleaning"):
        dedupe = st.checkbox("Remove duplicate rows", value=True, key=f"dd_{sig}")
        num_missing = st.selectbox("Missing numeric values", NUMERIC_MISSING_OPTIONS, key=f"nm_{sig}")
        cat_missing = st.selectbox("Missing categorical values", CATEGORY_MISSING_OPTIONS, key=f"cm_{sig}")
    ui.header(name, len(raw), raw.shape[1])

    try:
        clean, log = cached_clean(raw, dedupe, num_missing, cat_missing)
    except DataValidationError as exc:
        st.error(str(exc))
        views.quality(raw, None, [], None)
        return
    except Exception as exc:  # noqa: BLE001
        st.error(f"Unexpected error while cleaning the data: {exc}")
        return

    ctx = hashlib.md5(json.dumps([sig, dedupe, num_missing, cat_missing]).encode()).hexdigest()[:8]
    schema = build_schema(clean)
    specs, date_col = render_kpi_setup(clean, schema, ctx)
    filtered = render_filters(clean, schema, date_col, ctx)
    if filtered.empty:
        st.warning("No records match the current filters. Widen or reset the filters in the sidebar.")
        return

    try:
        ui.cards(kpi_cards(specs, filtered, clean)) if specs else st.info("Select key columns in the sidebar to show KPIs.")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not compute the KPIs: {exc}")

    t_over, t_an, t_stat, t_q, t_data = st.tabs(["Overview", "Analysis", "Statistics", "Data quality", "Data"])
    with t_over:
        views.overview(filtered, schema, date_col, ctx)
    with t_an:
        views.analysis(filtered, schema, ctx)
    with t_stat:
        views.statistics(filtered, schema, ctx)
    with t_q:
        views.quality(raw, clean, log, schema)
    with t_data:
        views.data(filtered, name)


main()

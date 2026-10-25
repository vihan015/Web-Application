"""Tab renderers. Each function receives already-prepared data."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from . import charts, ui
from .profiling import Schema
from .stats import (AGGREGATIONS, GRANULARITY, RECORDS, aggregate_by, categorical_summary, group_summary,
                    measure_label, numeric_summary, suggest_granularity, time_series)
from .validation import column_profile, dataset_overview


def _measure_controls(container, measures: list[str], key: str, default: int = 0):
    """Measure + aggregation pickers. 'Records' needs no aggregation."""
    options = [RECORDS] + measures
    measure = container[0].selectbox("Measure", options, index=min(default, len(options) - 1), key=f"{key}_m")
    if measure == RECORDS:
        container[1].selectbox("Aggregation", ["Count"], disabled=True, key=f"{key}_a0")
        return measure, "Count"
    agg = container[1].selectbox("Aggregation", list(AGGREGATIONS), index=1, key=f"{key}_a")
    return measure, agg


def overview(df: pd.DataFrame, schema: Schema, date_col: str | None, ctx: str) -> None:
    with st.container(border=True):
        ui.section("Trend over time", "Aggregated by the selected period")
        if date_col and df[date_col].notna().any():
            c = st.columns([1, 1, 1, 1])
            measure, agg = _measure_controls(c[:2], schema.measures, f"tr_{ctx}")
            grans = list(GRANULARITY)
            default = grans.index(suggest_granularity(df[date_col].min(), df[date_col].max()))
            gran = c[2].selectbox("Period", grans, index=default, key=f"tr_g_{ctx}")
            ts = time_series(df, date_col, GRANULARITY[gran], measure, agg)
            ui.show_plot(charts.trend_chart(ts, measure_label(measure, agg)), f"trend_{ctx}")
        else:
            st.info("No date column was detected. Trend charts appear when the data has a date or time column.")

    groups = schema.group_options
    if not groups:
        st.info("No categorical columns were found, so category breakdowns are unavailable.")
        return
    for i, col in enumerate(st.columns(2)):
        with col, st.container(border=True):
            ui.section("Breakdown", "Top groups by the selected measure")
            a, b = st.columns(2)
            dim = a.selectbox("Group by", groups, index=min(i, len(groups) - 1), key=f"bd_dim{i}_{ctx}")
            top = b.selectbox("Show top", [5, 10, 15, 20], index=1, key=f"bd_top{i}_{ctx}")
            c = st.columns(2)
            measure, agg = _measure_controls(c, schema.measures, f"bd{i}_{ctx}", default=i)
            ui.show_plot(charts.bar_chart(aggregate_by(df, dim, measure, agg), measure_label(measure, agg), top), f"bar{i}_{ctx}")


def analysis(df: pd.DataFrame, schema: Schema, ctx: str) -> None:
    nums = schema.measures
    if not nums:
        st.info("No numeric measures were detected in this dataset.")
        return
    hover = next((c for c in schema.identifiers), None)
    left, right = st.columns(2)
    with left, st.container(border=True):
        ui.section("Relationship", "Each point is one record")
        if len(nums) >= 2:
            a, b, c = st.columns(3)
            x = a.selectbox("X axis", nums, index=0, key=f"sc_x_{ctx}")
            y = b.selectbox("Y axis", nums, index=1, key=f"sc_y_{ctx}")
            color = c.selectbox("Color by", ["None"] + schema.dims, key=f"sc_c_{ctx}")
            ui.show_plot(charts.scatter_chart(df, x, y, None if color == "None" else color, hover), f"sc_{ctx}")
            if len(df) > 5000:
                st.caption("Showing a random sample of 5,000 records.")
        else:
            st.info("At least two numeric columns are required.")
    with right, st.container(border=True):
        ui.section("Distribution", "Spread of values in a numeric column")
        a, b = st.columns([2, 1])
        col = a.selectbox("Column", nums, key=f"hi_c_{ctx}")
        bins = b.slider("Bins", 5, 100, 30, key=f"hi_b_{ctx}")
        ui.show_plot(charts.histogram_chart(df, col, bins), f"hi_{ctx}")
    if schema.dims:
        with st.container(border=True):
            ui.section("Comparison across groups", "Distribution of a measure within each category")
            a, b, _ = st.columns([1, 1, 2])
            value = a.selectbox("Measure", nums, key=f"bx_v_{ctx}")
            by = b.selectbox("Group by", schema.dims, key=f"bx_b_{ctx}")
            ui.show_plot(charts.box_chart(df, value, by), f"bx_{ctx}")
    with st.container(border=True):
        ui.section("Correlation", "Pearson correlation between numeric columns")
        if len(nums) >= 2:
            ui.show_plot(charts.correlation_chart(df, nums), f"corr_{ctx}")
        else:
            st.info("At least two numeric columns are required.")


def statistics(df: pd.DataFrame, schema: Schema, ctx: str) -> None:
    with st.container(border=True):
        ui.section("Numeric columns", "Computed on the filtered records")
        if schema.measures:
            ui.show_table(numeric_summary(df, schema.measures))
        else:
            st.caption("No numeric columns.")
    cats = schema.group_options
    if cats:
        with st.container(border=True):
            ui.section("Categorical columns")
            ui.show_table(categorical_summary(df, cats))
        if schema.measures:
            with st.container(border=True):
                ui.section("Summary by group")
                a, b, _ = st.columns([1, 1, 2])
                dim = a.selectbox("Group by", cats, key=f"gs_dim_{ctx}")
                agg = b.selectbox("Aggregation", ["Mean", "Sum", "Median", "Min", "Max"], key=f"gs_agg_{ctx}")
                ui.show_table(group_summary(df, dim, schema.measures, agg))


def quality(raw: pd.DataFrame, clean: pd.DataFrame | None, log: list[str], schema: Schema | None) -> None:
    ov = dataset_overview(raw)
    ui.section("Uploaded data")
    ui.cards([
        {"label": "Rows", "value": f"{ov['rows']:,}", "sub": "records"},
        {"label": "Columns", "value": f"{ov['columns']}", "sub": f"{ov['memory_mb']:.2f} MB in memory"},
        {"label": "Missing values", "value": f"{ov['missing_cells']:,}", "sub": f"{ov['missing_pct']:.2f}% of cells"},
        {"label": "Duplicate rows", "value": f"{ov['duplicates']:,}", "sub": "exact duplicates"},
    ])
    raw_profile = column_profile(raw)
    with st.container(border=True):
        ui.section("Column profile", "Blank and placeholder text such as N/A counts as missing")
        ui.show_table(raw_profile)
    if (raw_profile["Missing (%)"] > 0).any():
        with st.container(border=True):
            ui.section("Missing values by column")
            ui.show_plot(charts.missing_chart(raw_profile), "missing_raw")
    if clean is not None and schema is not None:
        with st.container(border=True):
            ui.section("Cleaning log", f"{len(raw):,} rows in, {len(clean):,} rows out")
            st.markdown("\n".join(f"- {line}" for line in log) or "No changes were required.")
        with st.container(border=True):
            ui.section("Cleaned columns and detected roles", "Roles drive the suggested KPIs, filters and charts")
            ui.show_table(column_profile(clean, schema.kinds))


def data(df: pd.DataFrame, name: str) -> None:
    c1, c2 = st.columns([4, 1])
    c1.caption(f"{len(df):,} records after filters")
    c2.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"),
                       file_name=f"filtered_{name.rsplit('.', 1)[0]}.csv", mime="text/csv")
    ui.show_table(df.head(2000), height=520)
    if len(df) > 2000:
        st.caption("Preview limited to the first 2,000 rows. The download contains all filtered records.")

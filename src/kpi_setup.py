"""Sidebar controls that let the user confirm or redefine the key columns and KPIs."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .kpis import AGG_OPTIONS, KPISpec, default_agg, suggest_kpis
from .profiling import Schema, pick_time_column


def render_kpi_setup(df: pd.DataFrame, schema: Schema, ctx: str) -> tuple[list[KPISpec], str | None]:
    suggested = suggest_kpis(df, schema)
    suggested_cols = [s.column for s in suggested if s.column]
    suggested_agg = {s.column: s.agg for s in suggested if s.column}
    candidates = [c for c, k in schema.kinds.items() if k not in ("constant", "text")]

    with st.sidebar.expander("Key metrics and time", expanded=False):
        st.caption("Suggested from the data. Pick the columns that matter to you and how to summarise each.")
        none = "(none)"
        default_time = pick_time_column(df, schema)
        options = [none] + schema.datetimes
        time_choice = st.selectbox("Time column", options, index=options.index(default_time) if default_time else 0,
                                   key=f"time_{ctx}") if schema.datetimes else none
        show_records = st.checkbox("Show record count", value=True, key=f"rec_{ctx}")
        chosen = st.multiselect("Key columns", candidates, default=suggested_cols, max_selections=8, key=f"keys_{ctx}")
        specs: list[KPISpec] = [KPISpec(None)] if show_records else []
        for col in chosen:
            kind = schema.kinds[col]
            opts = AGG_OPTIONS.get(kind, ["Distinct count"])
            default = suggested_agg.get(col) or default_agg(col, kind)
            agg = st.selectbox(col, opts, index=opts.index(default) if default in opts else 0, key=f"agg_{col}_{ctx}")
            specs.append(KPISpec(col, agg))
        if len(schema.measures) >= 2 and st.checkbox("Add a ratio metric", key=f"ratio_{ctx}"):
            a, b = st.columns(2)
            num = a.selectbox("Numerator", schema.measures, index=0, key=f"num_{ctx}")
            den = b.selectbox("Denominator", schema.measures, index=1, key=f"den_{ctx}")
            fmt = st.selectbox("Show as", ["Percent", "Ratio"], key=f"rfmt_{ctx}")
            if num != den:
                specs.append(KPISpec(num, "Ratio (%)" if fmt == "Percent" else "Ratio (x)", den))
    return specs, (None if time_choice == none else time_choice)

"""Sidebar filters generated from the columns of the uploaded dataset."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from .profiling import Schema, as_label, rank_measures


def _defaults(date_col, schema: Schema, ranked: list[str]) -> list[str]:
    chosen = ([date_col] if date_col else []) + schema.dims[:3]
    for c in ranked:
        if len(chosen) >= 3:
            break
        if c not in chosen:
            chosen.append(c)
    return chosen


def render_filters(df: pd.DataFrame, schema: Schema, date_col: str | None, ctx: str) -> pd.DataFrame:
    """Draw the filter widgets and return the filtered frame."""
    epoch = st.session_state.get("epoch", 0)
    ranked = rank_measures(df, schema)
    candidates = ([date_col] if date_col else []) + schema.dims + [c for c in schema.measures if c not in schema.dims]

    st.sidebar.markdown('<div class="side-label">Filters</div>', unsafe_allow_html=True)
    chosen = st.sidebar.multiselect(
        "Filter columns", candidates, default=_defaults(date_col, schema, ranked), key=f"fcols_{ctx}_{epoch}",
        help="Choose which columns to filter by. The defaults are picked from your dataset.")

    mask = pd.Series(True, index=df.index)
    for col in chosen:
        key = f"flt_{col}_{ctx}_{epoch}"
        if col == date_col:
            lo, hi = df[col].min().date(), df[col].max().date()
            picked = st.sidebar.date_input(col, value=(lo, hi), min_value=lo, max_value=hi, key=key)
            if isinstance(picked, (tuple, list)) and len(picked) == 2 and (picked[0] > lo or picked[1] < hi):
                start, end = pd.Timestamp(picked[0]), pd.Timestamp(picked[1]) + pd.Timedelta(days=1)
                mask &= (df[col] >= start) & (df[col] < end)
        elif col in schema.dims:
            labels = as_label(df[col])
            options = sorted(labels.dropna().unique(), key=lambda v: (len(str(v)) if str(v).isdigit() else 0, str(v)))
            picked = st.sidebar.multiselect(col, options, key=key, placeholder="All")
            if picked:
                mask &= labels.isin(picked)
        else:
            lo, hi = float(df[col].min()), float(df[col].max())
            if not np.isfinite(lo) or lo == hi:
                st.sidebar.caption(f"{col}: single value, nothing to filter")
                continue
            if bool((df[col].dropna() % 1 == 0).all()):
                lo, hi, step, fmt = int(lo), int(hi), 1, "%d"
            else:
                step, fmt = float(f"{(hi - lo) / 200:.2g}") or 0.01, "%.2f"
            picked = st.sidebar.slider(col, min_value=lo, max_value=hi, value=(lo, hi), step=step, format=fmt, key=key)
            if picked[0] > lo or picked[1] < hi:
                mask &= df[col].between(picked[0], picked[1])

    filtered = df[mask]
    st.sidebar.caption(f"{len(filtered):,} of {len(df):,} records match")
    if st.sidebar.button("Reset filters"):
        st.session_state["epoch"] = epoch + 1
        st.rerun()
    return filtered

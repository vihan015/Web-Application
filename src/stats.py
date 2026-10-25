"""Reusable aggregations and statistical summaries."""
from __future__ import annotations

import pandas as pd

from .profiling import as_label

RECORDS = "Records"
AGGREGATIONS = {"Sum": "sum", "Mean": "mean", "Median": "median", "Min": "min", "Max": "max", "Distinct count": "nunique"}
GRANULARITY = {"Day": "D", "Week": "W", "Month": "M", "Quarter": "Q", "Year": "Y"}
_ZERO_FILL = {"Sum", "Distinct count"}


def measure_label(measure: str, agg: str) -> str:
    return "Number of records" if measure == RECORDS else f"{agg} of {measure}"


def aggregate_by(df: pd.DataFrame, by: str, measure: str, agg: str) -> pd.DataFrame:
    """One value per category. Columns: Group, Value."""
    groups = as_label(df[by]).rename("Group")
    g = df.groupby(groups, observed=True)
    value = g.size() if measure == RECORDS else g[measure].agg(AGGREGATIONS[agg])
    return value.rename("Value").reset_index()


def time_series(df: pd.DataFrame, date_col: str, freq: str, measure: str, agg: str) -> pd.DataFrame:
    """One value per period, with empty periods filled so the line is continuous. Columns: Period, Value."""
    d = df.dropna(subset=[date_col])
    period = d[date_col].dt.to_period(freq).rename("Period")
    g = d.groupby(period)
    value = g.size() if measure == RECORDS else g[measure].agg(AGGREGATIONS[agg])
    full = pd.period_range(value.index.min(), value.index.max(), freq=freq)
    value = value.reindex(full)
    if measure == RECORDS or agg in _ZERO_FILL:
        value = value.fillna(0)
    value.index = value.index.to_timestamp()
    return value.rename("Value").rename_axis("Period").reset_index()


def suggest_granularity(start: pd.Timestamp, end: pd.Timestamp) -> str:
    days = (end - start).days
    if days <= 60:
        return "Day"
    if days <= 180:
        return "Week"
    if days <= 1460:
        return "Month"
    return "Quarter"


def numeric_summary(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if not cols:
        return pd.DataFrame()
    d = df[cols].describe(percentiles=[0.25, 0.5, 0.75]).T
    d["skew"] = df[cols].skew()
    d["missing"] = df[cols].isna().sum()
    d = d.rename(columns={"50%": "median"})
    d = d[["count", "missing", "mean", "std", "min", "25%", "median", "75%", "max", "skew"]]
    return d.round(2).rename_axis("Column").reset_index()


def categorical_summary(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    rows = []
    for c in cols:
        counts = as_label(df[c]).value_counts(dropna=True)
        rows.append({
            "Column": c,
            "Unique": int(df[c].nunique()),
            "Most frequent": str(counts.index[0]) if len(counts) else "",
            "Frequency": int(counts.iloc[0]) if len(counts) else 0,
            "Share (%)": round(100 * counts.iloc[0] / max(len(df), 1), 1) if len(counts) else 0.0,
            "Missing": int(df[c].isna().sum()),
        })
    return pd.DataFrame(rows)


def group_summary(df: pd.DataFrame, by: str, cols: list[str], agg: str) -> pd.DataFrame:
    """Aggregate numeric columns per category, plus a record count.

    The grouping column is left out of the aggregated columns, and the count column is renamed
    if a dataset column already uses the name 'Records'.
    """
    cols = [c for c in cols if c != by]
    g = df.groupby(as_label(df[by]).rename("Group"), observed=True)
    out = g[cols].agg(AGGREGATIONS[agg]) if cols else pd.DataFrame(index=g.size().index)
    count_name = "Records" if "Records" not in cols else "Record count"
    out.insert(0, count_name, g.size())
    group_name = by if by not in out.columns else f"{by} (group)"
    return out.round(2).reset_index().rename(columns={"Group": group_name}).sort_values(count_name, ascending=False)

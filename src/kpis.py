"""KPI definitions, automatic suggestions and calculation."""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from .profiling import Schema, as_label, is_additive, rank_measures

AGG_OPTIONS = {
    "numeric": ["Sum", "Mean", "Median", "Min", "Max", "Std dev"],
    "categorical": ["Distinct count", "Most frequent", "Top value share (%)"],
    "label": ["Distinct count", "Most frequent", "Top value share (%)"],
    "identifier": ["Distinct count"],
    "text": ["Distinct count"],
    "boolean": ["Rate (%)", "Count true"],
    "datetime": ["Latest", "Earliest", "Span (days)"],
}
_EXTENSIVE = {"Sum", "Count", "Distinct count", "Count true"}
_POINTS = {"Rate (%)", "Top value share (%)", "Ratio (%)"}


@dataclass(frozen=True)
class KPISpec:
    column: str | None            # None means "number of records"
    agg: str = "Count"
    column2: str | None = None    # denominator for ratio KPIs

    @property
    def label(self) -> str:
        c, a = self.column, self.agg
        if c is None:
            return "Records"
        return {
            "Sum": f"Total {c}", "Mean": f"Average {c}", "Median": f"Median {c}", "Min": f"Minimum {c}",
            "Max": f"Maximum {c}", "Std dev": f"Std dev of {c}", "Distinct count": f"Unique {c}",
            "Most frequent": f"Top {c}", "Top value share (%)": f"Top {c} share", "Rate (%)": f"{c} rate",
            "Count true": f"{c} (count)", "Latest": f"Latest {c}", "Earliest": f"Earliest {c}",
            "Span (days)": f"{c} span (days)", "Ratio (%)": f"{c} / {self.column2} (%)", "Ratio (x)": f"{c} / {self.column2}",
        }.get(a, f"{a} {c}")


def default_agg(column: str, kind: str) -> str:
    if kind == "numeric":
        return "Sum" if is_additive(column) else "Mean"
    return AGG_OPTIONS.get(kind, ["Distinct count"])[0]


def suggest_kpis(df: pd.DataFrame, schema: Schema, max_keys: int = 4) -> list[KPISpec]:
    """Records plus the columns that look most important, mixing measures, identifiers and flags."""
    ranked = rank_measures(df, schema)
    ident = next((c for c in schema.identifiers if df[c].nunique() < len(df)), None)
    flag = next((c for c in schema.booleans), None)
    order = [ranked[0] if ranked else None, ident, ranked[1] if len(ranked) > 1 else None, flag,
             ranked[2] if len(ranked) > 2 else None, ranked[3] if len(ranked) > 3 else None]
    keys = [c for c in order if c][:max_keys]
    specs = [KPISpec(None)]
    specs += [KPISpec(c, default_agg(c, schema.kinds[c])) for c in keys]
    return specs


def compute_value(df: pd.DataFrame, spec: KPISpec):
    """Return a float, a string (most frequent value), a Timestamp, or None."""
    if spec.column is None:
        return len(df)
    if spec.agg.startswith("Ratio"):
        den = float(df[spec.column2].sum())
        if den == 0:
            return None
        ratio = float(df[spec.column].sum()) / den
        return ratio * 100 if spec.agg == "Ratio (%)" else ratio
    s = df[spec.column]
    a = spec.agg
    if s.dropna().empty:
        return None
    if a == "Sum":
        return float(s.sum())
    if a == "Mean":
        return float(s.mean())
    if a == "Median":
        return float(s.median())
    if a == "Min":
        return float(s.min())
    if a == "Max":
        return float(s.max())
    if a == "Std dev":
        return float(s.std()) if s.count() > 1 else None
    if a == "Distinct count":
        return int(s.nunique())
    if a == "Rate (%)":
        return float(s.astype(float).mean() * 100)
    if a == "Count true":
        return int(s.astype(float).sum())
    if a in ("Most frequent", "Top value share (%)"):
        counts = as_label(s).value_counts()
        return str(counts.index[0]) if a == "Most frequent" else float(counts.iloc[0] / counts.sum() * 100)
    if a == "Latest":
        return s.max()
    if a == "Earliest":
        return s.min()
    if a == "Span (days)":
        return int((s.max() - s.min()).days)
    return None


def format_compact(value: float) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    sign, v = ("-" if value < 0 else ""), abs(value)
    for limit, div, suffix in ((1e9, 1e9, "B"), (1e6, 1e6, "M"), (1e4, 1e3, "K")):
        if v >= limit:
            return f"{sign}{v / div:,.2f}{suffix}"
    return f"{sign}{v:,.0f}" if float(v).is_integer() else f"{sign}{v:,.2f}"


def format_value(value, spec: KPISpec) -> tuple[str, str]:
    """(display text, full-precision tooltip)."""
    if value is None:
        return "n/a", "Not enough data"
    if isinstance(value, pd.Timestamp):
        return f"{value:%d %b %Y}", f"{value:%Y-%m-%d}"
    if isinstance(value, str):
        return value, value
    if spec.agg in _POINTS:
        return f"{value:.1f}%", f"{value:.4f}%"
    if spec.agg == "Ratio (x)":
        return f"{value:,.2f}", f"{value:,.6f}"
    return format_compact(value), f"{value:,.4f}".rstrip("0").rstrip(".")


def _sub(cur, base, spec: KPISpec, df_len: int) -> str:
    a = spec.agg
    if cur is None or base is None or isinstance(cur, (str, pd.Timestamp)):
        if a == "Most frequent" and isinstance(cur, str):
            return "Most common value"
        return ""
    if a in _EXTENSIVE or spec.column is None:
        if math.isclose(cur, base):
            return "Full dataset"
        if a == "Distinct count":
            return f"of {base:,.0f} overall"
        return f"{100 * cur / base:.1f}% of dataset" if base else ""
    if a in _POINTS:
        return "Overall" if math.isclose(cur, base, abs_tol=0.05) else f"{cur - base:+.1f} pts vs overall"
    if math.isclose(cur, base, rel_tol=1e-9):
        return "Overall"
    return f"{100 * (cur / base - 1):+.1f}% vs overall" if base else ""


def kpi_cards(specs: list[KPISpec], df: pd.DataFrame, baseline: pd.DataFrame) -> list[dict]:
    cards = []
    for spec in specs:
        cur, base = compute_value(df, spec), compute_value(baseline, spec)
        text, title = format_value(cur, spec)
        cards.append({
            "label": spec.label, "value": text, "sub": _sub(cur, base, spec, len(df)), "title": f"{spec.label}: {title}",
            "negative": isinstance(cur, (int, float)) and cur < 0,
        })
    return cards

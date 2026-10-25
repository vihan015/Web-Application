"""Infer what each column is (measure, category, date, identifier, ...) and rank what matters."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd
from pandas.api.types import is_bool_dtype, is_datetime64_any_dtype, is_numeric_dtype

MISSING_TOKENS = {"", "nan", "none", "null", "n/a", "na", "#n/a", "-", "--", "?", "nat"}

KIND_LABELS = {
    "numeric": "Numeric", "categorical": "Category", "label": "Label", "identifier": "Identifier",
    "datetime": "Date", "boolean": "Flag", "text": "Free text", "constant": "Constant",
}

_ID_SUFFIXES = ("id", "uuid", "guid", "key", "index", "idx", "number", "num")
MEASURE_TOKENS = {
    "sale", "revenue", "amount", "total", "profit", "cost", "spend", "price", "income", "salary", "pay",
    "score", "rating", "quantity", "qty", "unit", "volume", "value", "expense", "fare", "weight", "duration",
    "hour", "margin", "balance", "budget", "charge", "fee", "wage", "tax", "discount", "age", "rate",
}
ADDITIVE_TOKENS = {
    "sale", "revenue", "amount", "total", "profit", "cost", "spend", "income", "expense", "quantity", "qty",
    "unit", "volume", "payment", "budget", "fee", "charge", "tax", "count",
}
NON_ADDITIVE_TOKENS = {
    "price", "rate", "ratio", "score", "rating", "age", "salary", "wage", "discount", "margin", "percent",
    "pct", "avg", "average", "mean", "tenure", "experience", "weight", "temperature", "per",
}


STRONG_TOKENS = {"sale", "revenue", "amount", "profit", "income", "salary", "cost", "price", "spend", "total", "expense", "wage", "fare"}


def tokens(name: str) -> set[str]:
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(name))
    return {t[:-1] if t.endswith("s") and len(t) > 3 else t for t in re.findall(r"[a-z]+", spaced.lower())}


def _id_like(name: str) -> bool:
    n = re.sub(r"[^a-z0-9]", "", str(name).lower())
    return n.startswith("id") or n.endswith(_ID_SUFFIXES)


def is_additive(name: str) -> bool:
    t = tokens(name)
    return bool(t & ADDITIVE_TOKENS) and not (t & NON_ADDITIVE_TOKENS)


def _is_whole(s: pd.Series) -> bool:
    v = s.dropna()
    return len(v) > 0 and bool((v % 1 == 0).all())


@dataclass
class Schema:
    kinds: dict[str, str]
    measures: list[str] = field(default_factory=list)      # numeric columns worth aggregating
    dims: list[str] = field(default_factory=list)          # low-cardinality: filters and grouping
    labels: list[str] = field(default_factory=list)        # high-cardinality categories: grouping only
    identifiers: list[str] = field(default_factory=list)
    datetimes: list[str] = field(default_factory=list)
    booleans: list[str] = field(default_factory=list)

    @property
    def group_options(self) -> list[str]:
        return self.dims + self.labels


def _infer_kind(s: pd.Series, name: str, rows: int) -> str:
    n = s.nunique(dropna=True)
    if n <= 1:
        return "constant"
    if is_datetime64_any_dtype(s):
        return "datetime"
    if is_bool_dtype(s):
        return "boolean"
    if is_numeric_dtype(s):
        vals = s.dropna()
        if n == 2 and set(vals.unique()) <= {0, 1}:
            return "boolean"
        whole = _is_whole(s)
        if whole and "year" in tokens(name) and vals.min() >= 1900 and vals.max() <= 2100:
            return "categorical"
        if whole and ((_id_like(name) and n > 0.5 * rows) or (rows > 20 and n == len(vals) and vals.is_monotonic_increasing)):
            return "identifier"
        return "numeric"
    ratio = n / max(rows, 1)
    if n <= 50 and (n <= 12 or ratio < 0.5):
        return "categorical"
    avg_len = s.dropna().astype(str).str.len().mean()
    if avg_len > 60:
        return "text"
    return "identifier" if (ratio > 0.5 or _id_like(name)) else "label"


def build_schema(df: pd.DataFrame) -> Schema:
    rows = max(len(df), 1)
    kinds = {c: _infer_kind(df[c], c, rows) for c in df.columns}
    measures = [c for c, k in kinds.items() if k == "numeric"]
    low_card_numeric = [c for c in measures if _is_whole(df[c]) and df[c].nunique() <= 8]
    categorical = [c for c, k in kinds.items() if k in ("categorical", "boolean")]
    dims = sorted(set(categorical + low_card_numeric), key=lambda c: (df[c].nunique(), c))
    return Schema(
        kinds=kinds,
        measures=measures,
        dims=dims,
        labels=[c for c, k in kinds.items() if k == "label"],
        identifiers=[c for c, k in kinds.items() if k == "identifier"],
        datetimes=[c for c, k in kinds.items() if k == "datetime"],
        booleans=[c for c, k in kinds.items() if k == "boolean"],
    )


def rank_measures(df: pd.DataFrame, schema: Schema) -> list[str]:
    """Order numeric columns by likely importance: completeness, variation and measure-like names."""
    scored = []
    for c in schema.measures:
        s = df[c].dropna()
        if s.empty:
            continue
        mean, sd = s.mean(), s.std()
        spread = min(abs(sd / mean), 1.0) if mean and pd.notna(sd) else 0.0
        t = tokens(c)
        hint = (1.0 if t & MEASURE_TOKENS else 0.0) + (0.5 if t & STRONG_TOKENS else 0.0)
        scored.append((len(s) / len(df) * (0.5 + spread) + hint, c))
    return [c for _, c in sorted(scored, key=lambda t: (-t[0], t[1]))]


def as_label(s: pd.Series) -> pd.Series:
    """String labels for grouping and filtering; whole numbers print without '.0'."""
    if is_numeric_dtype(s) and not is_bool_dtype(s) and _is_whole(s):
        return s.astype("Int64").astype("string")
    return s.astype("string")


def pick_time_column(df: pd.DataFrame, schema: Schema) -> str | None:
    if not schema.datetimes:
        return None
    hinted = [c for c in schema.datetimes if tokens(c) & {"date", "time", "created", "order", "day"}]
    return (hinted or schema.datetimes)[0]

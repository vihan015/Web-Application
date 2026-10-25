"""Dataset validation: dimensions, dtypes, missing values and duplicates."""
from __future__ import annotations

import pandas as pd

from .profiling import KIND_LABELS, MISSING_TOKENS


def missing_mask(s: pd.Series) -> pd.Series:
    """True where a value is NaN or a blank/placeholder string."""
    mask = s.isna()
    if not pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_datetime64_any_dtype(s):
        placeholder = s.astype("string").str.strip().str.lower().isin(MISSING_TOKENS)
        mask = mask | placeholder.fillna(False).astype(bool)
    return mask


def duplicate_count(df: pd.DataFrame) -> int:
    return int(df.duplicated().sum())


def dataset_overview(df: pd.DataFrame) -> dict[str, int | float]:
    missing_cells = int(sum(missing_mask(df[c]).sum() for c in df.columns))
    return {
        "rows": len(df),
        "columns": df.shape[1],
        "missing_cells": missing_cells,
        "missing_pct": 100 * missing_cells / max(df.size, 1),
        "duplicates": duplicate_count(df),
        "memory_mb": df.memory_usage(deep=True).sum() / 1_048_576,
    }


def column_profile(df: pd.DataFrame, kinds: dict[str, str] | None = None) -> pd.DataFrame:
    rows = []
    for c in df.columns:
        s = df[c]
        miss = int(missing_mask(s).sum())
        non_null = s.dropna()
        row = {
            "Column": c,
            "Data type": str(s.dtype),
            "Non-null": len(s) - miss,
            "Missing": miss,
            "Missing (%)": round(100 * miss / max(len(s), 1), 2),
            "Unique": int(s.nunique(dropna=True)),
            "Sample": str(non_null.iloc[0]) if len(non_null) else "",
        }
        if kinds:
            row = {"Column": c, "Detected as": KIND_LABELS.get(kinds.get(c, ""), ""), **{k: v for k, v in row.items() if k != "Column"}}
        rows.append(row)
    return pd.DataFrame(rows)

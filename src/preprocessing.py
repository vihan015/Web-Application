"""Generic cleaning pipeline: text, numbers stored as text, dates, missing values, duplicates."""
from __future__ import annotations

import pandas as pd
from pandas.api.types import is_bool_dtype, is_datetime64_any_dtype, is_numeric_dtype

from .profiling import MISSING_TOKENS, build_schema

NUMERIC_MISSING_OPTIONS = ("Leave as missing", "Fill with median", "Fill with 0", "Drop rows")
CATEGORY_MISSING_OPTIONS = ("Fill with 'Unknown'", "Leave as missing", "Drop rows")

_NUMBER_RE = r"^\(?-?[$€£₹¥]?\s*-?\d[\d,]*(\.\d+)?\s*%?\)?$"
_DATE_RE = (
    r"^\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}"
    r"|\d{1,2}\s+[A-Za-z]{3,9}\.?,?\s+\d{2,4}|[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4})([ T].*)?$"
)


class DataValidationError(ValueError):
    """Raised when nothing usable remains after cleaning."""


def _is_text(s: pd.Series) -> bool:
    return not (is_numeric_dtype(s) or is_datetime64_any_dtype(s) or is_bool_dtype(s))


def standardise_text(s: pd.Series, unify_limit: int = 1000) -> pd.Series:
    """Trim whitespace, null out placeholders and merge case variants ("west" / "WEST " -> "West")."""
    txt = s.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    txt = txt.mask(txt.str.lower().isin(MISSING_TOKENS).fillna(False).astype(bool))
    if txt.nunique() <= unify_limit:
        key = txt.str.lower()
        canon = txt.groupby(key).agg(lambda x: x.value_counts().idxmax())
        txt = key.map(canon)
    return txt.astype(object)


def to_numeric(s: pd.Series) -> pd.Series:
    """Parse numbers stored as text ("$1,234.50", "(45)", "12%")."""
    if is_numeric_dtype(s) and not is_bool_dtype(s):
        return s
    txt = s.astype("string").str.strip()
    negative = txt.str.match(r"^\(.*\)$").fillna(False).astype(bool)
    out = pd.to_numeric(txt.str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
    return out.where(~negative, -out.abs())


def parse_dates(s: pd.Series) -> pd.Series:
    """Parse mixed date formats; tries month-first, then day-first for anything left over."""
    if is_datetime64_any_dtype(s):
        parsed = s
    else:
        text = s.astype("string").str.strip()
        try:
            parsed = pd.to_datetime(text, errors="coerce", format="mixed")
        except (ValueError, TypeError):
            parsed = pd.to_datetime(text, errors="coerce", utc=True).dt.tz_localize(None)
        retry = parsed.isna() & text.notna()
        if retry.any():
            try:
                parsed.loc[retry] = pd.to_datetime(text[retry], errors="coerce", dayfirst=True, format="mixed")
            except (ValueError, TypeError):
                pass
    if getattr(parsed.dtype, "tz", None) is not None:
        parsed = parsed.dt.tz_localize(None)
    return parsed


def _share_matching(s: pd.Series, pattern: str) -> float:
    txt = s.dropna().astype(str).str.strip()
    return float(txt.str.match(pattern).mean()) if len(txt) else 0.0


def preprocess(
    df: pd.DataFrame,
    remove_duplicates: bool = True,
    numeric_missing: str = NUMERIC_MISSING_OPTIONS[0],
    category_missing: str = CATEGORY_MISSING_OPTIONS[0],
) -> tuple[pd.DataFrame, list[str]]:
    """Return the cleaned frame and a log of every change made."""
    log: list[str] = []
    out = df.copy()
    n_start = len(out)

    # 1. Text: whitespace, placeholders, case variants
    text_cols = [c for c in out.columns if _is_text(out[c])]
    merged = 0
    for c in text_cols:
        before = out[c].nunique()
        out[c] = standardise_text(out[c])
        merged += max(before - out[c].nunique(), 0)
    if text_cols:
        log.append(f"Trimmed whitespace and normalised placeholders in {len(text_cols)} text column(s)")
    if merged:
        log.append(f"Merged {merged} inconsistent spelling or case variant(s) in categorical values")

    # 2. Numbers stored as text, 3. dates stored as text
    for c in text_cols:
        s = out[c]
        filled = int(s.notna().sum())
        if not filled:
            continue
        if _share_matching(s, _NUMBER_RE) >= 0.9:
            matches = s.astype("string").str.strip().str.match(_NUMBER_RE).fillna(False).astype(bool)
            out[c] = to_numeric(s).where(matches)
            bad = filled - int(out[c].notna().sum())
            log.append(f"Converted '{c}' from text to numbers" + (f" ({bad} unreadable value(s) set to missing)" if bad else ""))
        elif _share_matching(s.sample(min(filled, 200), random_state=0) if filled > 200 else s, _DATE_RE) >= 0.9:
            parsed = parse_dates(s)
            if parsed.notna().sum() >= 0.9 * filled:
                out[c] = parsed
                log.append(f"Parsed '{c}' as dates, range {parsed.min():%Y-%m-%d} to {parsed.max():%Y-%m-%d}")

    # 4. Missing values
    schema = build_schema(out)
    measures = schema.measures
    if measures:
        rows_missing = int(out[measures].isna().any(axis=1).sum())
        cells = int(out[measures].isna().sum().sum())
        if cells:
            if numeric_missing == "Drop rows":
                out = out.dropna(subset=measures).copy()
                log.append(f"Dropped {rows_missing} row(s) with missing numeric values")
            elif numeric_missing == "Fill with median":
                out[measures] = out[measures].fillna(out[measures].median())
                log.append(f"Filled {cells} missing numeric value(s) with the column median")
            elif numeric_missing == "Fill with 0":
                out[measures] = out[measures].fillna(0)
                log.append(f"Filled {cells} missing numeric value(s) with 0")
            else:
                log.append(f"{cells} missing numeric value(s) left as missing (ignored by calculations)")
    cats = [c for c in schema.dims + schema.labels if _is_text(out[c])]
    if cats:
        cells = int(out[cats].isna().sum().sum())
        if cells:
            if category_missing == "Drop rows":
                before = len(out)
                out = out.dropna(subset=cats).copy()
                log.append(f"Dropped {before - len(out)} row(s) with missing categorical values")
            elif category_missing == "Fill with 'Unknown'":
                out[cats] = out[cats].fillna("Unknown")
                log.append(f"Filled {cells} missing categorical value(s) with 'Unknown'")
            else:
                log.append(f"{cells} missing categorical value(s) left as missing")

    # 5. Duplicates
    if remove_duplicates:
        before = len(out)
        out = out.drop_duplicates()
        if before - len(out):
            log.append(f"Removed {before - len(out)} duplicate row(s)")

    out = out.reset_index(drop=True)
    if out.empty:
        raise DataValidationError("No rows remain after cleaning. Review the cleaning options in the sidebar.")
    log.append(f"Rows after cleaning: {len(out):,} of {n_start:,}")
    return out, log

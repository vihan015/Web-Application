"""Read CSV, Excel and JSON uploads into a tidy DataFrame."""
from __future__ import annotations

import csv
import io
import json
import re

import pandas as pd

SUPPORTED_EXTENSIONS = ("csv", "xlsx", "json")


class DataLoadError(Exception):
    """Raised when an uploaded file cannot be turned into a table."""


def get_extension(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def excel_sheets(content: bytes) -> list[str]:
    try:
        return pd.ExcelFile(io.BytesIO(content), engine="openpyxl").sheet_names
    except Exception as exc:
        raise DataLoadError(f"Could not open the Excel workbook: {exc}") from exc


def load_dataframe(name: str, content: bytes, sheet: str | None = None) -> pd.DataFrame:
    ext = get_extension(name)
    if ext not in SUPPORTED_EXTENSIONS:
        raise DataLoadError(f"Unsupported file type '.{ext}'. Upload a CSV, XLSX or JSON file.")
    if not content:
        raise DataLoadError("The uploaded file is empty.")
    try:
        if ext == "csv":
            df = _read_csv(content)
        elif ext == "xlsx":
            df = _read_excel(content, sheet)
        else:
            df = _read_json(content)
    except DataLoadError:
        raise
    except Exception as exc:
        raise DataLoadError(f"Could not parse '{name}' as {ext.upper()}: {exc}") from exc
    return _tidy(df)


def _read_csv(content: bytes) -> pd.DataFrame:
    text = ""
    for enc in ("utf-8-sig", "latin-1"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    try:
        sep = csv.Sniffer().sniff(text[:10000], delimiters=",;\t|").delimiter
    except csv.Error:
        sep = ","
    return pd.read_csv(io.StringIO(text), sep=sep, low_memory=False)


def _read_excel(content: bytes, sheet: str | None) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(content), sheet_name=sheet or 0, engine="openpyxl")


def _read_json(content: bytes) -> pd.DataFrame:
    text = content.decode("utf-8-sig")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        try:  # newline-delimited JSON
            return pd.read_json(io.StringIO(text), lines=True)
        except ValueError as exc:
            raise DataLoadError(f"Invalid JSON: {exc}") from exc
    if isinstance(data, dict):
        nested = [v for v in data.values() if isinstance(v, list) and v and isinstance(v[0], dict)]
        if len(nested) == 1:
            data = nested[0]
        elif data and all(isinstance(v, list) for v in data.values()):
            return pd.DataFrame(data)
        else:
            data = [data]
    if not isinstance(data, list) or not data:
        raise DataLoadError("The JSON file does not contain a list of records.")
    if not all(isinstance(r, dict) for r in data):
        raise DataLoadError("Each JSON record must be an object with named fields.")
    return pd.json_normalize(data)


def _tidy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how="all").dropna(axis=1, how="all")
    if df.empty:
        raise DataLoadError("The file contains no data rows.")
    seen: dict[str, int] = {}
    names = []
    for raw in df.columns:
        n = re.sub(r"\s+", " ", str(raw)).strip() or "Column"
        seen[n] = seen.get(n, 0) + 1
        names.append(n if seen[n] == 1 else f"{n}_{seen[n]}")
    df.columns = names
    for c in df.columns:
        if df[c].dtype == object and df[c].map(lambda v: isinstance(v, (list, dict))).any():
            df[c] = df[c].map(lambda v: json.dumps(v, default=str) if isinstance(v, (list, dict)) else v)
    return df.reset_index(drop=True)

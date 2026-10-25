import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.kpis import KPISpec, compute_value, format_compact, kpi_cards, suggest_kpis
from src.loader import DataLoadError, load_dataframe
from src.preprocessing import parse_dates, preprocess, to_numeric
from src.profiling import build_schema, rank_measures
from src.stats import aggregate_by, group_summary, time_series
from src.validation import dataset_overview


def messy():
    return pd.DataFrame({
        "Student ID": [f"S{i}" for i in range(40)] + ["S1", "S2"],
        "Joined": ["2024-01-05", "05 Feb 2024", "03/15/2024"] * 14,
        "Course": ["math", "Math ", "Physics", "PHYSICS"] * 10 + ["Math", "Math"],
        "Score": ["71.5", "88", "n/a", "92"] * 10 + ["60", "61"],
        "Hours": np.arange(42) * 0.5 + 1,
        "Passed": [1, 0] * 21,
    })


def test_preprocess_infers_types_and_cleans():
    clean, log = preprocess(messy())
    s = build_schema(clean)
    assert s.kinds["Joined"] == "datetime"
    assert s.kinds["Score"] == "numeric" and s.kinds["Passed"] == "boolean"
    assert clean["Course"].nunique() == 2
    assert s.kinds["Student ID"] == "identifier"
    assert log


def test_numeric_text_and_dates():
    out = to_numeric(pd.Series(["$1,234.50", "(45)", "x", None]))
    assert out.iloc[0] == 1234.5 and out.iloc[1] == -45 and out.iloc[2:].isna().all()
    d = parse_dates(pd.Series(["2024-01-05", "05 Feb 2024", "03/15/2024", "junk"]))
    assert d.iloc[:3].notna().all() and pd.isna(d.iloc[3])


def test_suggested_kpis_are_dynamic():
    clean, _ = preprocess(messy())
    s = build_schema(clean)
    specs = suggest_kpis(clean, s)
    assert specs[0].column is None
    cols = {sp.column for sp in specs}
    assert "Passed" in cols and "Score" in cols
    assert next(sp for sp in specs if sp.column == "Passed").agg == "Rate (%)"
    cards = kpi_cards(specs, clean, clean)
    assert len(cards) == len(specs) and all(c["value"] for c in cards)


def test_kpi_values_and_filtered_comparison():
    df = pd.DataFrame({"Revenue": [10.0, 20.0, 30.0, 40.0], "Region": list("aabb"), "Cost": [5.0, 5.0, 10.0, 10.0]})
    assert compute_value(df, KPISpec("Revenue", "Sum")) == 100
    assert compute_value(df, KPISpec("Revenue", "Ratio (%)", "Cost")) == pytest.approx(100 / 30 * 100)
    assert compute_value(df, KPISpec("Region", "Distinct count")) == 2
    card = kpi_cards([KPISpec("Revenue", "Sum")], df[df.Region == "a"], df)[0]
    assert card["value"] == "30" and card["sub"] == "30.0% of dataset"


def test_ranking_prefers_measure_like_columns():
    df = pd.DataFrame({"Annual Salary": np.random.default_rng(0).normal(1e6, 2e5, 50),
                       "Training Hours": np.random.default_rng(1).gamma(3, 8, 50), "Dept": ["a", "b"] * 25})
    assert rank_measures(df, build_schema(df))[0] == "Annual Salary"


def test_aggregations_match_pandas():
    clean, _ = preprocess(messy())
    agg = aggregate_by(clean, "Course", "Score", "Mean")
    assert agg["Value"].notna().all() and len(agg) == 2
    ts = time_series(clean, "Joined", "M", "Records", "Count")
    assert ts["Value"].sum() == len(clean)
    assert "Records" in group_summary(clean, "Course", ["Score"], "Mean").columns


def test_works_without_dates_or_numbers():
    df = pd.DataFrame({"Colour": ["red", "blue", "red", "green"] * 5, "Size": ["S", "M"] * 10})
    clean, _ = preprocess(df, remove_duplicates=False)
    s = build_schema(clean)
    specs = suggest_kpis(clean, s)
    assert [sp.column for sp in specs] == [None]
    assert kpi_cards(specs, clean, clean)[0]["value"] == "20"


def test_format_compact():
    assert format_compact(12226) == "12.23K" and format_compact(3_400_000) == "3.40M" and format_compact(950) == "950"


def test_loaders_and_errors():
    df = messy()
    assert len(load_dataframe("a.csv", df.to_csv(index=False).encode())) == 42
    buf = io.BytesIO(); df.to_excel(buf, index=False)
    assert len(load_dataframe("a.xlsx", buf.getvalue())) == 42
    assert len(load_dataframe("a.json", df.to_json(orient="records").encode())) == 42
    assert len(load_dataframe("a.json", json.dumps({"rows": df.to_dict("records")}).encode())) == 42
    for bad in (("a.txt", b"x"), ("a.csv", b"")):
        with pytest.raises(DataLoadError):
            load_dataframe(*bad)


def test_overview_counts_duplicates():
    ov = dataset_overview(pd.concat([messy(), messy().iloc[[0]]], ignore_index=True))
    assert ov["duplicates"] == 1 and ov["missing_cells"] >= 1


def test_drop_rows_option_and_empty_guard():
    clean, _ = preprocess(messy(), numeric_missing="Drop rows")
    assert clean["Score"].notna().all()


def wine_like():
    rng = np.random.default_rng(0)
    n = 200
    return pd.DataFrame({
        "fixed acidity": rng.normal(8, 1, n), "alcohol": rng.normal(10, 1, n),
        "quality": rng.integers(3, 9, n), "Records": rng.integers(1, 5, n),
    })


def test_group_by_a_measure_does_not_duplicate_columns():
    from src.charts import box_chart, scatter_chart
    clean, _ = preprocess(wine_like())
    s = build_schema(clean)
    assert "quality" in s.dims and "quality" in s.measures
    out = group_summary(clean, "quality", s.measures, "Mean")
    assert out.columns.is_unique
    out2 = group_summary(clean, "Records", s.measures, "Sum")
    assert out2.columns.is_unique
    # charts that group or colour by a column that is also plotted
    box_chart(clean, "quality", "quality")
    scatter_chart(clean, "quality", "alcohol", "quality", None)

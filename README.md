# Data Explorer

A Streamlit dashboard for any tabular dataset (CSV, XLSX, JSON). It works out what each column is,
suggests the KPIs that matter most, and lets you define your own key columns.

## Run

    python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    streamlit run app.py

Two samples are bundled (sidebar buttons): retail orders and employees. Both are intentionally messy.

## How KPIs are chosen

1. **Column roles are detected** from data and names: numeric measure, category, high-cardinality label,
   identifier, date, flag (0/1 or true/false), free text, constant.
2. **Measures are ranked** by completeness, variation and measure-like names (revenue, salary, cost, score...).
3. **Suggested cards**: record count, the top measures, an identifier (distinct count) and a flag (rate).
   Additive-looking columns (sales, quantity, cost) default to Sum; others (price, salary, rating) to Mean.
4. **You stay in control**: in the sidebar open "Key metrics and time" to pick any columns (up to 8), choose
   the aggregation for each (Sum, Mean, Median, Min, Max, Std dev, Distinct count, Most frequent, Rate, Earliest,
   Latest...), add a ratio metric (A / B as percent or ratio), and choose the time column.
5. Every card compares the filtered result with the full dataset.

## Features

- Upload and validation: dimensions, column names, dtypes, missing values (placeholders such as N/A count), duplicates.
- Cleaning: whitespace and case variants, numbers and dates stored as text, mixed date formats, missing values
  (numeric: leave, median, 0, drop; categorical: Unknown, leave, drop), duplicate removal, with a change log.
- Filters generated from the data: date range, category multi-selects, numeric sliders. Columns are selectable.
- Charts: trend (any measure and aggregation), two breakdowns, scatter, histogram, box plot by group,
  correlation heatmap, missing-values chart.
- Statistics tables and filtered CSV download.

## Structure

    app.py                  Page orchestration
    src/loader.py           CSV, XLSX, JSON readers
    src/validation.py       Dimensions, types, missing values, duplicates
    src/preprocessing.py    Cleaning pipeline
    src/profiling.py        Column role detection and measure ranking
    src/kpis.py             KPI definitions, suggestions, calculation
    src/kpi_setup.py        Sidebar controls for key columns
    src/filters.py          Dynamic filters
    src/stats.py            Reusable aggregations and summaries
    src/charts.py, views.py, ui.py   Charts, tabs, styling
    tests/                  python -m pytest

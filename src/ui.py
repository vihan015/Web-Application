"""Styling and small presentational helpers."""
from __future__ import annotations

import html

import streamlit as st

from .charts import CONFIG

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
/* Apply the font to text containers only; never to spans, which carry Material icon ligatures. */
.stApp, .stApp :where(p, label, h1, h2, h3, h4, div, li, td, th, a, button, input, textarea) {
  font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
}
.stApp [data-testid="stIconMaterial"], .stApp .material-symbols-rounded, .stApp [class*="material-icons"] {
  font-family: 'Material Symbols Rounded', 'Material Icons' !important;
}
.stApp { background: #000; color: #ededed; }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1240px; }

h1, h2, h3, h4 { letter-spacing: -0.02em; font-weight: 600; color: #fff; }
.app-title { font-size: 24px; font-weight: 600; letter-spacing: -0.03em; margin: 0; color: #fff; }
.app-meta { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 10px 0 22px; }
.pill { font-size: 12px; color: #a1a1a1; background: #0a0a0a; border: 1px solid #262626; border-radius: 999px; padding: 3px 10px; }
.pill b { font-weight: 500; color: #ededed; }

section[data-testid="stSidebar"] { background: #0a0a0a; border-right: 1px solid #262626; }
section[data-testid="stSidebar"] .stButton > button { width: 100%; }
.brand { font-weight: 600; font-size: 15px; letter-spacing: -0.02em; padding: 4px 0 2px; color: #fff; }
.brand-sub { font-size: 12px; color: #8f8f8f; margin-bottom: 14px; }
.side-label { font-size: 11px; font-weight: 500; letter-spacing: 0.06em; text-transform: uppercase; color: #8f8f8f; margin: 18px 0 6px; }

.cards { display: grid; grid-template-columns: repeat(var(--cols, 5), minmax(0, 1fr)); gap: 12px; margin-bottom: 22px; }
@media (max-width: 1000px) { .cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.card { background: #0a0a0a; border: 1px solid #262626; border-radius: 8px; padding: 14px 16px; min-width: 0; }
.card-label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 12px; font-weight: 500; color: #a1a1a1; }
.card-value { font-size: 26px; font-weight: 600; letter-spacing: -0.03em; color: #fff; margin-top: 6px; font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-value.neg { color: #ff6166; }
.card-sub { font-size: 12px; color: #8f8f8f; margin-top: 4px; }

.section-title { font-size: 14px; font-weight: 600; color: #fff; margin: 0; }
.section-desc { font-size: 12px; color: #8f8f8f; margin: 2px 0 10px; }

div[data-testid="stVerticalBlockBorderWrapper"] { background: #0a0a0a; border-radius: 8px; border-color: #262626 !important; }
.stTabs [data-baseweb="tab-list"] { gap: 26px; border-bottom: 1px solid #262626; }
.stTabs button[data-baseweb="tab"] { padding: 8px 0; height: auto; background: transparent; }
.stTabs button[data-baseweb="tab"] p { font-size: 14px; font-weight: 500; color: #a1a1a1; }
.stTabs button[aria-selected="true"] p { color: #fff; }
.stTabs [data-baseweb="tab-highlight"] { background: #fff; height: 2px; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 20px; }

.stButton > button, .stDownloadButton > button { border-radius: 6px; border: 1px solid #333; background: #0a0a0a; color: #ededed; font-weight: 500; font-size: 13px; box-shadow: none; }
.stButton > button:hover, .stDownloadButton > button:hover { border-color: #fff; color: #fff; background: #0a0a0a; }
label[data-testid="stWidgetLabel"] p { font-size: 12px; font-weight: 500; color: #a1a1a1; }
[data-testid="stExpander"] { border-color: #262626; background: #0a0a0a; }

.empty { background: #0a0a0a; border: 1px solid #262626; border-radius: 8px; padding: 36px 32px; margin-top: 8px; }
.empty h2 { font-size: 20px; margin: 0 0 6px; }
.empty p { color: #a1a1a1; font-size: 14px; margin: 0; max-width: 620px; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def sidebar_brand() -> None:
    st.sidebar.markdown(
        '<div class="brand">Data Explorer</div><div class="brand-sub">Upload, clean and explore any tabular data</div>',
        unsafe_allow_html=True,
    )


def sidebar_label(text: str) -> None:
    st.sidebar.markdown(f'<div class="side-label">{html.escape(text)}</div>', unsafe_allow_html=True)


def header(name: str, rows: int, cols: int) -> None:
    st.markdown(
        f'<h1 class="app-title">Data Explorer</h1>'
        f'<div class="app-meta"><span class="pill"><b>{html.escape(name)}</b></span>'
        f'<span class="pill">{rows:,} rows</span><span class="pill">{cols} columns</span></div>',
        unsafe_allow_html=True,
    )


def section(title: str, description: str = "") -> None:
    desc = f'<div class="section-desc">{html.escape(description)}</div>' if description else ""
    st.markdown(f'<div class="section-title">{html.escape(title)}</div>{desc}', unsafe_allow_html=True)


def cards(items: list[dict]) -> None:
    parts = []
    for it in items:
        neg = " neg" if it.get("negative") else ""
        parts.append(
            f'<div class="card" title="{html.escape(it.get("title", ""))}">'
            f'<div class="card-label">{html.escape(it["label"])}</div>'
            f'<div class="card-value{neg}">{html.escape(it["value"])}</div>'
            f'<div class="card-sub">{html.escape(it.get("sub", ""))}</div></div>'
        )
    n = len(items)
    cols = n if n <= 5 else -(-n // 2)
    st.markdown(f'<div class="cards" style="--cols:{cols}">{"".join(parts)}</div>', unsafe_allow_html=True)


def show_plot(fig, key: str) -> None:
    try:
        st.plotly_chart(fig, width="stretch", config=CONFIG, key=key)
    except TypeError:  # older Streamlit
        st.plotly_chart(fig, use_container_width=True, config=CONFIG, key=key)


def show_table(df, height: int | None = None) -> None:
    kwargs = {"hide_index": True}
    if height:
        kwargs["height"] = height
    try:
        st.dataframe(df, width="stretch", **kwargs)
    except TypeError:
        st.dataframe(df, use_container_width=True, **kwargs)


def empty_state() -> None:
    st.markdown(
        '<h1 class="app-title">Data Explorer</h1><div style="height:14px"></div>'
        '<div class="empty"><h2>Upload a dataset to begin</h2>'
        '<p>Use the sidebar to upload a CSV, Excel or JSON file, or load one of the bundled samples. '
        'The app works out which columns are measures, categories, dates and identifiers, suggests the '
        'KPIs that matter most, and lets you choose your own key columns.</p></div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    for col, title, body in (
        (c1, "Understand", "Validation, detected column types, missing values and duplicates."),
        (c2, "Measure", "KPIs suggested from the data, or defined by you from any column."),
        (c3, "Explore", "Filters and charts generated from whatever columns the file contains."),
    ):
        with col:
            st.markdown(
                f'<div class="card" style="margin-top:12px"><div class="card-label">{title}</div>'
                f'<div class="card-sub" style="color:#a1a1a1;font-size:13px;margin-top:6px">{body}</div></div>',
                unsafe_allow_html=True,
            )

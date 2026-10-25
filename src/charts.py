"""Plotly figures with a restrained, monochrome-plus-one-accent style."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

INK, ACCENT, NEG, GRID, MUTED, SURFACE = "#ededed", "#3291ff", "#ff6166", "#262626", "#a1a1a1", "#0a0a0a"
COLORWAY = [ACCENT, "#ededed", "#a78bfa", "#f5a623", "#3ecf8e", "#ff4d9d", "#8f8f8f"]
CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def _base(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=4, r=4, t=8, b=4),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, colorway=COLORWAY,
        font=dict(family="Inter, -apple-system, Segoe UI, sans-serif", size=12, color=INK),
        hoverlabel=dict(bgcolor="#111111", bordercolor="#333333", font=dict(size=12, color=INK)),
        legend=dict(orientation="h", y=-0.18, x=0, title_text="", font=dict(color=MUTED)),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=GRID, tickcolor=GRID, ticks="outside",
                     tickfont=dict(color=MUTED), title_font=dict(color=MUTED, size=12))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor="rgba(0,0,0,0)", tickfont=dict(color=MUTED),
                     title_font=dict(color=MUTED, size=12))
    return fig


def trend_chart(ts: pd.DataFrame, label: str) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=ts["Period"], y=ts["Value"], mode="lines+markers" if len(ts) <= 2 else "lines",
        line=dict(color=ACCENT, width=2), fill="tozeroy", fillcolor="rgba(50,145,255,0.10)", connectgaps=False,
        hovertemplate=f"%{{x|%d %b %Y}}<br>{label}: %{{y:,.2~f}}<extra></extra>",
    ))
    return _base(fig, 320)


def bar_chart(agg: pd.DataFrame, label: str, top_n: int) -> go.Figure:
    d = agg.dropna(subset=["Value"]).nlargest(top_n, "Value").sort_values("Value")
    fig = go.Figure(go.Bar(
        x=d["Value"], y=d["Group"], orientation="h",
        marker=dict(color=[INK if v >= 0 else NEG for v in d["Value"]]),
        texttemplate="%{x:,.2~f}", textposition="outside", cliponaxis=False, textfont=dict(size=11, color=MUTED),
        hovertemplate=f"%{{y}}<br>{label}: %{{x:,.2~f}}<extra></extra>",
    ))
    fig.update_xaxes(showgrid=True, gridcolor=GRID, ticks="")
    fig.update_yaxes(showgrid=False, automargin=True, type="category")
    fig.update_layout(margin=dict(l=4, r=56, t=8, b=4))
    return _base(fig, max(240, 28 * len(d) + 70))


def scatter_chart(df: pd.DataFrame, x: str, y: str, color: str | None, hover: str | None, max_points: int = 5000) -> go.Figure:
    d = df if len(df) <= max_points else df.sample(max_points, random_state=0)
    if color:
        d = d.assign(__color__=d[color].astype(str))
    fig = px.scatter(d, x=x, y=y, color="__color__" if color else None, hover_name=hover, opacity=0.6,
                     color_discrete_sequence=COLORWAY, labels={"__color__": color or ""})
    fig.update_traces(marker=dict(size=6, line=dict(width=0)))
    return _base(fig, 360)


def histogram_chart(df: pd.DataFrame, col: str, bins: int) -> go.Figure:
    fig = px.histogram(df, x=col, nbins=bins, color_discrete_sequence=[INK])
    fig.update_traces(marker_line_color=SURFACE, marker_line_width=1, hovertemplate="%{x}<br>Count: %{y}<extra></extra>")
    fig.update_yaxes(title_text="Count")
    fig.update_layout(bargap=0.02)
    return _base(fig, 360)


def box_chart(df: pd.DataFrame, value: str, by: str, max_groups: int = 12) -> go.Figure:
    groups = df[by].astype(str)
    top = groups.value_counts().head(max_groups).index
    d = df.assign(__group__=groups)
    d = d[d["__group__"].isin(top)]
    fig = px.box(d, x="__group__", y=value, color_discrete_sequence=[ACCENT], labels={"__group__": by},
                 category_orders={"__group__": sorted(top, key=lambda v: (len(v), v))})
    fig.update_traces(marker=dict(size=3, opacity=0.5), line=dict(width=1.5))
    return _base(fig, 360)


def correlation_chart(df: pd.DataFrame, cols: list[str]) -> go.Figure:
    corr = df[cols].corr().round(2)
    fig = px.imshow(corr, text_auto=".2f", zmin=-1, zmax=1, aspect="auto",
                    color_continuous_scale=[[0, ACCENT], [0.5, SURFACE], [1, NEG]])
    fig.update_layout(coloraxis_colorbar=dict(thickness=10, len=0.8, outlinewidth=0, tickfont=dict(color=MUTED)))
    fig.update_xaxes(showgrid=False, side="bottom")
    fig.update_yaxes(showgrid=False)
    return _base(fig, max(320, 44 * len(cols) + 80))


def missing_chart(profile: pd.DataFrame) -> go.Figure:
    d = profile[profile["Missing (%)"] > 0].sort_values("Missing (%)")
    fig = go.Figure(go.Bar(
        x=d["Missing (%)"], y=d["Column"], orientation="h", marker=dict(color=ACCENT),
        texttemplate="%{x:.1f}%", textposition="outside", cliponaxis=False, textfont=dict(size=11, color=MUTED),
        hovertemplate="%{y}<br>Missing: %{x:.2f}%<extra></extra>",
    ))
    fig.update_xaxes(showgrid=True, gridcolor=GRID, ticksuffix="%", ticks="")
    fig.update_yaxes(showgrid=False, automargin=True, type="category")
    fig.update_layout(margin=dict(l=4, r=48, t=8, b=4))
    return _base(fig, max(160, 28 * len(d) + 60))

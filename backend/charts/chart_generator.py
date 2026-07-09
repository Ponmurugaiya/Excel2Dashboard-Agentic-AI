"""
Chart Generator — Phase 1
Maps chart plan dicts → Plotly figure JSON.
No AI involved. Pure Plotly.
"""

import json
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# Plotly colour palette (cycles for multiple charts)
_COLOUR_SEQUENCE = px.colors.qualitative.Plotly


def generate_charts(
    plan: Dict[str, Any],
    sheets: Dict[str, pd.DataFrame],
) -> List[Dict[str, Any]]:
    """
    Build Plotly chart JSON for every chart in the dashboard plan.

    Args:
        plan:   Output from llm_planner.plan_dashboard()
        sheets: Output from excel_parser.parse_excel()

    Returns:
        List of chart dicts:
        [
            {
                "id": "chart_0",
                "title": "Sales Over Time",
                "type": "line",
                "figure": { ...plotly JSON... }
            },
            ...
        ]
    """
    charts_out = []

    for i, chart_spec in enumerate(plan.get("charts", [])):
        chart_type = chart_spec.get("type", "bar").lower()
        title = chart_spec.get("title", f"Chart {i + 1}")
        sheet = chart_spec.get("sheet")
        x_col = chart_spec.get("x")
        y_col = chart_spec.get("y")
        color_col = chart_spec.get("color")

        # Resolve the DataFrame
        df = _resolve_sheet(sheets, sheet)
        if df is None:
            continue

        # Validate columns exist
        if x_col and x_col not in df.columns:
            x_col = None
        if y_col and y_col not in df.columns:
            y_col = None
        if color_col and color_col not in df.columns:
            color_col = None

        try:
            fig = _build_figure(df, chart_type, title, x_col, y_col, color_col)
        except Exception as e:
            # Don't crash the whole pipeline for one bad chart
            fig = _error_figure(title, str(e))

        charts_out.append({
            "id": f"chart_{i}",
            "title": title,
            "type": chart_type,
            "figure": json.loads(fig.to_json()),
        })

    return charts_out


def compute_kpis(
    plan: Dict[str, Any],
    sheets: Dict[str, pd.DataFrame],
) -> List[Dict[str, Any]]:
    """
    Compute KPI values from the plan.

    Returns:
    [
        {"label": "Total Sales", "value": 125000.0, "format": "currency"},
        ...
    ]
    """
    kpis_out = []

    for kpi_spec in plan.get("kpis", []):
        label = kpi_spec.get("label", "KPI")
        column = kpi_spec.get("column")
        aggregation = kpi_spec.get("aggregation", "sum")
        fmt = kpi_spec.get("format", "number")

        # Try to find the column in any sheet
        value = None
        for df in sheets.values():
            if column in df.columns:
                value = _aggregate(df[column], aggregation)
                break

        kpis_out.append({
            "label": label,
            "value": value,
            "format": fmt,
        })

    return kpis_out


# ── Private helpers ────────────────────────────────────────────────────────────

def _resolve_sheet(
    sheets: Dict[str, pd.DataFrame], sheet_name: str | None
) -> pd.DataFrame | None:
    """Return the named sheet, or the first sheet if name is missing/wrong."""
    if sheet_name and sheet_name in sheets:
        return sheets[sheet_name]
    if sheets:
        return next(iter(sheets.values()))
    return None


def _build_figure(
    df: pd.DataFrame,
    chart_type: str,
    title: str,
    x_col: str | None,
    y_col: str | None,
    color_col: str | None,
) -> go.Figure:
    """Dispatch to the right Plotly express function."""

    kwargs = dict(
        data_frame=df,
        title=title,
        color_discrete_sequence=_COLOUR_SEQUENCE,
    )
    if x_col:
        kwargs["x"] = x_col
    if y_col:
        kwargs["y"] = y_col
    if color_col:
        kwargs["color"] = color_col

    if chart_type == "line":
        fig = px.line(**kwargs)
    elif chart_type == "bar":
        fig = px.bar(**kwargs)
    elif chart_type == "area":
        fig = px.area(**kwargs)
    elif chart_type == "scatter":
        fig = px.scatter(**kwargs)
    elif chart_type == "pie":
        # Pie uses names/values instead of x/y
        pie_kwargs = dict(
            data_frame=df,
            title=title,
            color_discrete_sequence=_COLOUR_SEQUENCE,
        )
        if x_col:
            pie_kwargs["names"] = x_col
        if y_col:
            pie_kwargs["values"] = y_col
        fig = px.pie(**pie_kwargs)
    elif chart_type == "histogram":
        hist_kwargs = dict(
            data_frame=df,
            title=title,
            color_discrete_sequence=_COLOUR_SEQUENCE,
        )
        if x_col:
            hist_kwargs["x"] = x_col
        if color_col:
            hist_kwargs["color"] = color_col
        fig = px.histogram(**hist_kwargs)
    else:
        # Default fallback → bar chart
        fig = px.bar(**kwargs)

    fig.update_layout(
        template="plotly_white",
        title_font_size=16,
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return fig


def _aggregate(series: pd.Series, method: str) -> Any:
    """Apply a named aggregation to a pandas Series."""
    numeric = pd.to_numeric(series, errors="coerce").dropna()

    if method == "sum":
        return round(float(numeric.sum()), 2)
    elif method == "mean":
        return round(float(numeric.mean()), 2)
    elif method == "count":
        return int(series.count())
    elif method == "max":
        return round(float(numeric.max()), 2)
    elif method == "min":
        return round(float(numeric.min()), 2)
    elif method == "distinct_count":
        return int(series.nunique(dropna=True))
    else:
        return round(float(numeric.sum()), 2)


def _error_figure(title: str, error: str) -> go.Figure:
    """Return a placeholder figure when chart generation fails."""
    fig = go.Figure()
    fig.add_annotation(
        text=f"Could not render chart:<br>{error}",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color="red"),
    )
    fig.update_layout(title=title, template="plotly_white")
    return fig

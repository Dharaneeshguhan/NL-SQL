"""Plotly chart builders for query result visualization."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Brand palette used across the app
PALETTE = ["#7c3aed", "#a855f7", "#14b8a6", "#f97316", "#ec4899", "#6366f1"]


def recommend_chart_type(df: pd.DataFrame) -> dict | None:
    """
    Heuristic chart recommendation from result shape and column types.

    Returns dict with chart_type, x_col, y_col, title — or None if not chartable.
    """
    if df is None or df.empty or len(df.columns) < 2:
        return None

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    text_cols = [c for c in df.columns if c not in numeric_cols]

    if not numeric_cols:
        return None

    y_col = numeric_cols[0]
    x_col = text_cols[0] if text_cols else df.columns[0]

    # Time-like first column → line chart
    x_lower = x_col.lower()
    if any(k in x_lower for k in ("month", "date", "year", "quarter", "period", "time")):
        return {
            "chart_type": "line",
            "x_col": x_col,
            "y_col": y_col,
            "title": f"{y_col.replace('_', ' ').title()} over {x_col.replace('_', ' ').title()}",
        }

    # Small category set with one numeric → bar or pie
    if len(df) <= 8 and text_cols:
        return {
            "chart_type": "bar",
            "x_col": x_col,
            "y_col": y_col,
            "title": f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
        }

    if len(df) <= 6 and text_cols:
        return {
            "chart_type": "pie",
            "x_col": x_col,
            "y_col": y_col,
            "title": f"Share of {y_col.replace('_', ' ').title()}",
        }

    # Two numeric columns → scatter
    if len(numeric_cols) >= 2 and not text_cols:
        return {
            "chart_type": "scatter",
            "x_col": numeric_cols[0],
            "y_col": numeric_cols[1],
            "title": f"{numeric_cols[1]} vs {numeric_cols[0]}",
        }

    return {
        "chart_type": "bar",
        "x_col": x_col,
        "y_col": y_col,
        "title": f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
    }


def build_chart(
    df: pd.DataFrame,
    chart_type: str,
    x_col: str,
    y_col: str,
    title: str,
) -> go.Figure | None:
    """Build a styled Plotly figure from query results."""
    if df.empty or x_col not in df.columns or y_col not in df.columns:
        return None

    builders = {
        "bar": lambda: px.bar(
            df, x=x_col, y=y_col, title=title, color_discrete_sequence=PALETTE
        ),
        "line": lambda: px.line(
            df,
            x=x_col,
            y=y_col,
            title=title,
            markers=True,
            color_discrete_sequence=[PALETTE[0]],
        ),
        "pie": lambda: px.pie(
            df, names=x_col, values=y_col, title=title, color_discrete_sequence=PALETTE
        ),
        "scatter": lambda: px.scatter(
            df, x=x_col, y=y_col, title=title, color_discrete_sequence=[PALETTE[2]]
        ),
    }

    builder = builders.get(chart_type)
    if not builder:
        return None

    fig = builder()
    fig.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#faf5ff",
        font_color="#374151",
        title_font_color="#7c3aed",
        title_font_size=15,
        xaxis=dict(gridcolor="#f3e8ff", tickfont_color="#6b7280"),
        yaxis=dict(gridcolor="#f3e8ff", tickfont_color="#6b7280"),
        margin=dict(l=48, r=24, t=56, b=48),
        height=400,
    )
    return fig

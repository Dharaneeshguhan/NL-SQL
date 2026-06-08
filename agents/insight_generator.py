"""Steps 6–7 — Analyze query results and recommend visualizations."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from agents.llm_client import LLMClient
from utils.charts import recommend_chart_type

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "insight_prompt.txt"

SYSTEM = (
    "You are a business analyst. Respond with valid JSON only — no markdown fences."
)


def load_insight_prompt(question: str, sql: str, df: pd.DataFrame) -> str:
    """Build insight prompt with truncated result set."""
    preview = df.head(50).to_json(orient="records", date_format="iso")
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.format(question=question, sql=sql, results=preview)


def generate_insights(
    question: str,
    sql: str,
    df: pd.DataFrame,
    llm: LLMClient,
) -> dict:
    """
    Produce business insights and chart recommendation.

    Falls back to heuristic chart recommendation if LLM JSON parsing fails.
    """
    if df.empty:
        return {
            "summary": "The query returned no rows. Try broadening filters or check date ranges.",
            "key_findings": ["No data matched the query criteria."],
            "chart_type": None,
            "chart_x": None,
            "chart_y": None,
            "chart_title": None,
        }

    prompt = load_insight_prompt(question, sql, df)

    try:
        raw = llm.generate(prompt, system=SYSTEM, max_tokens=768)
        parsed = _normalize_insights(_parse_json(raw), df)
    except Exception:
        parsed = _fallback_insights(df)

    # Merge heuristic chart hint when LLM omits chart fields
    if not parsed.get("chart_type"):
        heuristic = recommend_chart_type(df)
        if heuristic:
            parsed.update(
                {
                    "chart_type": heuristic["chart_type"],
                    "chart_x": heuristic["x_col"],
                    "chart_y": heuristic["y_col"],
                    "chart_title": heuristic["title"],
                }
            )

    return parsed


def _parse_json(text: str) -> dict:
    cleaned = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group())
        raise


def _fallback_insights(df: pd.DataFrame) -> dict:
    """Rule-based fallback when LLM is unavailable or returns invalid JSON."""
    heuristic = recommend_chart_type(df)
    summary = f"Query returned {len(df)} row(s) with columns: {', '.join(df.columns)}."

    findings: list[str] = []
    numeric = df.select_dtypes(include="number").columns
    if len(numeric) > 0:
        col = numeric[0]
        findings.append(f"{col}: min={df[col].min()}, max={df[col].max()}, avg={df[col].mean():.2f}")

    result = {
        "summary": summary,
        "key_findings": findings or ["Review the table for detailed values."],
        "chart_type": None,
        "chart_x": None,
        "chart_y": None,
        "chart_title": None,
    }
    if heuristic:
        result.update(
            {
                "chart_type": heuristic["chart_type"],
                "chart_x": heuristic["x_col"],
                "chart_y": heuristic["y_col"],
                "chart_title": heuristic["title"],
            }
        )
    return result


def _normalize_insights(parsed: dict, df: pd.DataFrame) -> dict:
    """Ensure optional LLM fields always exist and point at result columns."""
    result = {
        "summary": parsed.get("summary") or "Here are your results.",
        "key_findings": parsed.get("key_findings") or [],
        "chart_type": parsed.get("chart_type"),
        "chart_x": parsed.get("chart_x") or parsed.get("x_col"),
        "chart_y": parsed.get("chart_y") or parsed.get("y_col"),
        "chart_title": parsed.get("chart_title") or parsed.get("title"),
    }

    if result["chart_x"] not in df.columns or result["chart_y"] not in df.columns:
        result["chart_type"] = None
        result["chart_x"] = None
        result["chart_y"] = None
        result["chart_title"] = None

    if isinstance(result["key_findings"], str):
        result["key_findings"] = [result["key_findings"]]

    return result

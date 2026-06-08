"""Regression tests for insight generation fallbacks."""

from __future__ import annotations

import pandas as pd

from agents.insight_generator import generate_insights


class DummyLLM:
    def __init__(self, response: str):
        self.response = response

    def generate(self, *args, **kwargs) -> str:
        return self.response


def test_missing_chart_fields_falls_back_to_heuristic():
    df = pd.DataFrame(
        [{"product_name": "Laptop Pro 15", "total_sales_rs": 181_999.50}]
    )
    llm = DummyLLM(
        """
        {
          "summary": "Laptop Pro 15 has the top sales.",
          "key_findings": ["Laptop Pro 15 leads revenue"],
          "chart_type": null
        }
        """
    )

    insights = generate_insights("top sales", "SELECT ...", df, llm)

    assert insights["summary"] == "Laptop Pro 15 has the top sales."
    assert insights["chart_type"] == "bar"
    assert insights["chart_x"] == "product_name"
    assert insights["chart_y"] == "total_sales_rs"


def test_invalid_insight_json_uses_safe_fallback():
    df = pd.DataFrame(
        [{"product_name": "Laptop Pro 15", "total_sales_rs": 181_999.50}]
    )
    insights = generate_insights("top sales", "SELECT ...", df, DummyLLM("not json"))

    assert insights["chart_type"] == "bar"
    assert insights["chart_x"] == "product_name"
    assert insights["chart_y"] == "total_sales_rs"

"""Tests for local SQL explanations."""

from __future__ import annotations

from utils.sql_explainer import explain_sql_locally


def test_explain_top_sales_query():
    sql = """
        SELECT p.name AS product_name, ROUND(SUM(s.total_amount), 2) AS total_sales_rs
        FROM sales s
        JOIN products p ON s.product_id = p.id
        GROUP BY p.id, p.name
        ORDER BY total_sales_rs DESC
        LIMIT 1
    """

    explanation = explain_sql_locally(sql)

    assert "product_name" in explanation
    assert "total_sales_rs" in explanation
    assert "`sales`" in explanation
    assert "`products`" in explanation
    assert "groups" in explanation
    assert "first 1 row" in explanation

"""Tests for INR formatting utilities."""

from __future__ import annotations

import pandas as pd

from utils.formatting import format_dataframe_for_display, format_inr, format_number


class TestFormatting:
    def test_format_inr(self):
        assert format_inr(129999) == "Rs 129,999.00"
        assert format_inr(0) == "Rs 0.00"
        assert format_inr(None) == "Rs 0"

    def test_format_number(self):
        assert format_number(1500) == "1,500"
        assert format_number(1234.56, decimals=2) == "1,234.56"

    def test_format_dataframe_currency_columns(self):
        df = pd.DataFrame(
            {
                "product": ["Laptop"],
                "total_sales": [259998.0],
                "quantity": [2],
            }
        )
        out = format_dataframe_for_display(df)
        assert out["total_sales"].iloc[0] == "Rs 259,998.00"
        assert out["quantity"].iloc[0] == 2

    def test_csv_bytes_roundtrip(self):
        from utils.formatting import dataframe_to_csv_bytes

        df = pd.DataFrame({"a": [1, 2]})
        raw = dataframe_to_csv_bytes(df)
        text = raw.decode("utf-8")
        assert "a" in text and "1" in text and "2" in text

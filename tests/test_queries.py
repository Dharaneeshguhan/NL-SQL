"""Tests for SQL validation and database queries (no LLM required)."""

from __future__ import annotations

import pandas as pd
import pytest

from agents.sql_validator import validate_sql
from utils.database import execute_query, init_db, is_read_only_sql, list_tables


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db(force=True)


class TestSQLValidator:
    def test_valid_select(self):
        result = validate_sql("SELECT * FROM sales LIMIT 10")
        assert result.valid
        assert "SELECT" in result.sanitized_sql.upper()

    def test_valid_with_cte(self):
        sql = "WITH t AS (SELECT 1 AS x) SELECT x FROM t"
        assert validate_sql(sql).valid

    def test_blocks_delete(self):
        assert not validate_sql("DELETE FROM sales").valid

    def test_blocks_drop(self):
        assert not validate_sql("DROP TABLE sales").valid

    def test_blocks_update(self):
        assert not validate_sql("UPDATE sales SET total_amount = 0").valid

    def test_blocks_insert(self):
        assert not validate_sql("INSERT INTO sales VALUES (99,1,1,'2024-01-01',1,100)").valid

    def test_blocks_alter(self):
        assert not validate_sql("ALTER TABLE sales ADD COLUMN x INT").valid

    def test_blocks_truncate(self):
        assert not validate_sql("TRUNCATE TABLE sales").valid

    def test_blocks_multiple_statements(self):
        assert not validate_sql("SELECT 1; DROP TABLE sales").valid

    def test_strips_markdown_fences(self):
        sql = "```sql\nSELECT COUNT(*) FROM employees\n```"
        result = validate_sql(sql)
        assert result.valid
        assert "```" not in result.sanitized_sql


class TestDatabase:
    def test_tables_exist(self):
        tables = set(list_tables())
        assert {"departments", "employees", "products", "sales"}.issubset(tables)

    def test_read_only_helper(self):
        assert is_read_only_sql("SELECT 1")
        assert not is_read_only_sql("DELETE FROM sales")

    def test_total_sales_by_month(self):
        sql = """
            SELECT strftime('%Y-%m', sale_date) AS month,
                   ROUND(SUM(total_amount), 2) AS total_sales
            FROM sales
            GROUP BY month
            ORDER BY month
        """
        df, err = execute_query(sql)
        assert err is None
        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 1
        assert "month" in df.columns
        assert "total_sales" in df.columns

    def test_highest_product_sales(self):
        sql = """
            SELECT p.name AS product_name,
                   ROUND(SUM(s.total_amount), 2) AS total_sales
            FROM sales s
            JOIN products p ON s.product_id = p.id
            GROUP BY p.id, p.name
            ORDER BY total_sales DESC
            LIMIT 1
        """
        df, err = execute_query(sql)
        assert err is None
        assert len(df) == 1
        assert df.iloc[0]["total_sales"] > 0

    def test_employee_count_by_department(self):
        sql = """
            SELECT d.name AS department, COUNT(e.id) AS employee_count
            FROM departments d
            LEFT JOIN employees e ON d.id = e.department_id
            GROUP BY d.id, d.name
            ORDER BY employee_count DESC
        """
        df, err = execute_query(sql)
        assert err is None
        assert len(df) == 5
        assert df["employee_count"].sum() == 15

    def test_blocks_mutating_query(self):
        df, err = execute_query("DELETE FROM sales")
        assert df is None
        assert err is not None

    def test_tamil_employee_names(self):
        sql = "SELECT name FROM employees ORDER BY id"
        df, err = execute_query(sql)
        assert err is None
        names = df["name"].tolist()
        assert "Dhana" in names
        assert "Priya" in names
        assert "Dharshini" in names
        assert "Alice" not in names

    def test_low_stock_products_query(self):
        sql = """
            SELECT name AS product_name, category, stock_quantity
            FROM products
            WHERE stock_quantity < 20
            ORDER BY stock_quantity ASC, name ASC
        """
        df, err = execute_query(sql)
        assert err is None
        assert len(df) >= 1
        assert (df["stock_quantity"] < 20).all()

    def test_priya_sales_query(self):
        sql = """
            SELECT COUNT(*) AS sale_count
            FROM sales s
            JOIN employees e ON s.employee_id = e.id
            WHERE e.name = 'Priya'
        """
        df, err = execute_query(sql)
        assert err is None
        assert df.iloc[0]["sale_count"] > 0

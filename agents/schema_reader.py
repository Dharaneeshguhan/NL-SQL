"""Step 1 — Read and format the SQLite database schema for the LLM."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from utils.database import DB_PATH, list_tables, is_uploaded_table

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_schema(include_samples: bool = True, sample_rows: int = 3) -> str:
    """
    Build a human-readable schema document from sqlite_master and PRAGMA.

    Includes column types, primary keys, foreign keys, row counts, and optional samples.
    Uploaded tables are marked with [USER-UPLOADED] notation.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. Run init_db() first."
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    lines: list[str] = ["# SQLite Database Schema", ""]

    try:
        tables = list_tables()
        
        # Separate uploaded and built-in tables
        uploaded_tables = [t for t in tables if is_uploaded_table(t)]
        builtin_tables = [t for t in tables if not is_uploaded_table(t)]
        
        # Process built-in tables first
        for table in builtin_tables:
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({table})")
            columns = cur.fetchall()

            cur.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cur.fetchone()[0]

            lines.append(f"## Table: {table} ({row_count} rows)")
            lines.append("Columns:")
            for col in columns:
                cid, name, col_type, notnull, default, pk = col
                flags = []
                if pk:
                    flags.append("PRIMARY KEY")
                if notnull:
                    flags.append("NOT NULL")
                flag_str = f" [{', '.join(flags)}]" if flags else ""
                lines.append(f"  - {name} ({col_type}){flag_str}")

            # Foreign keys
            cur.execute(f"PRAGMA foreign_key_list({table})")
            fks = cur.fetchall()
            if fks:
                lines.append("Foreign keys:")
                for fk in fks:
                    lines.append(
                        f"  - {fk[3]} → {fk[2]}.{fk[4]}"
                    )

            if include_samples and row_count > 0:
                cur.execute(f"SELECT * FROM {table} LIMIT {sample_rows}")
                samples = cur.fetchall()
                col_names = [c[1] for c in columns]
                lines.append("Sample rows:")
                for row in samples:
                    row_dict = dict(zip(col_names, row))
                    lines.append(f"  {row_dict}")

            lines.append("")

        # Process uploaded tables with special notation
        if uploaded_tables:
            lines.append("## User-Uploaded Tables [TEMPORARY SESSION DATA]")
            lines.append("")
            
            for table in uploaded_tables:
                cur = conn.cursor()
                cur.execute(f"PRAGMA table_info({table})")
                columns = cur.fetchall()

                cur.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cur.fetchone()[0]
                
                lines.append(f"### Table: {table} ({row_count} rows) [USER-UPLOADED]")
                lines.append("Columns:")
                for col in columns:
                    cid, name, col_type, notnull, default, pk = col
                    flags = []
                    if pk:
                        flags.append("PRIMARY KEY")
                    if notnull:
                        flags.append("NOT NULL")
                    flag_str = f" [{', '.join(flags)}]" if flags else ""
                    lines.append(f"  - {name} ({col_type}){flag_str}")

                if include_samples and row_count > 0:
                    cur.execute(f"SELECT * FROM {table} LIMIT {sample_rows}")
                    samples = cur.fetchall()
                    col_names = [c[1] for c in columns]
                    lines.append("Sample rows:")
                    for row in samples:
                        row_dict = dict(zip(col_names, row))
                        lines.append(f"  {row_dict}")

                lines.append("")

        # Relationship hints for common analytics joins
        lines.extend(
            [
                "## Join hints",
                "- sales.product_id → products.id",
                "- sales.employee_id → employees.id",
                "- employees.department_id → departments.id",
                "- orders.customer_id → customers.id",
                "- order_items.order_id → orders.id",
                "- order_items.product_id → products.id",
                "- sale_date is ISO format YYYY-MM-DD; use strftime for month/year grouping",
                "- order_date is ISO format YYYY-MM-DD; use strftime for month/year grouping",
            ]
        )
    finally:
        conn.close()

    return "\n".join(lines)


def get_schema_summary() -> dict:
    """Structured schema metadata for programmatic use."""
    summary: dict = {"tables": {}}
    conn = sqlite3.connect(DB_PATH)
    try:
        for table in list_tables():
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({table})")
            cols = [{"name": r[1], "type": r[2], "pk": bool(r[5])} for r in cur.fetchall()]
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            summary["tables"][table] = {"columns": cols, "row_count": count}
    finally:
        conn.close()
    return summary

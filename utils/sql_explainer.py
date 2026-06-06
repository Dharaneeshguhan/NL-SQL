"""Plain-English SQL explanation helpers."""

from __future__ import annotations

import re


def explain_sql_locally(sql: str) -> str:
    """Create a concise explanation without calling an LLM."""
    cleaned = " ".join(sql.strip().rstrip(";").split())
    if not cleaned:
        return "No SQL query was available to explain."

    parts: list[str] = []
    select_part = _section(cleaned, "SELECT", ["FROM"])
    from_part = _section(cleaned, "FROM", ["WHERE", "GROUP BY", "ORDER BY", "LIMIT"])
    where_part = _section(cleaned, "WHERE", ["GROUP BY", "ORDER BY", "LIMIT"])
    group_part = _section(cleaned, "GROUP BY", ["ORDER BY", "LIMIT"])
    order_part = _section(cleaned, "ORDER BY", ["LIMIT"])
    limit_part = _section(cleaned, "LIMIT", [])

    if select_part:
        parts.append(f"It returns { _plain_columns(select_part) }.")
    if from_part:
        parts.append(f"It reads data from { _plain_sources(from_part) }.")
    if where_part:
        parts.append(f"It filters rows where `{where_part}`.")
    if group_part:
        parts.append(f"It groups the result by `{group_part}`.")
    if order_part:
        parts.append(f"It sorts the result by `{order_part}`.")
    if limit_part:
        parts.append(f"It only shows the first {limit_part} row(s).")

    return " ".join(parts) or f"This is a read-only SQL query: `{cleaned}`"


def _section(sql: str, start: str, stops: list[str]) -> str:
    stop_pattern = "|".join(re.escape(stop) for stop in stops)
    if stop_pattern:
        pattern = rf"\b{re.escape(start)}\b\s+(.*?)(?=\b(?:{stop_pattern})\b|$)"
    else:
        pattern = rf"\b{re.escape(start)}\b\s+(.*)$"
    match = re.search(pattern, sql, flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _plain_columns(select_part: str) -> str:
    columns = []
    for item in _split_top_level(select_part):
        alias_match = re.search(r"\bAS\s+([a-zA-Z_][a-zA-Z0-9_]*)$", item, re.IGNORECASE)
        if alias_match:
            columns.append(f"`{alias_match.group(1)}`")
        else:
            columns.append(f"`{item}`")
    return ", ".join(columns)


def _plain_sources(from_part: str) -> str:
    tables = re.findall(
        r"(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+[a-zA-Z_][a-zA-Z0-9_]*)?",
        f"FROM {from_part}",
        flags=re.IGNORECASE,
    )
    if not tables:
        return f"`{from_part}`"
    unique_tables = list(dict.fromkeys(tables))
    return ", ".join(f"`{table}`" for table in unique_tables)


def _split_top_level(text: str) -> list[str]:
    items: list[str] = []
    depth = 0
    start = 0
    for idx, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            items.append(text[start:idx].strip())
            start = idx + 1
    items.append(text[start:].strip())
    return [item for item in items if item]

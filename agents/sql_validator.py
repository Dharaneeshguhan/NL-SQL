"""Step 4 — Validate generated SQL before execution (read-only enforcement)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from utils.database import is_read_only_sql

# Explicit blocklist per security requirements
BLOCKED = frozenset(
    {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "REPLACE"}
)

# Detect multiple statements (semicolon-separated) — only one allowed
_MULTI_STATEMENT = re.compile(r";\s*\S", re.DOTALL)

# Basic SQL injection patterns in literals (defense in depth)
_SUSPICIOUS = re.compile(
    r"(--|/\*|\*/|;\s*(DROP|DELETE|UPDATE|INSERT)|xp_|exec\s*\()",
    re.IGNORECASE,
)


@dataclass
class ValidationResult:
    valid: bool
    message: str
    sanitized_sql: str = ""


def validate_sql(sql: str) -> ValidationResult:
    """
    Validate LLM-generated SQL for safety and basic correctness.

    Rules:
    - Must be non-empty
    - Only SELECT / WITH allowed
    - Block DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE
    - Single statement only
    - Strip markdown fences if present
    """
    if not sql or not sql.strip():
        return ValidationResult(False, "SQL query is empty.")

    cleaned = _clean_sql(sql)

    if _MULTI_STATEMENT.search(cleaned):
        return ValidationResult(False, "Multiple SQL statements are not allowed.")

    if _SUSPICIOUS.search(cleaned):
        return ValidationResult(False, "Query contains suspicious patterns and was blocked.")

    # Check explicit blocked keywords
    upper = cleaned.upper()
    for keyword in BLOCKED:
        if re.search(rf"\b{keyword}\b", upper):
            return ValidationResult(
                False,
                f"Blocked keyword '{keyword}' detected. Only SELECT queries are permitted.",
            )

    if not is_read_only_sql(cleaned):
        return ValidationResult(
            False,
            "Query must start with SELECT or WITH and contain no mutating statements.",
        )

    # Must have FROM for SELECT (simple sanity check)
    if upper.lstrip().startswith("SELECT") and "FROM" not in upper:
        return ValidationResult(False, "SELECT query must include a FROM clause.")

    return ValidationResult(True, "SQL validation passed.", sanitized_sql=cleaned)


def _clean_sql(sql: str) -> str:
    """Remove markdown code fences and trailing semicolons."""
    text = sql.strip()
    text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip().rstrip(";")

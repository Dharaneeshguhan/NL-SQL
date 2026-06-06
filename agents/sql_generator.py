"""Steps 2–3 — Understand the question and generate SQL via LLM."""

from __future__ import annotations

import re
from pathlib import Path

from agents.llm_client import LLMClient

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "sql_prompt.txt"

SYSTEM = (
    "You are a SQLite SQL generator. Output only valid read-only SQL. "
    "Never include markdown, comments, or explanations."
)


def load_sql_prompt(schema: str, question: str) -> str:
    """Load and fill the SQL generation prompt template."""
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return template.format(schema=schema, question=question.strip())


def generate_sql(
    question: str,
    schema: str,
    llm: LLMClient,
) -> tuple[str, str]:
    """
    Generate SQL from natural language.

    Returns (sql, understanding_note) where understanding_note summarizes intent.
    """
    prompt = load_sql_prompt(schema, question)
    raw = llm.generate(prompt, system=SYSTEM, max_tokens=512)
    sql = extract_sql(raw)

    # Step 2: brief understanding (derived from question for agent trace)
    understanding = f"Analyzing: {question.strip()}"
    return sql, understanding


def extract_sql(text: str) -> str:
    """Pull SQL from model output, stripping fences and prose."""
    cleaned = text.strip()

    # Markdown code block
    block = re.search(r"```(?:sql)?\s*(.*?)```", cleaned, re.DOTALL | re.IGNORECASE)
    if block:
        cleaned = block.group(1).strip()

    # Take first SELECT/WITH statement if model added explanation
    match = re.search(
        r"((?:WITH\b[\s\S]*?)?SELECT\b[\s\S]*)",
        cleaned,
        re.IGNORECASE,
    )
    if match:
        cleaned = match.group(1).strip()

    # Remove trailing semicolon and whitespace
    return cleaned.rstrip(";").strip()

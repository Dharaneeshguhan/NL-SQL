"""Schema-grounded text-to-SQL agent via OpenRouter (OpenAI-compatible tools)."""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

import httpx
from openai import APIStatusError, OpenAI

from database import describe_table, list_tables, run_query

# Windows: avoid ascii codec errors on API requests / error messages
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")

_MODEL_ALIASES = {
    "google/gemini-2.0-flash-001": "google/gemini-2.5-flash",
    "google/gemini-2.0-flash": "google/gemini-2.5-flash",
    "google/gemini-flash-1.5-8b": "google/gemini-2.5-flash-lite",
}

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "List all tables in the SQLite database.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_table",
            "description": "Get column definitions, row count, and sample rows for a table.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table",
                    },
                },
                "required": ["table_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": (
                "Execute a read-only SELECT query and return JSON rows (max 500). "
                "Use to validate SQL before finalizing your answer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "Read-only SQLite SELECT",
                    },
                },
                "required": ["sql"],
            },
        },
    },
]

SYSTEM = """You are a schema-grounded analytics agent for a SQLite warehouse.

Workflow:
1. Use list_tables and describe_table to understand the schema before writing SQL.
2. Draft SQL, optionally test with run_sql.
3. When ready, respond with ONLY a JSON object (no markdown fences):

{
  "answer": "Clear 1-3 sentence business answer",
  "sql": "The final SELECT you recommend",
  "chart_type": "bar" | "line" | "pie" | "scatter" | null,
  "chart_x": "column for categories or time",
  "chart_y": "numeric column",
  "chart_title": "short title"
}

Rules:
- SQL must be read-only (SELECT / WITH only).
- Join tables correctly using foreign keys.
- Prefer meaningful aliases and aggregations.
- Suggest a chart only when it helps (bar: categories, line: time, pie: share, scatter: correlation).
- Do not use emoji in the answer text.
"""


def resolve_model(model: str | None) -> str:
    mid = (model or DEFAULT_MODEL).strip()
    return _MODEL_ALIASES.get(mid, mid)


def _ascii_header(value: str) -> str:
    """HTTP headers must be ASCII; strip anything else (Windows-safe)."""
    return value.encode("ascii", errors="ignore").decode("ascii")


def _client(api_key: str) -> OpenAI:
    return OpenAI(
        base_url=OPENROUTER_BASE,
        api_key=api_key.strip(),
        default_headers={
            "HTTP-Referer": _ascii_header(
                os.environ.get("OPENROUTER_REFERER", "http://localhost:8501")
            ),
            "X-Title": "NL-to-SQL Analytics Agent",
        },
        http_client=httpx.Client(timeout=httpx.Timeout(120.0)),
    )


def _format_api_error(model_id: str, exc: Exception) -> str:
    if isinstance(exc, APIStatusError):
        body = exc.body
        if isinstance(body, dict):
            err = body.get("error", body)
            if isinstance(err, dict):
                msg = err.get("message") or err.get("metadata", {}).get("raw", "")
                if msg:
                    return f"OpenRouter ({model_id}): {msg}"
        return f"OpenRouter ({model_id}): HTTP {exc.status_code}"
    if isinstance(exc, UnicodeEncodeError):
        return (
            f"OpenRouter ({model_id}): text encoding failed on Windows. "
            "Restart the app and try again without emoji in your question."
        )
    return f"OpenRouter ({model_id}): {exc!r}"


def _run_tool(name: str, inputs: dict) -> str:
    if name == "list_tables":
        return json.dumps(list_tables(), ensure_ascii=False)
    if name == "describe_table":
        return describe_table(inputs.get("table_name", ""))
    if name == "run_sql":
        df, err = run_query(inputs.get("sql", ""))
        if err:
            return json.dumps({"error": err}, ensure_ascii=False)
        return df.to_json(orient="records", date_format="iso")
    return json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)


def _parse_final(text: str) -> dict:
    cleaned = re.sub(r"```json|```", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Model did not return valid JSON. Raw output:\n{text[:500]}")


def _assistant_tool_message(assistant: Any, tool_calls: list) -> dict:
    return {
        "role": "assistant",
        "content": assistant.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments or "{}",
                },
            }
            for tc in tool_calls
        ],
    }


def run_analytics_agent(
    question: str,
    api_key: str,
    model: str | None = None,
    max_turns: int = 12,
) -> dict:
    client = _client(api_key)
    model_id = resolve_model(model)
    # Plain text only in API payload (no emoji from UI paste)
    clean_question = question.strip()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": clean_question},
    ]
    tool_trace: list[dict] = []

    for _ in range(max_turns):
        try:
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=2048,
            )
        except Exception as exc:
            raise RuntimeError(_format_api_error(model_id, exc)) from exc

        choice = response.choices[0]
        assistant = choice.message
        tool_calls = assistant.tool_calls or []

        if tool_calls:
            messages.append(_assistant_tool_message(assistant, tool_calls))
            for tc in tool_calls:
                fn = tc.function
                try:
                    args = json.loads(fn.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                output = _run_tool(fn.name, args)
                tool_trace.append(
                    {"tool": fn.name, "input": args, "preview": output[:400]}
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": output,
                    }
                )
            continue

        text = (assistant.content or "").strip()
        if not text:
            raise RuntimeError(
                f"Empty response from {model_id}. "
                "Try google/gemini-2.5-flash or meta-llama/llama-3.3-70b-instruct:free."
            )
        return {"result": _parse_final(text), "tool_trace": tool_trace}

    raise RuntimeError("Agent exceeded maximum tool turns without a final answer.")

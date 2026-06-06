# AI Usage Documentation

This document describes how AI assisted in building the NL-to-SQL Analytics Agent, including prompts, corrections, and design decisions.

## What AI helped with

| Area | AI contribution |
|------|-----------------|
| Project scaffolding | Full folder structure, module boundaries, and agent loop design |
| Prompt engineering | SQL and insight prompt templates in `prompts/` |
| Security layer | SQL validator blocklist, read-only connection pattern, single-statement checks |
| Streamlit UI | Layout, styling, sidebar provider toggle, chat history |
| Sample data | CSV schemas and seed rows for departments, employees, products, sales |
| Tests | pytest suite for validator and three canonical example queries |
| Documentation | README setup instructions and this file |

## Prompts used

### SQL generation (`prompts/sql_prompt.txt`)

The SQL prompt includes:

- Full database schema placeholder `{schema}`
- User question placeholder `{question}`
- Strict rules: SELECT only, correct joins, `strftime` for dates
- Three few-shot examples matching project requirements:
  - Total sales by month
  - Highest-selling product
  - Employee count by department

System message (in `sql_generator.py`):

```
You are a SQLite SQL generator. Output only valid read-only SQL.
Never include markdown, comments, or explanations.
```

### Insight generation (`prompts/insight_prompt.txt`)

The insight prompt includes:

- Question, SQL, and JSON result preview
- Required JSON output schema: `summary`, `key_findings`, chart fields
- Chart type guidance (bar, line, pie, scatter, null)

System message (in `insight_generator.py`):

```
You are a business analyst. Respond with valid JSON only — no markdown fences.
```

### Agent loop design prompt (conceptual)

The 7-step pipeline was specified as:

1. Read database schema
2. Understand user question
3. Generate SQL
4. Validate SQL
5. Execute SQL
6. Analyze result
7. Recommend visualization

Each step maps to a dedicated module except steps 2–3 (combined in `sql_generator.py`) and steps 6–7 (combined in `insight_generator.py` with heuristic fallback).

## AI mistakes and corrections

### 1. Markdown-wrapped SQL

**Mistake:** Llama3 often wraps SQL in ` ```sql ` fences or adds explanatory text before/after the query.

**Correction:** Added `extract_sql()` in `sql_generator.py` and `_clean_sql()` in `sql_validator.py` to strip fences and extract the first SELECT/WITH statement.

### 2. Mutating SQL suggestions

**Mistake:** Models occasionally suggest `CREATE TEMP TABLE` or multiple statements.

**Correction:** `sql_validator.py` blocks CREATE, ALTER, TRUNCATE, and semicolon-separated multi-statements. `utils/database.py` opens read-only connections for execution.

### 3. Invalid JSON from insight model

**Mistake:** Insight responses sometimes include markdown or truncated JSON.

**Correction:** `_parse_json()` with regex fallback; `_fallback_insights()` uses pandas heuristics and `recommend_chart_type()` when LLM parsing fails.

### 4. Wrong chart column names

**Mistake:** LLM chart_x/chart_y did not always match actual result column names.

**Correction:** Insight prompt instructs to use exact column names; `build_chart()` validates columns exist; heuristic recommender uses actual DataFrame dtypes.

### 5. Ollama connection errors on Windows

**Mistake:** Generic httpx errors when Ollama is not running.

**Correction:** `LLMClient.is_available()` health check and clear message: "Start Ollama and run: ollama pull llama3".

### 6. OpenRouter without API key

**Mistake:** App attempted cloud calls with empty key.

**Correction:** Sidebar key input, `OPENROUTER_API_KEY` env support, and validation before running the agent loop.

## Human review checklist

- [x] SELECT-only enforcement tested in `tests/test_queries.py`
- [x] Sample queries match README examples
- [x] Both Ollama and OpenRouter paths implemented
- [x] Agent loop steps visible in UI expander
- [x] Production comments in all Python modules

## Tools and models

- **Cursor AI** — code generation, refactoring, documentation
- **Ollama llama3** — local SQL and insight generation
- **OpenRouter** — cloud fallback (`meta-llama/llama-3.3-70b-instruct:free`, Gemini, etc.)

## Iteration notes

Future improvements identified during AI-assisted development:

1. SQL retry loop: if validation or execution fails, feed error back to LLM for correction
2. Schema caching to avoid re-reading on every question
3. Query result caching for repeated questions
4. Stronger SQL parsing (e.g. `sqlparse`) instead of regex-only validation

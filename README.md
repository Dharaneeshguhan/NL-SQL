# NL-to-SQL Analytics Agent

Streamlit app that lets business users ask analytics questions in plain English. A schema-grounded agent uses tools to inspect SQLite, generates read-only SQL, runs it, and returns the answer, the SQL used, and a chart when appropriate.

**LLM:** [OpenRouter](https://openrouter.ai) — one API key, many models (including free options).

## Features

- **Natural language questions** — no SQL required
- **Tool-using agent** — `list_tables`, `describe_table`, `run_sql` before answering
- **Read-only SQLite** — sample e-commerce warehouse
- **Light modern UI** — violet & teal theme, KPI cards, Plotly charts
- **Voice-to-SQL support** — speak questions and get SQL + dashboard results
- **Query history** — access previous questions and reuse them quickly
- **Export results** — download query results as PDF or Excel
- **SQL explanation** — inspect generated SQL with a plain-English explanation

## Setup

```bash
cd Infinite
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

1. Create an API key at [openrouter.ai/keys](https://openrouter.ai/keys)
2. Set it:

```bash
set OPENROUTER_API_KEY=sk-or-v1-...
```

For Windows voice input, install PyAudio with `pipwin` if needed:

```bash
pip install pipwin
pipwin install pyaudio
```

Optional default model:

```bash
set OPENROUTER_MODEL=google/gemini-2.5-flash
```

## Run

```bash
streamlit run app.py
```

In the sidebar, choose a model. Default **`google/gemini-2.5-flash`** is recommended for tool calling. Free options include `meta-llama/llama-3.3-70b-instruct:free`.

## Example questions

- Top 5 customers by revenue
- Monthly sales trend in 2024
- Revenue by product category

## Project structure

| File | Role |
|------|------|
| `app.py` | Streamlit UI |
| `agent.py` | OpenRouter agent with schema tools |
| `database.py` | Sample DB seed + read-only queries |

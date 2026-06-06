"""NL-to-SQL Analytics Agent — Streamlit UI."""

import os
import sys

# UTF-8 on Windows (prevents ascii codec errors with API / unicode text)
if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")

import pandas as pd
import plotly.express as px
import streamlit as st

from agent import resolve_model, run_analytics_agent
from database import init_db, kpi_metrics, run_query, get_table_info

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NL-to-SQL Analytics Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; color: #1e1b4b; }
    .stApp {
        background: linear-gradient(165deg, #fff7ed 0%, #fdf4ff 40%, #f0fdfa 100%);
    }
    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e9d5ff;
        box-shadow: 4px 0 24px rgba(124, 58, 237, 0.06);
    }
    [data-testid="stSidebar"] .stMarkdown h2 {
        color: #7c3aed !important;
        font-weight: 700;
    }
    [data-testid="stSidebar"] .stCaption { color: #6b7280; }

    .hero {
        background: linear-gradient(120deg, #7c3aed 0%, #a855f7 45%, #14b8a6 100%);
        border-radius: 20px;
        padding: 32px 36px;
        margin-bottom: 28px;
        box-shadow: 0 12px 40px rgba(124, 58, 237, 0.25);
        position: relative;
        overflow: hidden;
    }
    .hero::after {
        content: '';
        position: absolute; right: -20px; top: -20px;
        width: 200px; height: 200px;
        background: rgba(255,255,255,0.12);
        border-radius: 50%;
    }
    .hero h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.02em;
    }
    .hero p { color: rgba(255,255,255,0.92); margin: 10px 0 0; font-size: 1.05rem; max-width: 640px; }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e9d5ff;
        border-radius: 16px;
        padding: 18px 22px;
        box-shadow: 0 4px 20px rgba(124, 58, 237, 0.08);
    }
    div[data-testid="stMetric"] label { color: #6b7280 !important; font-weight: 500; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #7c3aed !important;
        font-weight: 700;
    }

    .bubble-tag {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        opacity: 0.85;
        margin-right: 6px;
    }
    .user-bubble {
        background: linear-gradient(135deg, #7c3aed, #a855f7);
        color: #ffffff;
        padding: 14px 20px;
        border-radius: 20px 20px 4px 20px;
        margin: 10px 0 10px 40px;
        font-size: 0.95rem;
        line-height: 1.55;
        box-shadow: 0 6px 20px rgba(124, 58, 237, 0.25);
    }
    .assistant-bubble {
        background: #ffffff;
        color: #374151;
        padding: 14px 20px;
        border-radius: 20px 20px 20px 4px;
        margin: 10px 40px 10px 0;
        font-size: 0.95rem;
        line-height: 1.55;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
    }
    .assistant-bubble .bubble-tag { color: #7c3aed; opacity: 1; }
    .sql-label {
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #9ca3af;
        margin: 14px 0 6px;
        font-weight: 600;
    }
    .sql-block {
        background: #1e1b4b;
        border-left: 4px solid #14b8a6;
        border-radius: 10px;
        padding: 14px 18px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: #5eead4;
        white-space: pre-wrap;
        word-break: break-word;
    }
    .tool-pill {
        display: inline-block;
        background: #f3e8ff;
        border: 1px solid #d8b4fe;
        border-radius: 999px;
        padding: 3px 12px;
        font-size: 0.72rem;
        color: #6b21a8;
        margin: 2px 6px 2px 0;
        font-weight: 500;
    }
    .stTextInput input, .stSelectbox > div > div {
        background: #ffffff !important;
        border: 1px solid #d8b4fe !important;
        border-radius: 12px !important;
        color: #1e1b4b !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #7c3aed, #14b8a6) !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        color: white !important;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(124, 58, 237, 0.35) !important;
    }
    hr { border-color: #e9d5ff !important; }
    [data-testid="stDataFrame"] { border-radius: 12px; border: 1px solid #e5e7eb; }
</style>
""",
    unsafe_allow_html=True,
)


def make_chart(df: pd.DataFrame, chart_type: str, x_col: str, y_col: str, title: str):
    if not chart_type or x_col not in df.columns or y_col not in df.columns:
        return None
    palette = ["#7c3aed", "#a855f7", "#14b8a6", "#f97316", "#ec4899"]
    builders = {
        "bar": lambda: px.bar(df, x=x_col, y=y_col, title=title, color_discrete_sequence=palette),
        "line": lambda: px.line(
            df, x=x_col, y=y_col, title=title, markers=True, color_discrete_sequence=["#7c3aed"]
        ),
        "pie": lambda: px.pie(df, names=x_col, values=y_col, title=title, color_discrete_sequence=palette),
        "scatter": lambda: px.scatter(
            df, x=x_col, y=y_col, title=title, color_discrete_sequence=["#14b8a6"]
        ),
    }
    builder = builders.get(chart_type)
    if not builder:
        return None
    fig = builder()
    fig.update_layout(
        plot_bgcolor="#ffffff",
        paper_bgcolor="#faf5ff",
        font_color="#374151",
        title_font_color="#7c3aed",
        title_font_size=15,
        xaxis=dict(gridcolor="#f3e8ff", tickfont_color="#6b7280"),
        yaxis=dict(gridcolor="#f3e8ff", tickfont_color="#6b7280"),
        margin=dict(l=48, r=24, t=56, b=48),
        height=380,
    )
    return fig


if "history" not in st.session_state:
    st.session_state.history = []
if "db_ready" not in st.session_state:
    init_db()
    st.session_state.db_ready = True

OPENROUTER_MODELS = [
    "google/gemini-2.5-flash",
    "google/gemini-2.5-flash-lite",
    "google/gemini-3.5-flash",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-4-26b-a4b-it:free",
    "moonshotai/kimi-k2.6:free",
    "qwen/qwen-2.5-7b-instruct",
]

SUGGESTIONS = [
    "Top 5 customers by revenue",
    "Monthly sales trend in 2024",
    "Revenue by product category",
    "Products with low stock (under 20)",
    "Average order value by customer segment",
    "Count of orders by status",
]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🗄️ Analytics Agent")
    st.caption("Schema-grounded NL → SQL")

    api_key = st.text_input(
        "OpenRouter API Key",
        type="password",
        value=os.environ.get("OPENROUTER_API_KEY", ""),
        placeholder="sk-or-... or set OPENROUTER_API_KEY",
        help="Get a key at https://openrouter.ai/keys",
    )
    default_model = resolve_model(os.environ.get("OPENROUTER_MODEL"))
    model_idx = (
        OPENROUTER_MODELS.index(default_model)
        if default_model in OPENROUTER_MODELS
        else 0
    )
    model = st.selectbox("Model", OPENROUTER_MODELS, index=model_idx)
    st.caption("Powered by **[OpenRouter](https://openrouter.ai)** — pick a free or paid model")
    st.markdown("---")

    st.markdown("### 📋 Schema explorer")
    for tname, tdata in get_table_info().items():
        with st.expander(f"**{tname}** · {tdata['count']} rows"):
            for col in tdata["columns"]:
                pk = " 🔑" if col[5] else ""
                st.markdown(f"`{col[1]}` · *{col[2]}*{pk}")

    st.markdown("---")
    st.markdown("### 💡 Example questions")
    for s in SUGGESTIONS:
        if st.button(s, key=f"sug_{s}", use_container_width=True):
            st.session_state["prefill"] = s

    st.markdown("---")
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.history = []
        st.rerun()

# ── Main ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="hero">
  <h1>NL-to-SQL Analytics Agent</h1>
  <p>Ask in plain English. The agent inspects your SQLite schema with tools,
  writes safe read-only SQL, and returns answers with charts when it helps.</p>
</div>
""",
    unsafe_allow_html=True,
)

kpis = kpi_metrics()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Completed orders", kpis["orders"])
c2.metric("Total revenue", f"${kpis['revenue']:,.2f}")
c3.metric("Customers", kpis["customers"])
c4.metric("Products", kpis["products"])

st.markdown("---")

for item in st.session_state.history:
    if item["role"] == "user":
        st.markdown(
            f'<div class="user-bubble"><span class="bubble-tag">You</span> {item["content"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="assistant-bubble"><span class="bubble-tag">Agent</span> {item["content"]}</div>',
            unsafe_allow_html=True,
        )
        if item.get("tools"):
            pills = "".join(
                f'<span class="tool-pill">{t["tool"]}</span>' for t in item["tools"]
            )
            st.markdown(f"**Agent tools used:** {pills}", unsafe_allow_html=True)
        if item.get("sql"):
            st.markdown(
                f'<div class="sql-label">Generated SQL</div>'
                f'<div class="sql-block">{item["sql"]}</div>',
                unsafe_allow_html=True,
            )
        if item.get("error"):
            st.error(item["error"])
        elif item.get("df") is not None and not item["df"].empty:
            st.dataframe(item["df"], use_container_width=True, hide_index=True)
        if item.get("chart") is not None:
            st.plotly_chart(item["chart"], use_container_width=True)

st.markdown("---")
prefill = st.session_state.pop("prefill", "")
col_q, col_run = st.columns([5, 1])
with col_q:
    question = st.text_input(
        "Question",
        value=prefill,
        placeholder="e.g. Which product categories drive the most revenue?",
        label_visibility="collapsed",
    )
with col_run:
    submit = st.button("▶ Ask", type="primary", use_container_width=True)

if submit and question.strip():
    if not api_key:
        st.warning("Add your OpenRouter API key in the sidebar or set `OPENROUTER_API_KEY`.")
    else:
        st.session_state.history.append({"role": "user", "content": question})
        with st.spinner("Agent is exploring schema and building SQL…"):
            try:
                out = run_analytics_agent(question, api_key, model=model)
                result = out["result"]
                sql = result.get("sql", "")
                df, err = run_query(sql) if sql else (pd.DataFrame(), None)
                chart = None
                if df is not None and not df.empty and result.get("chart_type"):
                    chart = make_chart(
                        df,
                        result["chart_type"],
                        result.get("chart_x", ""),
                        result.get("chart_y", ""),
                        result.get("chart_title", "Chart"),
                    )
                st.session_state.history.append(
                    {
                        "role": "assistant",
                        "content": result.get("answer", "Here are your results."),
                        "sql": sql,
                        "df": df if df is not None else pd.DataFrame(),
                        "chart": chart,
                        "error": err,
                        "tools": out.get("tool_trace", []),
                    }
                )
            except Exception as exc:
                st.session_state.history.append(
                    {
                        "role": "assistant",
                        "content": "I could not complete that request.",
                        "sql": None,
                        "df": None,
                        "chart": None,
                        "error": str(exc),
                        "tools": [],
                    }
                )
        st.rerun()

"""Reusable Streamlit UI components."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.constants import APP_NAME, SAMPLE_QUESTIONS
from utils.formatting import (
    dataframe_to_csv_bytes,
    dataframe_to_excel_bytes,
    format_dataframe_for_display,
    format_inr,
    query_report_pdf_bytes,
)
from utils.history import export_history_csv, get_history
from utils.database import get_table_info


def render_schema_explorer() -> None:
    """Render schema explorer as an expandable panel on the right side."""
    with st.expander("📊 Schema Explorer", expanded=False):
        for tname, tdata in get_table_info().items():
            with st.expander(f"**{tname}** ({tdata['count']} rows)"):
                for col in tdata["columns"]:
                    pk = " 🔑" if col[5] else ""
                    st.markdown(f"`{col[1]}` - *{col[2]}*{pk}")


def render_query_history_panel() -> None:
    """Render query history as an expandable panel on the right side."""
    with st.expander("📜 Query History", expanded=False):
        history = get_history(limit=20)
        if not history:
            st.caption("No queries yet. Ask a question to get started.")
            return

        for entry in history:
            icon = "✅" if entry.get("success") else "❌"
            ts = entry.get("timestamp", "")[:16].replace("T", " ")
            label = f"{icon} {entry.get('question', '')[:40]}"
            
            if st.button(label, key=f"hist_{entry.get('id', ts)}", use_container_width=True):
                st.session_state.selected_history = entry
                st.rerun()
            st.caption(f"{ts} • {entry.get('row_count', 0)} rows")
        
        st.divider()
        st.download_button(
            "📥 Download History (CSV)",
            data=export_history_csv(),
            file_name="query_history.csv",
            mime="text/csv",
            use_container_width=True,
        )


def render_hero() -> None:
    st.markdown(
        f"""
<div class="dashboard-topbar">
  <div>
    <div class="hero-badge">Analytics Dashboard</div>
    <h1>{APP_NAME}</h1>
    <p>Ask questions, generate SQL, and explore business results in one clean workspace.</p>
  </div>
  <div class="topbar-chip">NL to SQL</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_kpis(kpis: dict[str, float | int]) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Sales", format_inr(kpis["total_sales"]))
    c2.metric("Employees", f"{kpis['employees']:,}")
    c3.metric("Products", f"{kpis['products']:,}")
    c4.metric("Departments", f"{kpis['departments']:,}")


def render_sample_questions() -> None:
    st.markdown("### Quick questions")
    for q in SAMPLE_QUESTIONS[:3]:
        if st.button(q, key=f"sug_{q}", use_container_width=True):
            st.session_state["auto_ask"] = q
            st.rerun()


def render_query_history_sidebar() -> None:
    # Initialize session state
    if "show_history" not in st.session_state:
        st.session_state.show_history = False
    
    # Toggle button
    if st.button("📜 Quick History", use_container_width=True):
        st.session_state.show_history = not st.session_state.show_history
        st.rerun()
    
    # Show history only if toggled on
    if st.session_state.show_history:
        history = get_history(limit=10)
        if not history:
            st.caption("No queries yet. Ask a question to get started.")
            return

        for entry in history:
            icon = "✅" if entry.get("success") else "❌"
            ts = entry.get("timestamp", "")[:16].replace("T", " ")
            label = f"{icon}  {entry.get('question', '')[:40]}"
            if st.button(
                label,
                key=f"history_{entry.get('id', ts)}",
                use_container_width=True,
                help=f"{ts} - {entry.get('row_count', 0)} rows",
            ):
                st.session_state.selected_history = entry
                st.rerun()
            st.caption(f"{ts} - {entry.get('row_count', 0)} rows")

        st.divider()
        st.download_button(
            "📥 Download history (CSV)",
            data=export_history_csv(),
            file_name="query_history.csv",
            mime="text/csv",
            use_container_width=True,
        )


def render_selected_history() -> None:
    entry = st.session_state.get("selected_history")
    if not entry:
        return

    status = "Successful query" if entry.get("success") else "Failed query"
    st.markdown("### History reference")
    with st.container(border=True):
        st.markdown(f"**{status}**")
        st.markdown(f"**Question:** {entry.get('question', '')}")
        if entry.get("summary"):
            st.markdown(f"**Answer:** {entry.get('summary')}")
        st.caption(f"Rows: {entry.get('row_count', 0)} | Session ID: {entry.get('id', '')}")
        if entry.get("sql"):
            st.markdown("**SQL**")
            st.markdown(f'<div class="sql-block">{entry["sql"]}</div>', unsafe_allow_html=True)
        if entry.get("error"):
            st.error(entry["error"])


def render_query_box(on_voice_click: Callable[[], str | None] | None = None) -> tuple[str, bool]:
    st.markdown(
        """
<div class="query-panel-title">
  <span>Ask your data</span>
  <small>Type or speak a question and run analysis</small>
</div>
""",
        unsafe_allow_html=True,
    )
    voice_status = st.container()
    col_mic, col_q, col_btn = st.columns([0.7, 5, 1])
    with col_mic:
        if st.button("Mic", use_container_width=True, help="Use microphone"):
            with voice_status:
                if on_voice_click is not None:
                    on_voice_click()
                else:
                    st.error("Voice input is not available.")
    with col_q:
        typed = st.text_input(
            "Ask a question",
            placeholder="Example: Show total sales by month in Rs",
            label_visibility="collapsed",
            key="question_input",
        )
    with col_btn:
        ask_clicked = st.button("Ask", type="primary", use_container_width=True)
    return typed, ask_clicked


def render_agent_steps(steps: list[dict[str, Any]], expanded: bool = False) -> None:
    with st.expander("Agent pipeline", expanded=expanded):
        for step in steps:
            status = step.get("status", "pending")
            css = {
                "done": "step-done",
                "error": "step-error",
                "running": "step-running",
            }.get(status, "step-pending")
            label = {"done": "Done", "error": "Error", "running": "Running"}.get(status, "Pending")
            st.markdown(
                f"<span class='{css}'>{label}</span> "
                f"Step {step['step']}: {step['name']} "
                f"<span style='color:#6b7280'>{step.get('detail', '')}</span>",
                unsafe_allow_html=True,
            )


def render_assistant_response(item: dict[str, Any], message_index: int) -> None:
    if item.get("error"):
        if item.get("steps"):
            render_agent_steps(item["steps"])
        if item.get("sql"):
            _render_sql(item)
        st.error(item["error"])
        if item.get("error_hint"):
            st.info(item["error_hint"])
        return

    df: pd.DataFrame | None = item.get("df")

    if item.get("findings"):
        st.markdown("**Key findings**")
        for finding in item["findings"]:
            st.markdown(f"- {finding}")

    chart: go.Figure | None = item.get("chart")
    if chart is not None:
        st.plotly_chart(chart, use_container_width=True)

    if df is not None and not df.empty:
        with st.expander(f"Results table ({len(df)} rows)", expanded=True):
            st.dataframe(format_dataframe_for_display(df), use_container_width=True, hide_index=True)
            _render_downloads(item, message_index, df)

    if item.get("sql"):
        with st.expander("Generated SQL"):
            _render_sql(item)

    if item.get("steps"):
        render_agent_steps(item["steps"])


def _render_sql(item: dict[str, Any]) -> None:
    st.markdown(f'<div class="sql-block">{item["sql"]}</div>', unsafe_allow_html=True)
    if item.get("sql_explanation"):
        st.markdown("**SQL explanation**")
        st.info(item["sql_explanation"])


def _render_downloads(item: dict[str, Any], message_index: int, df: pd.DataFrame) -> None:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            label="Download CSV",
            data=dataframe_to_csv_bytes(df),
            file_name=f"query_results_{message_index}.csv",
            mime="text/csv",
            key=f"dl_csv_{message_index}",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            label="Download Excel",
            data=dataframe_to_excel_bytes(df),
            file_name=f"query_results_{message_index}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_xlsx_{message_index}",
            use_container_width=True,
        )
    with c3:
        try:
            pdf_bytes = query_report_pdf_bytes(
                item.get("question", ""),
                item.get("content", ""),
                item.get("sql", ""),
                df,
            )
            st.download_button(
                label="Download PDF",
                data=pdf_bytes,
                file_name=f"query_report_{message_index}.pdf",
                mime="application/pdf",
                key=f"dl_pdf_{message_index}",
                use_container_width=True,
            )
        except RuntimeError:
            st.caption("PDF unavailable")


def render_loading_steps(current_step: int = 1) -> None:
    from config.constants import AGENT_STEPS

    st.markdown('<div class="loading-pulse">Running analysis...</div>', unsafe_allow_html=True)
    for i, name in enumerate(AGENT_STEPS, start=1):
        if i < current_step:
            st.success(f"Step {i}: {name}")
        elif i == current_step:
            st.info(f"Step {i}: {name}")
        else:
            st.caption(f"Step {i}: {name}")

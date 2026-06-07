"""NL-to-SQL Analytics Agent Streamlit entry point."""

from __future__ import annotations

import os 
import sys
import traceback

if sys.platform == "win32":
    os.environ.setdefault("PYTHONUTF8", "1")

import streamlit as st
from dotenv import load_dotenv

try:
    import speech_recognition as sr
except ImportError:  # pragma: no cover - handled in the Streamlit UI
    sr = None

try:
    import sounddevice as sd
except ImportError:  # pragma: no cover - handled in the Streamlit UI
    sd = None

from agents.agent_loop import run_agent_loop
from agents.llm_client import LLMClient
from config.constants import APP_NAME, OLLAMA_MODELS, OPENROUTER_MODELS
from ui.components import (
    render_assistant_response,
    render_hero,
    render_kpis,
    render_query_box,
    render_query_history_sidebar,
    render_sample_questions,
    render_selected_history,
)
from ui.styles import CUSTOM_CSS
from utils.database import (
    get_table_info,
    init_db,
    kpi_metrics,
    load_csv_to_sqlite,
    get_uploaded_tables,
    clear_all_uploaded_tables,
    is_uploaded_table,
    UPLOADED_TABLES_KEY,
)
from utils.errors import AnalyticsAgentError, LLMConnectionError
from utils.history import add_entry, clear_history
from utils.sql_explainer import explain_sql_locally

load_dotenv()


def _init_session() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_history" not in st.session_state:
        st.session_state.selected_history = None
    if "db_ready" not in st.session_state:
        init_db(force=True)
        st.session_state.db_ready = True
    if UPLOADED_TABLES_KEY not in st.session_state:
        st.session_state[UPLOADED_TABLES_KEY] = {}


def _build_llm(use_ollama: bool, model: str, api_key: str, ollama_base: str) -> LLMClient:
    kwargs: dict = {"provider": "ollama" if use_ollama else "openrouter", "model": model}
    if use_ollama:
        kwargs["ollama_base"] = ollama_base
    else:
        kwargs["api_key"] = api_key
    return LLMClient(**kwargs)


def _handle_csv_upload(uploaded_file) -> None:
    """Process CSV file upload and create temporary SQLite table."""
    if uploaded_file is None:
        return
    
    try:
        # Check file size (warn if > 50MB)
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        if file_size_mb > 50:
            st.warning(f"⚠️ Large file ({file_size_mb:.1f} MB) - processing may take a moment...")
        
        # Load CSV into SQLite
        table_name, df, error = load_csv_to_sqlite(uploaded_file, uploaded_file.name, st.session_state)
        
        if error:
            st.error(f"❌ Upload failed: {error}")
            return
        
        # Success!
        st.success(f"✅ CSV uploaded successfully as table '{table_name}'")
        st.info(f"📊 {len(df)} rows × {len(df.columns)} columns")
        
        # Show dataframe preview
        with st.expander(f"Preview: {uploaded_file.name}", expanded=True):
            st.dataframe(df.head(10), use_container_width=True)
            if len(df) > 10:
                st.caption(f"Showing 10 of {len(df)} rows")
        
        # Rerun to update schema explorer
        st.rerun()
        
    except Exception as exc:
        st.error(f"❌ Unexpected error: {str(exc)}")


def _process_question(question: str, llm: LLMClient) -> dict:
    """Run the agent loop with step-by-step status UI and robust error handling."""
    assistant_payload: dict = {
        "role": "assistant",
        "question": question,
        "content": "",
        "sql": None,
        "sql_explanation": None,
        "df": None,
        "chart": None,
        "error": None,
        "error_hint": None,
        "findings": [],
        "steps": [],
    }

    try:
        with st.status("Running analysis...", expanded=True) as status:
            st.write("Reading schema and preparing SQL...")
            out = run_agent_loop(question, llm)

            for step in out.steps:
                if step.status == "done":
                    st.success(f"Step {step.step}: {step.name}")
                elif step.status == "error":
                    st.error(f"Step {step.step}: {step.name} - {step.detail}")
                else:
                    st.info(f"Step {step.step}: {step.name}")

            assistant_payload["steps"] = [
                {"step": s.step, "name": s.name, "status": s.status, "detail": s.detail}
                for s in out.steps
            ]

            if out.error:
                status.update(label="Query failed", state="error")
                assistant_payload["content"] = "I couldn't complete that query."
                assistant_payload["error"] = out.error
                assistant_payload["sql"] = out.sql or None
                add_entry(question, out.sql, "", 0, False, out.error)
                return assistant_payload

            insights = out.insights or {}
            assistant_payload["content"] = insights.get("summary", "Here are your results.")
            assistant_payload["sql"] = out.sql
            assistant_payload["df"] = out.df
            assistant_payload["chart"] = out.chart
            assistant_payload["findings"] = insights.get("key_findings", [])

            row_count = len(out.df) if out.df is not None else 0
            add_entry(question, out.sql, assistant_payload["content"], row_count, True)
            status.update(label="Analysis complete", state="complete")

    except LLMConnectionError as exc:
        assistant_payload["content"] = "Analysis engine failed."
        assistant_payload["error"] = exc.user_message()
        add_entry(question, None, "", 0, False, str(exc))
    except AnalyticsAgentError as exc:
        assistant_payload["content"] = "Agent error."
        assistant_payload["error"] = exc.user_message()
        add_entry(question, None, "", 0, False, str(exc))
    except Exception as exc:
        assistant_payload["content"] = "Unexpected error."
        assistant_payload["error"] = str(exc)
        assistant_payload["error_hint"] = "Try rephrasing your question."
        add_entry(question, None, "", 0, False, str(exc))
        if os.environ.get("DEBUG"):
            st.code(traceback.format_exc())

    return assistant_payload


def _capture_voice_query() -> str | None:
    """Capture microphone audio and return recognized speech as text."""
    if sr is None:
        st.error(
            "Voice input is unavailable because SpeechRecognition is not installed. "
            "Install the updated requirements and restart the app."
        )
        return None
    if sd is None:
        st.error(
            "Voice input is unavailable because the microphone recorder dependency is "
            "not installed. Install the updated requirements and restart the app."
        )
        return None

    recognizer = sr.Recognizer()
    sample_rate = 16_000
    duration_seconds = 8

    try:
        sd.query_devices(kind="input")
        st.info("Listening... speak your question clearly.")
        recording = sd.rec(
            int(duration_seconds * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
        )
        sd.wait()
        audio = sr.AudioData(recording.tobytes(), sample_rate, 2)
    except OSError as exc:
        st.error(
            "Microphone access failed. Check that a microphone is connected and that "
            f"your system has granted permission. Details: {exc}"
        )
        return None
    except Exception as exc:
        st.error(
            "I could not record from the microphone. Check device permissions and try "
            f"again. Details: {exc}"
        )
        return None

    try:
        recognized_text = recognizer.recognize_google(audio).strip()
    except sr.UnknownValueError:
        st.warning("I could not understand the audio. Please try again or type your question.")
        return None
    except sr.RequestError as exc:
        st.error(
            "Speech recognition could not reach the recognition service. "
            f"Check your internet connection and try again. Details: {exc}"
        )
        return None

    if not recognized_text:
        st.warning("No speech was recognized. Please try again or type your question.")
        return None

    st.session_state.question_input = recognized_text
    st.success("Voice captured. You can edit the question before clicking Ask.")
    return recognized_text


def _run_query_flow(question: str, use_ollama: bool, model: str, api_key: str, ollama_base: str) -> None:
    llm = _build_llm(use_ollama, model, api_key, ollama_base)
    ok, msg = llm.is_available()
    if not ok:
        st.warning(msg)
        return
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.messages.append(_process_question(question, llm))


def _render_messages(use_ollama: bool, model: str, api_key: str, ollama_base: str) -> None:
    for idx, item in enumerate(st.session_state.messages):
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
            if item["role"] != "assistant":
                continue

            render_assistant_response(item, idx)
            if item.get("sql") and st.button("Explain SQL", key=f"explain_sql_{idx}"):
                fallback = explain_sql_locally(item["sql"])
                try:
                    explainer = _build_llm(use_ollama, model, api_key, ollama_base)
                    ok, msg = explainer.is_available()
                    if not ok:
                        st.session_state.messages[idx]["sql_explanation"] = (
                            f"{fallback}\n\nAI explanation was unavailable: {msg}"
                        )
                    else:
                        explanation = explainer.explain_sql(item["sql"]).strip()
                        st.session_state.messages[idx]["sql_explanation"] = explanation or fallback
                except Exception as exc:
                    st.session_state.messages[idx]["sql_explanation"] = (
                        f"{fallback}\n\nAI explanation failed: {exc}"
                    )
                st.rerun()


def main() -> None:
    st.set_page_config(
        page_title=APP_NAME,
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)
    _init_session()

    with st.sidebar:
        st.markdown(f"## {APP_NAME}")
        st.caption("Natural language to SQL insights")

        provider = st.radio("LLM Provider", ["OpenRouter (cloud)", "Ollama (local Llama3)"])
        use_ollama = provider.startswith("Ollama")
        api_key = ""
        ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

        if use_ollama:
            model = st.selectbox("Ollama Model", OLLAMA_MODELS)
            ollama_base = st.text_input("Ollama URL", value=ollama_base)
        else:
            api_key = st.text_input(
                "OpenRouter API Key",
                type="password",
                value=os.environ.get("OPENROUTER_API_KEY", ""),
                placeholder="sk-or-v1-...",
            )
            model = st.selectbox("OpenRouter Model", OPENROUTER_MODELS)

        st.markdown("---")
        st.markdown("### 📤 Upload CSV Data")
        uploaded_csv = st.file_uploader(
            "Choose a CSV file",
            type=["csv"],
            accept_multiple_files=False,
            help="Upload a CSV file to create a temporary SQLite table for analysis"
        )
        if uploaded_csv is not None:
            _handle_csv_upload(uploaded_csv)
        
        st.markdown("---")
        st.markdown("### Schema explorer")
        
        # Get table info
        table_info = get_table_info()
        uploaded_tables = get_uploaded_tables(st.session_state)
        
        # Display uploaded tables first with special styling
        if uploaded_tables:
            st.markdown("**Uploaded Tables:**")
            for tname, tdata in table_info.items():
                if is_uploaded_table(tname):
                    meta = uploaded_tables.get(tname, {})
                    filename = meta.get("filename", tname)
                    with st.expander(f"📊 {tname} - {tdata['count']} rows (from {filename})"):
                        for col in tdata["columns"]:
                            pk = " (PK)" if col[5] else ""
                            st.markdown(f"`{col[1]}` - {col[2]}{pk}")
            st.divider()
        
        # Display built-in tables
        builtin_count = 0
        for tname, tdata in table_info.items():
            if not is_uploaded_table(tname):
                with st.expander(f"{tname} - {tdata['count']} rows"):
                    for col in tdata["columns"]:
                        pk = " (PK)" if col[5] else ""
                        st.markdown(f"`{col[1]}` - {col[2]}{pk}")
                builtin_count += 1
        
        if builtin_count == 0:
            st.caption("No built-in tables available")

        st.markdown("---")
        render_sample_questions()
        st.markdown("---")
        render_query_history_sidebar()
        st.markdown("---")
        if st.button("Clear results", use_container_width=True):
            st.session_state.messages = []
            st.session_state.selected_history = None
            st.rerun()
        if st.button("Clear query history", use_container_width=True):
            clear_history()
            st.session_state.selected_history = None
            st.toast("History cleared")
            st.rerun()
        if get_uploaded_tables(st.session_state):
            if st.button("Clear uploaded data", use_container_width=True, type="secondary"):
                count, error = clear_all_uploaded_tables(st.session_state)
                st.toast(f"Cleared {count} uploaded table(s)")
                st.rerun()

    render_hero()
    render_kpis(kpi_metrics())
    typed, ask_clicked = render_query_box(on_voice_click=_capture_voice_query)
    render_selected_history()
    _render_messages(use_ollama, model, api_key, ollama_base)

    auto_ask = st.session_state.pop("auto_ask", None)
    if auto_ask:
        _run_query_flow(auto_ask.strip(), use_ollama, model, api_key, ollama_base)
        st.rerun()

    if ask_clicked and typed.strip():
        _run_query_flow(typed.strip(), use_ollama, model, api_key, ollama_base)
        st.rerun()


if __name__ == "__main__":
    main()

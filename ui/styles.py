"""Streamlit UI styles for the dashboard."""

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg: #e8f4f2;
    --page: #f7fcfb;
    --panel: #ffffff;
    --ink: #10172a;
    --muted: #6f7485;
    --line: #dde8e7;
    --coral: #ff796b;
    --coral-dark: #ee6255;
    --teal: #0f766e;
    --teal-soft: #e8f8f5;
    --shadow: 0 18px 45px rgba(28, 43, 58, 0.08);
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: var(--ink);
}

.stApp {
    background:
        linear-gradient(90deg, rgba(200, 226, 221, 0.72) 0, rgba(200, 226, 221, 0.72) 11%, transparent 11%, transparent 89%, rgba(200, 226, 221, 0.72) 89%),
        var(--bg);
}

#MainMenu {
    display: none !important;
}

footer {
    display: none !important;
}

[data-testid="stSidebar"] {
    background: #f5f7fa !important;
    border-right: 1px solid #dde8e7 !important;
    display: block !important;
    visibility: visible !important;
}

[data-testid="stSidebar"] > div {
    display: flex !important;
    flex-direction: column !important;
}

[data-testid="stSidebar"] * {
    color: #10172a !important;
}

[data-testid="stSidebar"] h2 {
    font-weight: 800 !important;
    letter-spacing: 0;
}

[data-testid="stSidebar"] h3 {
    margin-top: 0.35rem;
    font-size: 0.82rem !important;
    font-weight: 800 !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] .stCaption {
    color: #6f7485 !important;
}

[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: #ffffff;
    border: 1px solid #dde8e7;
}

[data-testid="stSidebar"] button {
    background: #ffffff !important;
    border: 1px solid #dde8e7 !important;
    color: #10172a !important;
    text-align: left !important;
}

[data-testid="stSidebar"] button:hover {
    border-color: var(--coral) !important;
    background: #f0f2f5 !important;
}

[data-testid="stSidebar"] input {
    background: #ffffff !important;
    color: #10172a !important;
}

[data-testid="stSidebar"] [data-baseweb="radio"] label,
[data-testid="stSidebar"] [data-baseweb="select"] * {
    color: #10172a !important;
}

.block-container {
    max-width: 1320px;
    min-height: 100vh;
    padding: 54px 34px 48px;
    background: var(--page);
    box-shadow: var(--shadow);
}

.dashboard-topbar {
    display: flex;
    justify-content: space-between;
    gap: 24px;
    align-items: center;
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 28px;
    margin-bottom: 22px;
    box-shadow: 0 12px 30px rgba(24, 39, 54, 0.05);
}

.hero-badge {
    display: inline-block;
    margin-bottom: 28px;
    color: var(--coral);
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.dashboard-topbar h1 {
    margin: 0;
    color: var(--ink);
    font-size: 1.55rem;
    line-height: 1.1;
    font-weight: 800;
    letter-spacing: 0;
}

.dashboard-topbar p {
    margin: 24px 0 0;
    color: var(--muted);
    font-size: 0.94rem;
}

.topbar-chip {
    background: var(--teal-soft);
    color: var(--teal);
    border: 1px solid #c7e9e3;
    border-radius: 999px;
    padding: 12px 18px;
    font-size: 0.78rem;
    font-weight: 800;
    white-space: nowrap;
}

div[data-testid="stMetric"] {
    background: var(--panel);
    border: 1px solid var(--line);
    border-top: 5px solid var(--coral);
    border-radius: 8px;
    padding: 22px 22px 20px;
    box-shadow: 0 14px 30px rgba(24, 39, 54, 0.06);
}

div[data-testid="stMetric"] label {
    color: var(--muted) !important;
    font-size: 0.74rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.02em;
}

div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: var(--ink) !important;
    font-size: 1.55rem !important;
    font-weight: 800 !important;
}

.query-panel-title {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin: 38px 0 10px;
}

.query-panel-title span,
.analysis-heading {
    color: var(--ink);
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    font-size: 0.82rem;
}

.query-panel-title small {
    color: var(--muted);
    font-weight: 600;
}

.stTextInput input {
    min-height: 50px;
    background: #ffffff !important;
    border: 1px solid #d7e2e3 !important;
    border-radius: 8px !important;
    color: var(--ink) !important;
    font-size: 0.94rem !important;
    box-shadow: 0 8px 22px rgba(24, 39, 54, 0.04);
}

.stTextInput input:focus {
    border-color: var(--coral) !important;
    box-shadow: 0 0 0 3px rgba(255, 121, 107, 0.14) !important;
}

.stButton > button,
.stDownloadButton > button {
    min-height: 42px;
    border-radius: 8px !important;
    border: 1px solid #d7e2e3 !important;
    background: #ffffff !important;
    color: var(--ink) !important;
    font-weight: 700 !important;
    box-shadow: none !important;
}

.stButton > button[kind="primary"] {
    min-height: 50px;
    background: var(--coral) !important;
    border-color: var(--coral) !important;
    color: #ffffff !important;
}

.stButton > button[kind="primary"]:hover {
    background: var(--coral-dark) !important;
    border-color: var(--coral-dark) !important;
}

[data-testid="stExpander"] {
    margin-top: 18px;
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 8px;
    overflow: hidden;
}

[data-testid="stExpander"] summary {
    font-weight: 800;
    color: var(--ink);
}

.table-pill {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    padding: 10px 12px;
    margin-bottom: 8px;
    background: #f5fbfa;
    border: 1px solid var(--line);
    border-radius: 8px;
    font-size: 0.88rem;
}

.table-pill span {
    color: var(--muted);
    font-size: 0.78rem;
    font-weight: 700;
}

.sql-block {
    background: #172033;
    border-left: 4px solid #66d4b2;
    border-radius: 8px;
    padding: 14px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: #c8f7df;
    white-space: pre-wrap;
    word-break: break-word;
}

.step-done { color: #16835f; font-weight: 800; }
.step-error { color: #c24134; font-weight: 800; }
.step-running { color: #2563eb; font-weight: 800; }
.step-pending { color: #8d94a3; font-weight: 700; }

[data-testid="stChatMessage"] {
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 10px 14px;
    margin-top: 16px;
}

[data-testid="stDataFrame"] {
    border-radius: 8px;
    border: 1px solid var(--line);
    overflow: hidden;
}

hr {
    display: none;
}

@media (max-width: 760px) {
    .block-container {
        padding: 24px 16px 36px;
    }

    .dashboard-topbar {
        align-items: flex-start;
        flex-direction: column;
        padding: 22px;
    }

    .hero-badge {
        margin-bottom: 18px;
    }

    .dashboard-topbar p {
        margin-top: 14px;
    }
}
"""

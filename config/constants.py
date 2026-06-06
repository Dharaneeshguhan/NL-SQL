"""Central constants for the analytics agent."""

APP_NAME = "InsightSQL Agent"
APP_TAGLINE = "Ask in English. Get SQL, charts & business insights."
CURRENCY_LABEL = "Rs"
CURRENCY_SYMBOL = "Rs"

OPENROUTER_MODELS = [
    "google/gemini-2.5-flash-lite",
]

OLLAMA_MODELS = ["llama3", "llama3.1", "llama3.2"]

PROVIDER_OPENROUTER = "OpenRouter (cloud)"
PROVIDER_OLLAMA = "Ollama (local Llama3)"

SAMPLE_QUESTIONS = [
    "Show total sales by month",
    "Which product has highest sales?",
    "Show employee count by department",
]

AGENT_STEPS = [
    "Read database schema",
    "Understand user question",
    "Generate SQL",
    "Validate SQL",
    "Execute SQL",
    "Analyze result",
    "Recommend visualization",
]

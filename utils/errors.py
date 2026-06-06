"""Custom exceptions for clearer error handling across the agent pipeline."""


class AnalyticsAgentError(Exception):
    """Base exception for agent failures."""

    def user_message(self) -> str:
        return str(self)


class SchemaError(AnalyticsAgentError):
    """Failed to read database schema."""


class SQLGenerationError(AnalyticsAgentError):
    """LLM failed to produce SQL."""


class SQLValidationError(AnalyticsAgentError):
    """Generated SQL failed security or syntax checks."""


class SQLExecutionError(AnalyticsAgentError):
    """Query execution failed against SQLite."""


class InsightGenerationError(AnalyticsAgentError):
    """Failed to generate business insights."""


class LLMConnectionError(AnalyticsAgentError):
    """Ollama or OpenRouter is unavailable."""

    def user_message(self) -> str:
        return (
            f"{self}\n\n"
            "**Tips:**\n"
            "- Ollama: run `ollama pull llama3` and ensure the server is running\n"
            "- OpenRouter: check your API key in the sidebar or `OPENROUTER_API_KEY`"
        )

"""

7-step Analytics Agent Loop.



Step 1: Read database schema

Step 2: Understand user question

Step 3: Generate SQL

Step 4: Validate SQL

Step 5: Execute SQL

Step 6: Analyze result

Step 7: Recommend visualization

"""



from __future__ import annotations



from dataclasses import dataclass, field



import pandas as pd



from agents.insight_generator import generate_insights

from agents.llm_client import LLMClient

from agents.schema_reader import read_schema

from agents.sql_generator import generate_sql

from agents.sql_validator import validate_sql

from utils.charts import build_chart, recommend_chart_type

from utils.database import execute_query

from utils.errors import (

    InsightGenerationError,

    SQLExecutionError,

    SQLGenerationError,

    SQLValidationError,

    SchemaError,

)





@dataclass

class AgentStep:

    step: int

    name: str

    status: str  # pending | running | done | error

    detail: str = ""





@dataclass

class AgentResult:

    question: str

    understanding: str = ""

    sql: str = ""

    validation_message: str = ""

    df: pd.DataFrame | None = None

    error: str | None = None

    insights: dict = field(default_factory=dict)

    chart: object | None = None

    steps: list[AgentStep] = field(default_factory=list)





def run_agent_loop(question: str, llm: LLMClient) -> AgentResult:

    """Execute the full NL-to-SQL analytics pipeline with structured error reporting."""

    if not question or not question.strip():

        result = AgentResult(question=question, error="Please enter a question.")

        return result



    result = AgentResult(question=question.strip())

    steps = [

        AgentStep(1, "Read database schema", "pending"),

        AgentStep(2, "Understand user question", "pending"),

        AgentStep(3, "Generate SQL", "pending"),

        AgentStep(4, "Validate SQL", "pending"),

        AgentStep(5, "Execute SQL", "pending"),

        AgentStep(6, "Analyze result", "pending"),

        AgentStep(7, "Recommend visualization", "pending"),

    ]

    result.steps = steps



    # Step 1: Schema

    steps[0].status = "running"

    try:

        schema = read_schema()

        steps[0].status = "done"

        steps[0].detail = f"Loaded {len(schema.splitlines())} lines of schema"

    except FileNotFoundError as exc:

        steps[0].status = "error"

        result.error = f"Database not found: {exc}"

        return result

    except Exception as exc:

        steps[0].status = "error"

        result.error = SchemaError(f"Schema read failed: {exc}").user_message()

        return result



    # Steps 2–3: Understand + Generate SQL

    steps[1].status = "running"

    steps[2].status = "running"

    try:

        sql, understanding = generate_sql(question, schema, llm)

        if not sql:

            raise SQLGenerationError("Model returned empty SQL. Try rephrasing your question.")

        result.understanding = understanding

        result.sql = sql

        steps[1].status = "done"

        steps[1].detail = understanding

        steps[2].status = "done"

        steps[2].detail = sql[:180] + ("…" if len(sql) > 180 else "")

    except SQLGenerationError as exc:

        steps[1].status = "error"

        steps[2].status = "error"

        result.error = exc.user_message()

        return result

    except Exception as exc:

        steps[1].status = "error"

        steps[2].status = "error"

        result.error = SQLGenerationError(str(exc)).user_message()

        return result



    # Step 4: Validate

    steps[3].status = "running"

    validation = validate_sql(sql)

    result.validation_message = validation.message

    if not validation.valid:

        steps[3].status = "error"

        steps[3].detail = validation.message

        result.error = SQLValidationError(validation.message).user_message()

        return result

    result.sql = validation.sanitized_sql

    steps[3].status = "done"

    steps[3].detail = "Read-only SELECT validated ✓"



    # Step 5: Execute

    steps[4].status = "running"

    df, err = execute_query(result.sql)

    if err:

        steps[4].status = "error"

        steps[4].detail = err

        result.error = SQLExecutionError(

            f"Query failed: {err}\n\nTip: Ask about tables — departments, employees, products, sales."

        ).user_message()

        return result

    result.df = df

    steps[4].status = "done"

    steps[4].detail = f"{len(df)} row(s), {len(df.columns)} column(s)"



    # Step 6: Analyze

    steps[5].status = "running"

    try:

        insights = generate_insights(question, result.sql, df, llm)

        result.insights = insights

        steps[5].status = "done"

        steps[5].detail = (insights.get("summary") or "")[:100]

    except Exception as exc:

        steps[5].status = "error"

        result.error = InsightGenerationError(str(exc)).user_message()

        return result



    # Step 7: Visualization

    steps[6].status = "running"

    chart_type = insights.get("chart_type")

    chart_x = insights.get("chart_x")

    chart_y = insights.get("chart_y")

    chart_title = insights.get("chart_title") or "Chart"



    fig = None

    if chart_type and chart_x and chart_y:

        fig = build_chart(df, chart_type, chart_x, chart_y, chart_title)

    if fig is None:

        heuristic = recommend_chart_type(df)

        if heuristic:

            fig = build_chart(

                df,

                heuristic["chart_type"],

                heuristic["x_col"],
                heuristic["y_col"],
                heuristic["title"],

            )

            steps[6].detail = f"{heuristic['chart_type']} chart (auto-detected)"

        else:

            steps[6].detail = "Table view — no chart needed"

    else:

        steps[6].detail = f"{chart_type} chart"



    result.chart = fig

    steps[6].status = "done"

    return result



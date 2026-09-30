"""Route user questions through the LLM and validated database executor."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from app.core import anomalies
from app.core.database import QueryExecutionError, run_query
from app.core.sql_validator import validate_sql
from app.llm.prompts import build_messages


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def answer_question(question: str) -> dict:
    completion = Groq().chat.completions.create(
        model=os.environ["GROQ_MODEL"],
        messages=build_messages(question), # type: ignore
        temperature=0,
        response_format={"type": "json_object"},
    )
    try:
        result = json.loads(completion.choices[0].message.content) # type: ignore
    except (AttributeError, IndexError, TypeError, json.JSONDecodeError):
        return {"intent": "unsupported", "error": "could not parse LLM response"}
    if not isinstance(result, dict) or "intent" not in result:
        return {"intent": "unsupported", "error": "could not parse LLM response"}

    intent = result["intent"]
    if intent not in ("data_query", "anomaly_query", "unsupported"):
        intent = "unsupported"
    if intent == "unsupported":
        return {"intent": "unsupported", "message": "I can help analyze support ticket data."}
    if intent == "anomaly_query":
        try:
            timeframe = "week" if result.get("timeframe") == "week" else None
            results = anomalies.find_anomalies(timeframe)
        except QueryExecutionError as exc:
            return {"intent": "anomaly_query", "error": str(exc)}
        return {"intent": "anomaly_query", "anomalies": results}

    sql = result.get("sql")
    valid, reason = validate_sql(sql)
    if not valid:
        return {"intent": "data_query", "error": f"unsafe query: {reason}"}
    try:
        rows = run_query(sql, as_of=None)
    except QueryExecutionError as exc:
        return {"intent": "data_query", "error": str(exc)}
    return {"intent": "data_query", "sql": sql, "rows": rows, "assumptions": result.get("assumptions", [])}
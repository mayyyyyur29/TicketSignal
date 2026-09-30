import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core import anomalies, orchestrator
from app.core.database import QueryExecutionError


def _mock_llm(monkeypatch: pytest.MonkeyPatch, content: str) -> Mock:
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )
    client = Mock()
    client.chat.completions.create.return_value = completion
    monkeypatch.setattr(orchestrator, "Groq", Mock(return_value=client))
    monkeypatch.setenv("GROQ_MODEL", "test-model")
    return client


def test_answer_question_calls_groq_and_executes_valid_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = {
        "intent": "data_query",
        "sql": "SELECT count(*) FROM v_tickets",
        "assumptions": ["all tickets"],
    }
    client = _mock_llm(monkeypatch, json.dumps(response))
    rows = [{"count": 3}]
    run_query = Mock(return_value=rows)
    monkeypatch.setattr(orchestrator, "run_query", run_query)

    result = orchestrator.answer_question("How many tickets?")

    assert result == {"intent": "data_query", "sql": response["sql"], "rows": rows, "assumptions": response["assumptions"]}
    request = client.chat.completions.create.call_args.kwargs
    assert request["model"] == "test-model"
    assert request["messages"] == orchestrator.build_messages("How many tickets?")
    assert request["temperature"] == 0
    assert request["response_format"] == {"type": "json_object"}
    run_query.assert_called_once_with(response["sql"], as_of=None)


@pytest.mark.parametrize("content", ["not json", "{}"])
def test_answer_question_handles_invalid_or_missing_intent(
    monkeypatch: pytest.MonkeyPatch, content: str
) -> None:
    _mock_llm(monkeypatch, content)
    run_query = Mock()
    monkeypatch.setattr(orchestrator, "run_query", run_query)

    assert orchestrator.answer_question("question") == {
        "intent": "unsupported",
        "error": "could not parse LLM response",
    }
    run_query.assert_not_called()


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ({"intent": "other"}, {"intent": "unsupported", "message": "I can help analyze support ticket data."}),
    ],
)
def test_answer_question_handles_non_data_intents(
    monkeypatch: pytest.MonkeyPatch, response: dict, expected: dict
) -> None:
    _mock_llm(monkeypatch, json.dumps(response))
    run_query = Mock()
    monkeypatch.setattr(orchestrator, "run_query", run_query)

    assert orchestrator.answer_question("question") == expected
    run_query.assert_not_called()


def test_answer_question_returns_anomalies(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_llm(monkeypatch, json.dumps({"intent": "anomaly_query"}))
    results = [{"ticket_id": "T-1", "reason": "High priority, unresolved for 30.0h (threshold 24h)"}]
    find_anomalies = Mock(return_value=results)
    monkeypatch.setattr(anomalies, "find_anomalies", find_anomalies)

    assert orchestrator.answer_question("Find anomalies") == {
        "intent": "anomaly_query",
        "anomalies": results,
    }
    find_anomalies.assert_called_once_with()


def test_answer_question_returns_anomaly_database_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_llm(monkeypatch, json.dumps({"intent": "anomaly_query"}))
    monkeypatch.setattr(
        anomalies, "find_anomalies", Mock(side_effect=QueryExecutionError("timeout"))
    )

    assert orchestrator.answer_question("Find anomalies") == {
        "intent": "anomaly_query",
        "error": "timeout",
    }


def test_answer_question_rejects_invalid_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_llm(monkeypatch, json.dumps({"intent": "data_query", "sql": "DELETE FROM tickets"}))
    run_query = Mock()
    monkeypatch.setattr(orchestrator, "run_query", run_query)

    result = orchestrator.answer_question("question")

    assert result == {"intent": "data_query", "error": "unsafe query: only SELECT statements are allowed"}
    run_query.assert_not_called()


def test_answer_question_returns_database_error(monkeypatch: pytest.MonkeyPatch) -> None:
    sql = "SELECT count(*) FROM v_tickets"
    _mock_llm(monkeypatch, json.dumps({"intent": "data_query", "sql": sql}))
    monkeypatch.setattr(orchestrator, "run_query", Mock(side_effect=QueryExecutionError("timeout")))

    assert orchestrator.answer_question("question") == {
        "intent": "data_query",
        "error": "timeout",
    }
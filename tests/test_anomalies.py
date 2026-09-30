from unittest.mock import Mock

from app.core import anomalies


def test_find_anomalies_queries_and_formats_rows(monkeypatch) -> None:
    rows = [
        {"ticket_id": "T-1", "priority": "Critical", "status": "Open", "age_hours": 31.26, "resolution_time_hrs": None},
        {"ticket_id": "T-2", "priority": "Medium", "status": "Resolved", "age_hours": 35, "resolution_time_hrs": 25},
    ]
    run_query = Mock(return_value=rows)
    monkeypatch.setattr(anomalies, "run_query", run_query)

    assert anomalies.find_anomalies() == [
        {"ticket_id": "T-1", "reason": "Critical priority, unresolved for 31.3h (threshold 24h)"},
        {"ticket_id": "T-2", "reason": "Medium priority, resolution took 25.0h (threshold 24h)"},
    ]
    run_query.assert_called_once()
    query = run_query.call_args.args[0]
    assert "status != 'Resolved' AND priority IN ('High', 'Critical') AND age_hours > 24" in query
    assert "status = 'Resolved' AND resolution_time_hrs > 24" in query
    assert "created_at >= as_of" not in query


def test_find_anomalies_limits_to_as_of_week(monkeypatch) -> None:
    run_query = Mock(return_value=[])
    monkeypatch.setattr(anomalies, "run_query", run_query)

    assert anomalies.find_anomalies("week") == []

    assert "created_at >= as_of - interval '7 days'" in run_query.call_args.args[0]
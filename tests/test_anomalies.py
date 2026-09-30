from unittest.mock import Mock

from app.core import anomalies


def test_find_anomalies_queries_and_formats_rows(monkeypatch) -> None:
    rows = [
        {"ticket_id": "T-1", "priority": "Critical", "status": "Open", "age_hours": 31.26},
        {"ticket_id": "T-2", "priority": "High", "status": "Escalated", "age_hours": 25},
    ]
    run_query = Mock(return_value=rows)
    monkeypatch.setattr(anomalies, "run_query", run_query)

    assert anomalies.find_anomalies() == [
        {"ticket_id": "T-1", "reason": "Critical priority, unresolved for 31.3h (threshold 24h)"},
        {"ticket_id": "T-2", "reason": "High priority, unresolved for 25.0h (threshold 24h)"},
    ]
    run_query.assert_called_once_with(
        """SELECT ticket_id, priority, status, age_hours
FROM v_tickets
WHERE priority IN ('High', 'Critical') AND status != 'Resolved' AND age_hours > 24
ORDER BY age_hours DESC"""
    )
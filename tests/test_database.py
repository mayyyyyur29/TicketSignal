from unittest.mock import MagicMock, call

import pytest

from app.core import database


def _mock_pool(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock, MagicMock]:
    pool = MagicMock()
    connection = MagicMock()
    cursor = MagicMock()
    pool.connection.return_value.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor
    monkeypatch.setattr(database, "_get_pool", lambda: pool)
    return pool, connection, cursor


def test_run_query_sets_read_only_and_parameters_and_returns_dict_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, connection, cursor = _mock_pool(monkeypatch)
    rows = [{"ticket_id": 7, "status": "closed"}]
    cursor.fetchall.return_value = rows

    result = database.run_query(
        "SELECT ticket_id, status FROM v_tickets", as_of="2026-09-30", timeout_ms=1200
    )

    assert result == rows
    connection.execute.assert_called_once_with("BEGIN READ ONLY")
    assert cursor.execute.call_args_list == [
        call("SELECT set_config('statement_timeout', %s, true)", ("1200",)),
        call("SELECT set_config('app.as_of', %s, true)", ("2026-09-30",)),
        call("SELECT ticket_id, status FROM v_tickets"),
    ]


def test_run_query_wraps_database_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    _, _, cursor = _mock_pool(monkeypatch)
    cursor.execute.side_effect = RuntimeError("database unavailable")

    with pytest.raises(database.QueryExecutionError, match="Query execution failed"):
        database.run_query("SELECT count(*) FROM v_tickets")
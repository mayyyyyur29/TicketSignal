from app.core.sql_validator import validate_sql


def test_allows_view_queries_and_approved_functions() -> None:
    queries = [
        "SELECT count(*) FROM v_tickets",
        "SELECT ROUND(AVG(response_time_hrs)::numeric, 2) FROM v_tickets",
        "SELECT date_trunc('day', created_at) FROM v_tickets",
    ]
    assert all(validate_sql(query) == (True, "") for query in queries)


def test_allows_boolean_connectors() -> None:
    queries = [
        "SELECT ticket_id FROM v_tickets WHERE resolution_time_hrs > 24 OR status != 'Resolved'",
        "SELECT ticket_id FROM v_tickets WHERE status = 'Open' AND priority = 'High'",
        "SELECT ticket_id FROM v_tickets WHERE NOT status = 'Resolved'",
    ]
    assert all(validate_sql(query) == (True, "") for query in queries)


def test_rejects_non_select_and_stacked_queries() -> None:
    queries = [
        "DELETE FROM tickets",
        "SELECT 1 FROM v_tickets; SELECT 1",
        "SELECT * INTO copied_tickets FROM v_tickets",
        "SELECT * FROM v_tickets FOR UPDATE",
    ]
    assert all(not validate_sql(query)[0] for query in queries)


def test_rejects_tables_other_than_view() -> None:
    queries = [
        "SELECT * FROM tickets",
        "SELECT * FROM pg_catalog.pg_tables",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM other_table",
        "SELECT 1",
    ]
    assert all(not validate_sql(query)[0] for query in queries)


def test_rejects_unapproved_and_time_dependent_functions() -> None:
    queries = [
        "SELECT pg_sleep(1) FROM v_tickets",
        "SELECT now() FROM v_tickets",
        "SELECT CURRENT_DATE FROM v_tickets",
        "SELECT CURRENT_TIMESTAMP FROM v_tickets",
        "SELECT public.count(*) FROM v_tickets",
    ]
    assert all(not validate_sql(query)[0] for query in queries)


def test_rejects_comments() -> None:
    queries = [
        "SELECT 1 FROM v_tickets -- hidden text",
        "SELECT 1 FROM v_tickets /* hidden text */",
    ]
    assert all(not validate_sql(query)[0] for query in queries)

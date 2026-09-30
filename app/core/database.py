"""Read-only database access for LLM-generated queries."""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class QueryExecutionError(RuntimeError):
    """Raised when a read-only query cannot be executed."""


_pool: ConnectionPool | None = None
_pool_lock = Lock()


def _get_pool() -> ConnectionPool:
    global _pool

    if _pool is None:
        with _pool_lock:
            if _pool is None:
                database_url = os.environ.get("LLM_DATABASE_URL")
                if not database_url:
                    raise QueryExecutionError("LLM_DATABASE_URL is not set")
                pool = ConnectionPool(database_url, min_size=1, max_size=4, open=False)
                pool.open(wait=True)
                _pool = pool # type: ignore
    return _pool # type: ignore


def run_query(
    sql: str, as_of: str | None = None, timeout_ms: int = 5000
) -> list[dict]:
    """Execute a query in a read-only transaction and return rows as dictionaries."""
    try:
        if type(timeout_ms) is not int:
            raise ValueError("timeout_ms must be an integer")

        with _get_pool().connection() as connection:
            connection.execute("BEGIN READ ONLY")
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    "SELECT set_config('statement_timeout', %s, true)",
                    (str(timeout_ms),),
                )
                if as_of is not None:
                    cursor.execute(
                        "SELECT set_config('app.as_of', %s, true)",
                        (as_of,),
                    )
                cursor.execute(sql) # type: ignore
                return cursor.fetchall()
    except QueryExecutionError:
        raise
    except Exception as exc:
        raise QueryExecutionError(f"Query execution failed: {exc}") from exc
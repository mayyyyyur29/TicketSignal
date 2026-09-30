# Ticket Intelligence

Ask natural-language questions about support tickets and flag unusually slow or aging tickets. The demo uses a read-only SQL role for LLM-generated queries.

## Quick start

1. Copy `.env.example` to `.env` and set `GROQ_API_KEY` to a Groq free-tier API key.
2. Run `docker compose up --build` from the repository root.
3. Open the Streamlit UI at <http://localhost:8501> or the API docs at <http://localhost:8000/docs>.

Compose initializes PostgreSQL from `db/schema.sql` and `db/roles.sql`, then runs a one-shot CSV ingestion service before starting the API. The bundled CSV is loaded into the database automatically. `docker compose down` preserves the database volume; `docker compose down -v` removes it so the next startup initializes and loads the data again.

The API health endpoint is `GET /health`; natural-language requests use `POST /query` with `{"question":"How many tickets are open?"}`. The Streamlit UI supports both data and anomaly questions.

## Architecture

`support_tickets.csv` → pandas validation/normalization → PostgreSQL `tickets` table → `v_tickets` view → FastAPI. The view provides the `as_of`, age, and resolution fields used by the query layer. Streamlit calls the API; the API sends question/context to Groq, validates generated SQL with sqlglot, and executes allowed queries through a Psycopg 3 pool using the separate `llm_ro` connection. Anomaly questions use fixed SQL rules and do not ask the LLM to generate SQL.

## Model and tools

- LLM: Groq API using `GROQ_MODEL` (the template defaults to `openai/gpt-oss-20b`). A free-tier key is required; no paid service is required for the demo within free-tier limits.
- Application: Python 3.12, FastAPI, Streamlit, pandas, Psycopg 3, and sqlglot.
- Data store: PostgreSQL 16, run locally in Docker Compose.

## Example queries

These outputs were checked against the bundled 500-row CSV; exact answers depend on the loaded data.

| Question | Example output |
| --- | --- |
| How many tickets are currently open? | 111 |
| How many Critical tickets are unresolved? | 31 |
| Which agent has the lowest average customer rating? | AGT-08, average 3.48 |
| Are there any anomalies? | 154 matches across the demo rules and current dataset |

“Not resolved within N hours” means a resolved ticket has `resolution_time_hrs > N`, or an unresolved ticket has `age_hours > N`. “This week” is relative to the view’s `as_of` value, which defaults to the latest `created_at` in the data.

## Known limitations

- Authentication and rate limiting are out of scope for this demo.
- The `llm_ro` role uses a hardcoded development password; use managed secrets outside local evaluation.
- `.env` was briefly committed during development and has since been untracked; rotate its Groq key before any real deployment because it may remain in Git history.
- Anomaly thresholds are fixed at 24 hours and are not configurable.
- Root-level development scripts remain in the repository.
- Groq request failures are surfaced as generic errors rather than provider-specific messages.
# Known Limitations

- Authentication and rate limiting are out of scope for this demo.
- The `llm_ro` database role uses a hardcoded development password; production should use managed secrets.
- `.env` was briefly committed during development; rotate the Groq key before any real deployment.
- `tests/test_llm_clients.py` imports LLM client modules that are no longer present.
- Root-level debug scripts (`debug_validator.py` and `support_analysis.py`) remain from development.
- Groq failures are surfaced as generic request errors rather than provider-specific messages.

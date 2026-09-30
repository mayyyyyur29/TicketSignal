import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.ingestion import load_csv, normalize_columns, validate, load_to_db

load_dotenv(ROOT / ".env")

default_csv = ROOT / "data" / "support_tickets.csv"

if len(sys.argv) > 1:
    csv_arg = sys.argv[1]
    csv_path = Path(csv_arg).resolve() if Path(csv_arg).is_absolute() else (ROOT / csv_arg).resolve()
else:
    csv_path = default_csv

if not csv_path.exists():
    print(f"Error: CSV file not found: {csv_path}")
    raise SystemExit(1)

print(f"Loading CSV: {csv_path}")

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL is not set in the environment.")

df = load_csv(csv_path)
normalized = normalize_columns(df)
valid_df, rejects = validate(normalized)

load_to_db(valid_df, database_url)

print(f"rows read: {len(df)}")
print(f"rows valid: {len(valid_df)}")
print(f"rows rejected: {len(rejects)}")
for ticket_id, reason in rejects:
    print(f"  - {ticket_id}: {reason}")

import psycopg

with psycopg.connect(database_url) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM tickets")
        count = cur.fetchone()[0]
print(f"rows in tickets table: {count}")

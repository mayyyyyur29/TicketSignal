import hashlib
from io import StringIO

import pandas as pd
import psycopg


def load_csv(path):
    """Read a CSV file into a pandas DataFrame."""
    return pd.read_csv(path)


def normalize_columns(df):
    """Rename legacy column names to the canonical ticket column names when present."""
    rename_map = {
        "resp_time_hrs": "response_time_hrs",
        "resol_time_hrs": "resolution_time_hrs",
        "cust_rating": "customer_rating",
    }
    normalized = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return normalized


def validate(df):
    """Return a cleaned DataFrame and a list of rejected rows with reasons."""
    valid_rows = []
    rejects = []

    allowed_categories = {"Billing", "Technical", "General"}
    allowed_priorities = {"Low", "Medium", "High", "Critical"}
    allowed_statuses = {"Open", "Resolved", "Escalated"}

    duplicates = df[df["ticket_id"].duplicated(keep=False)] if "ticket_id" in df.columns else pd.DataFrame()
    duplicate_ids = set(duplicates["ticket_id"].dropna().astype(str))

    for idx, row in df.iterrows():
        ticket_id = row.get("ticket_id", None)
        ticket_key = str(ticket_id) if pd.notna(ticket_id) else ""

        if ticket_key in duplicate_ids:
            rejects.append((ticket_key or None, "duplicate ticket_id"))
            continue

        category = row.get("category")
        if pd.isna(category) or str(category) not in allowed_categories:
            rejects.append((ticket_key or None, "invalid category"))
            continue

        priority = row.get("priority")
        if pd.isna(priority) or str(priority) not in allowed_priorities:
            rejects.append((ticket_key or None, "invalid priority"))
            continue

        status = row.get("status")
        if pd.isna(status) or str(status) not in allowed_statuses:
            rejects.append((ticket_key or None, "invalid status"))
            continue

        rating = row.get("customer_rating")
        if pd.notna(rating):
            try:
                rating_value = int(rating)
            except (TypeError, ValueError):
                rejects.append((ticket_key or None, "rating outside 1-5"))
                continue
            if rating_value < 1 or rating_value > 5:
                rejects.append((ticket_key or None, "rating outside 1-5"))
                continue

        created_at = row.get("created_at")
        if pd.isna(created_at):
            rejects.append((ticket_key or None, "created_at cannot be parsed"))
            continue
        try:
            pd.to_datetime(created_at)
        except (TypeError, ValueError):
            rejects.append((ticket_key or None, "created_at cannot be parsed"))
            continue

        valid_rows.append(row)

    valid_df = pd.DataFrame(valid_rows)
    if valid_df.empty:
        valid_df = df.iloc[0:0].copy()
    if "customer_rating" in valid_df.columns:
        valid_df["customer_rating"] = pd.to_numeric(valid_df["customer_rating"], errors="coerce")
        valid_df["customer_rating"] = valid_df["customer_rating"].apply(
            lambda value: int(value) if pd.notna(value) else None
        ).astype(object)
    return valid_df, rejects


def load_to_db(valid_df, database_url):
    """Load valid rows into the tickets table using a temporary staging table in one transaction."""
    if valid_df.empty:
        return

    columns = [
        "ticket_id",
        "created_at",
        "category",
        "priority",
        "status",
        "response_time_hrs",
        "resolution_time_hrs",
        "agent_id",
        "customer_rating",
        "issue_summary",
    ]

    def clean_value(value, col_name):
        if pd.isna(value):
            return None
        if col_name == "customer_rating":
            return int(value)
        return value

    table_df = valid_df.copy()
    if "customer_rating" in table_df.columns:
        table_df["customer_rating"] = pd.to_numeric(table_df["customer_rating"], errors="coerce")
        table_df["customer_rating"] = table_df["customer_rating"].apply(
            lambda value: int(value) if pd.notna(value) else None
        ).astype(object)
    for col in columns:
        if col in table_df.columns:
            table_df[col] = table_df[col].map(lambda value, col_name=col: clean_value(value, col_name)).astype(object)

    with psycopg.connect(database_url) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("CREATE TEMP TABLE tickets_stage (LIKE tickets INCLUDING ALL)")
                copy_sql = (
                    "COPY tickets_stage (ticket_id, created_at, category, priority, status, "
                    "response_time_hrs, resolution_time_hrs, agent_id, customer_rating, issue_summary) "
                    "FROM STDIN"
                )
                with cur.copy(copy_sql) as copy:
                    for record in table_df[columns].to_dict(orient="records"):
                        row = tuple(clean_value(record.get(col), col) for col in columns)
                        copy.write_row(row)
                cur.execute("TRUNCATE tickets")
                cur.execute(
                    "INSERT INTO tickets (ticket_id, created_at, category, priority, status, response_time_hrs, resolution_time_hrs, agent_id, customer_rating, issue_summary) "
                    "SELECT ticket_id, created_at, category, priority, status, response_time_hrs, resolution_time_hrs, agent_id, customer_rating, issue_summary FROM tickets_stage"
                )


def file_checksum(path):
    """Return the SHA-256 checksum for the given file."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()

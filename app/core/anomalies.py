"""Find unresolved high-priority tickets that exceed the age threshold."""

from app.core.database import run_query


def find_anomalies() -> list[dict]:
    rows = run_query(
        """SELECT ticket_id, priority, status, age_hours
FROM v_tickets
WHERE priority IN ('High', 'Critical') AND status != 'Resolved' AND age_hours > 24
ORDER BY age_hours DESC"""
    )
    return [
        {
            "ticket_id": row["ticket_id"],
            "reason": f"{row['priority']} priority, unresolved for {row['age_hours']:.1f}h (threshold 24h)",
        }
        for row in rows
    ]
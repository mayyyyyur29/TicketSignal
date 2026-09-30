"""Find unusually long resolutions and aging high-priority open tickets."""

from app.core.database import run_query


def find_anomalies(timeframe: str | None = None) -> list[dict]:
    week_filter = "AND created_at >= as_of - interval '7 days'" if timeframe == "week" else ""
    rows = run_query(
        f"""SELECT ticket_id, priority, status, age_hours, resolution_time_hrs
FROM v_tickets
WHERE (
    (status != 'Resolved' AND priority IN ('High', 'Critical') AND age_hours > 24)
    OR (status = 'Resolved' AND resolution_time_hrs > 24)
)
{week_filter}
ORDER BY CASE WHEN status = 'Resolved' THEN resolution_time_hrs ELSE age_hours END DESC"""
    )
    return [
        {
            "ticket_id": row["ticket_id"],
            "reason": (
                f"{row['priority']} priority, resolution took {row['resolution_time_hrs']:.1f}h (threshold 24h)"
                if row["status"] == "Resolved"
                else f"{row['priority']} priority, unresolved for {row['age_hours']:.1f}h (threshold 24h)"
            ),
        }
        for row in rows
    ]
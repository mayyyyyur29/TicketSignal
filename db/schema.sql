CREATE TABLE IF NOT EXISTS tickets (
    ticket_id           TEXT PRIMARY KEY,
    created_at          TIMESTAMP NOT NULL,
    category            TEXT NOT NULL CHECK (category IN ('Billing', 'Technical', 'General')),
    priority            TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
    status              TEXT NOT NULL CHECK (status IN ('Open', 'Resolved', 'Escalated')),
    response_time_hrs   NUMERIC(6,1) NOT NULL,
    resolution_time_hrs NUMERIC(6,1),
    agent_id            TEXT NOT NULL,
    customer_rating     SMALLINT CHECK (customer_rating BETWEEN 1 AND 5),
    issue_summary       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets (created_at);
CREATE INDEX IF NOT EXISTS idx_tickets_agent_id   ON tickets (agent_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status_priority ON tickets (status, priority);

CREATE OR REPLACE VIEW v_tickets AS
WITH cfg AS (
  SELECT COALESCE(NULLIF(current_setting('app.as_of', true), '')::timestamp,
                  (SELECT max(created_at) FROM tickets)) AS as_of
)
SELECT t.*,
       cfg.as_of,
       (t.status = 'Resolved') AS is_resolved,
       t.created_at + (t.resolution_time_hrs::float8) * interval '1 hour' AS resolved_at,
       EXTRACT(EPOCH FROM (cfg.as_of - t.created_at)) / 3600 AS age_hours
FROM tickets t CROSS JOIN cfg
WHERE t.created_at <= cfg.as_of;
-- 1. Test: inserts two rows with different created_at values and verifies the view uses the default as-of time.
INSERT INTO tickets VALUES ('T-A','2024-03-30 18:06','Billing','High','Open',1.0,NULL,'AGT-01',NULL,'test');
INSERT INTO tickets VALUES ('T-B','2024-03-29 18:06','Billing','High','Open',1.0,NULL,'AGT-01',NULL,'test');

-- 2. Test: the view should expose as_of, age_hours, and the derived columns for both rows.
SELECT ticket_id, as_of, age_hours FROM v_tickets ORDER BY ticket_id;

-- 3. Test: overriding app.as_of changes the view’s time boundary and should filter rows accordingly.
SET app.as_of = '2024-03-29 18:06';

-- 4. Test: the same SELECT after the override should reflect the new as_of value and row visibility.
SELECT ticket_id, as_of, age_hours FROM v_tickets ORDER BY ticket_id;

-- 5. Test: cleanup removes the rows so the schema/test remains isolated.
DELETE FROM tickets;
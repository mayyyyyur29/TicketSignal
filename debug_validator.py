from sqlglot import parse_one, exp
sql = "SELECT ticket_id FROM v_tickets WHERE resolution_time_hrs > 24 OR status != 'Resolved'"
tree = parse_one(sql, read="postgres")
for node in tree.walk():
    if isinstance(node, exp.Func) and not isinstance(node, exp.Cast):
        name = node.name if isinstance(node, exp.Anonymous) else node.sql_name()
        print(type(node).__name__, repr(name))

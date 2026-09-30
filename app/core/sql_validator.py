"""Validate generated queries before they reach the read-only database role."""

from sqlglot import exp, parse
from sqlglot.errors import ParseError
_ALLOWED_FUNCTIONS = {
    "count", "sum", "avg", "min", "max", "round", "extract",
    "coalesce", "nullif", "date_trunc",
}



def validate_sql(sql: str) -> tuple[bool, str]:
    """Allow one comment-free SELECT over v_tickets using approved functions only."""
    try:
        statements = parse(sql, read="postgres")
    except (ParseError, TypeError, ValueError):
        return False, "SQL could not be parsed"
    statements = [statement for statement in statements if statement is not None]
    if len(statements) != 1:
        return False, "exactly one SQL statement is required"
    tree = statements[0]
    if not isinstance(tree, exp.Select):
        return False, "only SELECT statements are allowed"
    if tree.args.get("into") or tree.args.get("locks"):
        return False, "write-like SELECT clauses are not allowed"
    for node in tree.walk():
        if node.comments:
            return False, "SQL comments are not allowed"
        if isinstance(
            node,
            (
                exp.Insert,
                exp.Update,
                exp.Delete,
                exp.Create,
                exp.Alter,
                exp.Drop,
                exp.TruncateTable,
                exp.Merge,
                exp.Grant,
                exp.Revoke,
            ),
        ):
            return False, "DDL and DML statements are not allowed"
    tables = list(tree.find_all(exp.Table))
    if not tables or any(
        table.name.lower() != "v_tickets" or table.db or table.catalog for table in tables
    ):
        return False, "queries may reference only the v_tickets view"
    for node in tree.walk():
        if isinstance(node, exp.Func) and not isinstance(
            node, (exp.Cast, exp.Connector, exp.Not)
        ):
            if isinstance(node.parent, exp.Dot) and node.parent.expression is node:
                return False, "schema-qualified functions are not allowed"
            function = (
                "date_trunc"
                if isinstance(node, exp.TimestampTrunc)
                else node.name.lower()
                if isinstance(node, exp.Anonymous)
                else node.sql_name().lower()
            )
            if function in {"now", "current_date", "current_timestamp"}:
                return False, f"function {function} is not allowed"
            if function not in _ALLOWED_FUNCTIONS:
                return False, f"function {function} is not allowed"
    return True, ""

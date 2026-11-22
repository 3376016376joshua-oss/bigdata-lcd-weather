"""Turn a HiveQL query file into a statement Spark SQL can run."""

from __future__ import annotations

import re

DATABASE_VARIABLE = "${hivevar:db}"
_DATABASE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_VARIABLE = re.compile(r"\$\{[^}]*\}")


def render_query(sql_text: str, database: str) -> str:
    """Fill in the database the way ``beeline --hivevar db=<database>`` does.

    The trailing semicolon that Beeline needs is removed because ``spark.sql`` takes a
    single statement.
    """
    if not _DATABASE_NAME.fullmatch(database):
        raise ValueError(f"not a valid database name: {database!r}")
    if DATABASE_VARIABLE not in sql_text:
        raise ValueError(f"the query does not read from {DATABASE_VARIABLE}")
    rendered = sql_text.replace(DATABASE_VARIABLE, database).strip().rstrip(";").rstrip()
    unresolved = _VARIABLE.search(rendered)
    if unresolved:
        raise ValueError(f"unknown variable {unresolved.group(0)} in the query")
    if ";" in rendered:
        raise ValueError("a query file must hold exactly one statement")
    return rendered

"""Query files and their rendering for Spark SQL (no Spark needed)."""

from __future__ import annotations

import pytest

from lcdweather.analysis.catalog import ANALYSIS_QUESTIONS, discover_queries, select_queries
from lcdweather.analysis.export import is_cluster_path
from lcdweather.analysis.sql import DATABASE_VARIABLE, render_query

EXPECTED_QUERY_COUNT = 22


def test_render_query_fills_database_and_drops_semicolon():
    rendered = render_query(f"SELECT 1 FROM {DATABASE_VARIABLE}.lcd_daily;\n", "wl3564_nyu_edu")
    assert rendered == "SELECT 1 FROM wl3564_nyu_edu.lcd_daily"


@pytest.mark.parametrize(
    ("sql_text", "database", "message"),
    [
        (f"SELECT 1 FROM {DATABASE_VARIABLE}.t", "db; DROP TABLE t", "valid database name"),
        ("SELECT 1 FROM lcd_daily", "db", "does not read from"),
        (f"SELECT ${{hivevar:other}} FROM {DATABASE_VARIABLE}.t", "db", "unknown variable"),
        (f"SELECT 1 FROM {DATABASE_VARIABLE}.t; SELECT 2", "db", "exactly one statement"),
    ],
)
def test_render_query_rejects_bad_input(sql_text, database, message):
    with pytest.raises(ValueError, match=message):
        render_query(sql_text, database)


def test_every_question_has_query_files(queries_dir):
    queries = discover_queries(queries_dir)
    assert len(queries) == EXPECTED_QUERY_COUNT
    assert {query.question for query in queries} == set(ANALYSIS_QUESTIONS)
    assert all(query.name == query.path.stem for query in queries)


def test_query_files_are_single_beeline_friendly_statements(queries_dir):
    for query in discover_queries(queries_dir):
        sql_text = query.read_sql()
        assert render_query(sql_text, "some_db"), query.name
        assert sql_text.rstrip().endswith(";"), query.name
        comments = [line for line in sql_text.splitlines() if line.lstrip().startswith("--")]
        # Older Beeline versions misread quotes and semicolons inside comments.
        assert not [line for line in comments if set(line) & set("';\"")], query.name


def test_discover_queries_ignores_other_questions(tmp_path):
    for name in ("q1_a.sql", "q6_b.sql", "q7_regression.sql", "notes.sql"):
        (tmp_path / name).write_text(f"SELECT 1 FROM {DATABASE_VARIABLE}.t;", encoding="utf-8")
    assert [query.name for query in discover_queries(tmp_path)] == ["q1_a", "q6_b"]


def test_discover_queries_requires_query_files(tmp_path):
    with pytest.raises(FileNotFoundError, match="no q<N>_<name>.sql"):
        discover_queries(tmp_path)
    with pytest.raises(FileNotFoundError, match="query directory not found"):
        discover_queries(tmp_path / "missing")


def test_select_queries_filters_by_question(queries_dir):
    queries = discover_queries(queries_dir)
    assert select_queries(queries, None) == queries
    assert {query.question for query in select_queries(queries, [2, 5])} == {2, 5}
    with pytest.raises(ValueError, match="questions 1-6"):
        select_queries(queries, [7])


@pytest.mark.parametrize(
    ("results_dir", "expected"),
    [
        ("hdfs:///user/wl3564_nyu_edu/lcd/results", True),
        ("gs://bucket/results", True),
        ("results", False),
        ("/tmp/results", False),
        ("file:///tmp/results", False),
    ],
)
def test_is_cluster_path(results_dir, expected):
    assert is_cluster_path(results_dir) is expected

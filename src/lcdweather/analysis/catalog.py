"""The Phase 4 query files and the result each one produces."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ANALYSIS_QUESTIONS = (1, 2, 3, 4, 5, 6)
_QUERY_FILE = re.compile(r"q(\d+)_[a-z0-9_]+\.sql")


@dataclass(frozen=True)
class AnalysisQuery:
    """One query file; ``name`` is also the name of its result CSV."""

    name: str
    question: int
    path: Path

    def read_sql(self) -> str:
        return self.path.read_text(encoding="utf-8")


def discover_queries(queries_dir: str | Path) -> list[AnalysisQuery]:
    """List the question 1-6 query files in ``queries_dir``, sorted by name."""
    directory = Path(queries_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"query directory not found: {directory}")
    queries = []
    for path in sorted(directory.glob("q*.sql")):
        match = _QUERY_FILE.fullmatch(path.name)
        if match and int(match.group(1)) in ANALYSIS_QUESTIONS:
            queries.append(AnalysisQuery(path.stem, int(match.group(1)), path))
    if not queries:
        raise FileNotFoundError(f"no q<N>_<name>.sql query files in {directory}")
    return queries


def select_queries(
    queries: Iterable[AnalysisQuery], questions: Iterable[int] | None
) -> list[AnalysisQuery]:
    """Keep the queries of the given questions (all of them when ``questions`` is None)."""
    if questions is None:
        return list(queries)
    wanted = set(questions)
    unknown = wanted - set(ANALYSIS_QUESTIONS)
    if unknown:
        raise ValueError(f"Phase 4 covers questions 1-6, got {sorted(unknown)}")
    return [query for query in queries if query.question in wanted]

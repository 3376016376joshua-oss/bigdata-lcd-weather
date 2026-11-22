"""Phase 4: geography, time and category analysis for questions 1-6.

The queries live in ``hive/queries/q<N>_<name>.sql`` and are the single source of truth:
Beeline runs them on Hive and :mod:`lcdweather.analysis.runner` runs the same text with
Spark SQL, so both engines answer every question with one definition.
"""

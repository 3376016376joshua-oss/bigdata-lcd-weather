"""Phase 6: time the Phase 2 ingest and Phase 4 analysis jobs on 1, 4, 8 and 16 years.

Runs on the edge node as plain Python and launches each job with spark-submit:

    PYTHONPATH=src python3 jobs/phase6_timing.py --spark-submit "spark-submit --master yarn"
"""

from __future__ import annotations

import sys

from lcdweather.timing.cli import main

if __name__ == "__main__":
    sys.exit(main())

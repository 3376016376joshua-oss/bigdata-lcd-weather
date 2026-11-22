#!/usr/bin/env bash
# Phase 6 on NYU Dataproc: time the Phase 2 ingest and Phase 4 analysis jobs on
# 1, 4, 8 and 16 years and write results/runtime_scaling.csv (+ _summary.csv).
#
#   bash scripts/run_phase6_timing.sh                      # both jobs, all four sizes
#   bash scripts/run_phase6_timing.sh --jobs analysis --repeats 3
#
# Each window ingests into its own scratch cleaned zone (<LCD_HDFS_ROOT>/timing/clean/<n>y)
# and Hive database (<LCD_HIVE_DB>_timing_t<n>y), then analyses that database, so the
# production zone and database are never touched. Needs Phase 1's raw zone.
# The jobs run with LCD_SPARK_SUBMIT_OPTS, the same spark-submit flags as run_phase2.sh.
set -euo pipefail

# shellcheck source=scripts/phase_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/phase_common.sh"
cd "$REPO_ROOT"

build_package_zip
PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:${PYTHONPATH}}" python3 jobs/phase6_timing.py \
  --spark-submit "spark-submit ${LCD_SPARK_SUBMIT_OPTS} --py-files ${PACKAGE_ZIP}" \
  "$@"

#!/usr/bin/env bash
# Phase 6 on NYU Dataproc: time the Phase 2 ingest and Phase 4 analysis jobs on
# 1, 4, 8 and 16 years and write results/runtime_scaling.csv (+ _summary.csv).
#
#   bash scripts/run_phase6_timing.sh                      # both jobs, all four sizes
#   bash scripts/run_phase6_timing.sh --jobs analysis --repeats 3
#
# Each window ingests into its own scratch cleaned zone (<LCD_HDFS_ROOT>/timing/clean/<n>y)
# and Hive database (<LCD_HIVE_DB>_timing_t<n>y), then analyses that database, so the
# production zone and database are never touched. Needs jobs/phase2_ingest.py and
# jobs/phase4_analysis.py (the Phase 2-3 and Phase 4 PRs) and Phase 1's raw zone.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/env.sh
source "${REPO_ROOT}/scripts/env.sh"
SPARK_SUBMIT="${SPARK_SUBMIT:-spark-submit}"
SPARK_SUBMIT_ARGS="${SPARK_SUBMIT_ARGS:---master yarn --deploy-mode client}"
PACKAGE_ZIP="${REPO_ROOT}/dist/lcdweather.zip"

mkdir -p "$(dirname "${PACKAGE_ZIP}")"
rm -f "${PACKAGE_ZIP}"
(cd "${REPO_ROOT}/src" && python3 -m zipfile -c "${PACKAGE_ZIP}" lcdweather)

cd "${REPO_ROOT}"
PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" python3 jobs/phase6_timing.py \
  --spark-submit "${SPARK_SUBMIT} ${SPARK_SUBMIT_ARGS} --py-files ${PACKAGE_ZIP}" \
  "$@"

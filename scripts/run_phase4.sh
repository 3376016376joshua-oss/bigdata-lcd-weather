#!/usr/bin/env bash
# Phase 4: answer questions 1-6 on the NYU Dataproc cluster.
#
#   scripts/run_phase4.sh spark   run the queries with Spark SQL, results to HDFS
#   scripts/run_phase4.sh fetch   copy the Spark results from HDFS into results/
#   scripts/run_phase4.sh hive    run the same queries on Hive through Beeline,
#                                 results to results/hive/
#   scripts/run_phase4.sh all     spark, then fetch (default)
#
# Settings come from scripts/env.sh (LCD_NETID, LCD_HIVE_DB, LCD_HDFS_ROOT,
# LCD_RESULTS_DIR). LCD_BEELINE_URL is the HiveServer2 JDBC URL. Extra arguments
# after the step name go to jobs/phase4_analysis.py, for example
#   scripts/run_phase4.sh spark --questions 1 5

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/env.sh
source "${REPO_DIR}/scripts/env.sh"

: "${LCD_BEELINE_URL:=jdbc:hive2://localhost:10000}"
QUERIES_DIR="${REPO_DIR}/hive/queries"
HDFS_RESULTS="${LCD_HDFS_ROOT}/results"
case "${LCD_RESULTS_DIR}" in
  /*) LOCAL_RESULTS="${LCD_RESULTS_DIR}" ;;
  *) LOCAL_RESULTS="${REPO_DIR}/${LCD_RESULTS_DIR}" ;;
esac

phase4_queries() {
  find "${QUERIES_DIR}" -maxdepth 1 -name 'q[1-6]_*.sql' | sort
}

run_spark() {
  # The job only runs SQL, so lcdweather is needed on the driver alone. Client mode
  # keeps the driver on this node, where it imports the package and reads the query
  # files straight from the repository.
  PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}" spark-submit \
    --name lcd-phase4-analysis \
    --deploy-mode client \
    "${REPO_DIR}/jobs/phase4_analysis.py" \
    --db "${LCD_HIVE_DB}" \
    --queries-dir "${QUERIES_DIR}" \
    --results-dir "${HDFS_RESULTS}" \
    "$@"
}

fetch_results() {
  local query name
  mkdir -p "${LOCAL_RESULTS}"
  while IFS= read -r query; do
    name="$(basename "${query}" .sql)"
    if hdfs dfs -test -d "${HDFS_RESULTS}/${name}"; then
      rm -f "${LOCAL_RESULTS}/${name}.csv"
      hdfs dfs -getmerge "${HDFS_RESULTS}/${name}" "${LOCAL_RESULTS}/${name}.csv"
      echo "fetched ${LOCAL_RESULTS}/${name}.csv"
    else
      echo "skipped ${name}: ${HDFS_RESULTS}/${name} does not exist" >&2
    fi
  done < <(phase4_queries)
  # getmerge leaves a checksum file next to every CSV.
  find "${LOCAL_RESULTS}" -maxdepth 1 -name '.q[1-6]_*.csv.crc' -delete
}

run_hive() {
  local query name
  mkdir -p "${LOCAL_RESULTS}/hive"
  while IFS= read -r query; do
    name="$(basename "${query}" .sql)"
    echo "beeline: ${name}"
    beeline -u "${LCD_BEELINE_URL}" \
      --hivevar db="${LCD_HIVE_DB}" \
      --hiveconf hive.resultset.use.unique.column.names=false \
      --outputformat=csv2 --silent=true --showHeader=true \
      -f "${query}" > "${LOCAL_RESULTS}/hive/${name}.csv"
  done < <(phase4_queries)
}

step="${1:-all}"
if [ "$#" -gt 0 ]; then
  shift
fi
case "${step}" in
  spark) run_spark "$@" ;;
  fetch) fetch_results ;;
  hive) run_hive ;;
  all)
    run_spark "$@"
    fetch_results
    ;;
  *)
    echo "usage: $0 [spark|fetch|hive|all] [job arguments]" >&2
    exit 2
    ;;
esac

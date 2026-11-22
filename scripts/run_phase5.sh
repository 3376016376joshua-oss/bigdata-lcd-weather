#!/usr/bin/env bash
# Phase 5 on NYU Dataproc: submit the three MLlib jobs, then pull their result
# CSVs from HDFS into results/.
#
#   bash scripts/run_phase5.sh                       # regression, classification, kmeans
#   bash scripts/run_phase5.sh kmeans                # only the named job(s)
#   bash scripts/run_phase5.sh fetch                 # only download the results
#
# Local smoke run without Hive (needs pyspark and Java):
#   LCD_SPARK_SUBMIT_OPTS="--master local[2]" PHASE5_JOB_ARGS="--synthetic" PHASE5_GRID=quick \
#     LCD_RESULTS_URI=results bash scripts/run_phase5.sh
#
# LCD_SPARK_SUBMIT_OPTS holds extra spark-submit flags, as for run_phase2.sh.
set -euo pipefail

# shellcheck source=scripts/phase_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/phase_common.sh"
RESULTS_URI="${LCD_RESULTS_URI:-${LCD_HDFS_ROOT}/results}"
LOCAL_RESULTS="${LCD_RESULTS_DIR}"
PHASE5_JOB_ARGS="${PHASE5_JOB_ARGS:-}"
# Hyper-parameter grid of the two supervised jobs: full, or quick for a smoke run.
PHASE5_GRID="${PHASE5_GRID:-full}"
RESULT_PREFIXES=(q7_ q8_ kmeans_)

submit_phase5_job() {
  local job="$1"
  local grid_args=()
  if [[ "${job}" != "kmeans" ]]; then
    grid_args=(--grid "${PHASE5_GRID}")
  fi
  echo "==> Phase 5 ${job}"
  # shellcheck disable=SC2086  # PHASE5_JOB_ARGS holds several words by design
  submit_job "phase5_${job}.py" --database "${LCD_HIVE_DB}" --results-dir "${RESULTS_URI}" \
    ${grid_args[@]+"${grid_args[@]}"} ${PHASE5_JOB_ARGS}
}

fetch_results() {
  if [[ "${RESULTS_URI}" != "${LCD_HDFS_SCHEME}"* ]]; then
    echo "Results were written locally to ${RESULTS_URI#file://}; nothing to fetch."
    return 0
  fi
  mkdir -p "${LOCAL_RESULTS}"
  local prefix dir name
  for prefix in "${RESULT_PREFIXES[@]}"; do
    while IFS= read -r dir; do
      name="$(basename "${dir}")"
      hdfs dfs -getmerge "${dir}" "${LOCAL_RESULTS}/${name}.csv"
      rm -f "${LOCAL_RESULTS}/.${name}.csv.crc"
      echo "fetched ${LOCAL_RESULTS}/${name}.csv"
    done < <(hdfs dfs -ls -d -C "${RESULTS_URI%/}/${prefix}*")
  done
}

main() {
  local jobs=("$@")
  if [[ ${#jobs[@]} -eq 0 ]]; then
    jobs=(regression classification kmeans)
  fi
  if [[ "${jobs[0]}" != "fetch" ]]; then
    build_package_zip
    local job
    for job in "${jobs[@]}"; do
      case "${job}" in
        regression|classification|kmeans) submit_phase5_job "${job}" ;;
        *) echo "Unknown job '${job}' (regression, classification, kmeans, fetch)" >&2; exit 2 ;;
      esac
    done
  fi
  fetch_results
}

main "$@"

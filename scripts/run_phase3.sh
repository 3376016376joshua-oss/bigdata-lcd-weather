#!/usr/bin/env bash
# Phase 3 on NYU Dataproc: validate lcd_daily against FiveThirtyEight, profile the data,
# then copy the result CSVs from HDFS into the local results folder.
#
#   scripts/run_phase3.sh
#
# Environment: the settings of scripts/env.sh and LCD_SPARK_SUBMIT_OPTS (extra spark-submit
# flags).
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/phase_common.sh"
cd "$REPO_ROOT"

RESULT_NAMES=(
  validation_538
  validation_538_daily
  profile_report_types
  profile_missing
  profile_ranges
  table_row_counts
)

build_package_zip
submit_job phase3_validate.py \
  --db "$LCD_HIVE_DB" \
  --fivethirtyeight "$LCD_HDFS_ROOT/fivethirtyeight" \
  --results "$LCD_HDFS_ROOT/results"
submit_job phase3_profile.py \
  --input "$LCD_HDFS_ROOT/raw" \
  --db "$LCD_HIVE_DB" \
  --results "$LCD_HDFS_ROOT/results"

mkdir -p "$LCD_RESULTS_DIR"
for name in "${RESULT_NAMES[@]}"; do
  hdfs dfs -getmerge "$LCD_HDFS_ROOT/results/$name" "$LCD_RESULTS_DIR/$name.csv"
  # getmerge leaves a checksum file next to each copy; it is of no use outside HDFS.
  rm -f "$LCD_RESULTS_DIR/.$name.csv.crc"
  echo "wrote $LCD_RESULTS_DIR/$name.csv"
done

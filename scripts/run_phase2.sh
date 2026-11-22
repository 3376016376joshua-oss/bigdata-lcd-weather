#!/usr/bin/env bash
# Phase 2 on NYU Dataproc: raw LCD v2 CSV in HDFS -> cleaned ORC tables in Hive.
#
#   scripts/run_phase2.sh                     # all years, tables lcd_hourly/lcd_daily/lcd_monthly
#   scripts/run_phase2.sh --years 2010-2013   # extra arguments go to jobs/phase2_ingest.py
#
# Environment: the settings of scripts/env.sh, LCD_STATIONS_CSV, LCD_BEELINE_URL,
# LCD_SPARK_SUBMIT_OPTS (extra spark-submit flags) and LCD_SKIP_HIVE_DDL=1 to leave out the
# Beeline step, for example for a trial run with --table-prefix.
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/phase_common.sh"
cd "$REPO_ROOT"

build_package_zip
submit_job phase2_ingest.py \
  --input "$LCD_HDFS_ROOT/raw" \
  --output "$LCD_HDFS_ROOT/clean" \
  --db "$LCD_HIVE_DB" \
  "$@"

if [[ "${LCD_SKIP_HIVE_DDL:-0}" == "1" ]]; then
  echo "LCD_SKIP_HIVE_DDL=1: not running hive/ddl"
  exit 0
fi

for ddl in hive/ddl/lcd_hourly.sql hive/ddl/lcd_daily.sql hive/ddl/lcd_monthly.sql; do
  beeline -u "$LCD_BEELINE_URL" \
    --hivevar db="$LCD_HIVE_DB" \
    --hivevar clean_zone="$LCD_HDFS_ROOT/clean" \
    -f "$ddl"
done

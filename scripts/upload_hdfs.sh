#!/usr/bin/env bash
# Copy the raw LCD files and the FiveThirtyEight validation files to HDFS (NYU Dataproc).
#
#   bash scripts/upload_hdfs.sh             # upload
#   bash scripts/upload_hdfs.sh --dry-run   # print the hdfs commands without running them
#
# Layout written under $LCD_HDFS_ROOT (default hdfs:///user/<netid>_nyu_edu/lcd):
#   raw/<station_id>/LCD_<station_id>_<year>.csv
#   fivethirtyeight/<CODE>.csv
# Set LCD_NETID (or LCD_HDFS_ROOT) to upload into another home directory.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/env.sh
source "$script_dir/env.sh"

dry_run=0
case "${1:-}" in
  "") ;;
  --dry-run) dry_run=1 ;;
  *)
    echo "usage: $0 [--dry-run]" >&2
    exit 2
    ;;
esac

readonly RAW_ZONE="$LCD_HDFS_ROOT/raw"
readonly FIVETHIRTYEIGHT_ZONE="$LCD_HDFS_ROOT/fivethirtyeight"

run_hdfs() {
  if ((dry_run)); then
    echo "hdfs dfs $*"
  else
    hdfs dfs "$@"
  fi
}

# Fails unless the HDFS directory holds exactly as many files as were uploaded to it.
verify_file_count() {
  local hdfs_dir="$1" expected="$2" actual
  if ((dry_run)); then
    return
  fi
  actual="$(hdfs dfs -count "$hdfs_dir" | awk '{print $2}')"
  if [[ "$actual" != "$expected" ]]; then
    echo "$hdfs_dir holds $actual files, expected $expected" >&2
    exit 1
  fi
}

shopt -s nullglob

raw_files=("$LCD_LOCAL_RAW_DIR"/*/LCD_*.csv)
if ((${#raw_files[@]} == 0)); then
  echo "no LCD files under $LCD_LOCAL_RAW_DIR; run scripts/download_lcd.py first" >&2
  exit 1
fi
for station_dir in "$LCD_LOCAL_RAW_DIR"/*/; do
  station_files=("$station_dir"LCD_*.csv)
  if ((${#station_files[@]} == 0)); then
    continue
  fi
  station_id="$(basename "$station_dir")"
  run_hdfs -mkdir -p "$RAW_ZONE/$station_id"
  run_hdfs -put -f "${station_files[@]}" "$RAW_ZONE/$station_id/"
done
verify_file_count "$RAW_ZONE" "${#raw_files[@]}"
echo "raw zone: ${#raw_files[@]} files in $RAW_ZONE"

validation_files=("$LCD_FIVETHIRTYEIGHT_DIR"/*.csv)
if ((${#validation_files[@]} == 0)); then
  echo "no files under $LCD_FIVETHIRTYEIGHT_DIR; run scripts/fetch_fivethirtyeight.sh first" >&2
  exit 1
fi
run_hdfs -mkdir -p "$FIVETHIRTYEIGHT_ZONE"
run_hdfs -put -f "${validation_files[@]}" "$FIVETHIRTYEIGHT_ZONE/"
verify_file_count "$FIVETHIRTYEIGHT_ZONE" "${#validation_files[@]}"
echo "validation set: ${#validation_files[@]} files in $FIVETHIRTYEIGHT_ZONE"
if ((dry_run)); then
  echo "dry run: nothing was uploaded"
fi

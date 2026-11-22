#!/usr/bin/env bash
# Fetch the ten FiveThirtyEight "US Weather History" files, the validation set.
# Source: https://github.com/fivethirtyeight/data/tree/master/us-weather-history
#
#   bash scripts/fetch_fivethirtyeight.sh [output_dir]
#
# One file per city code in config/stations.csv lands in data/fivethirtyeight/<CODE>.csv.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(dirname "$script_dir")"
# shellcheck source=scripts/env.sh
source "$script_dir/env.sh"

readonly FIVETHIRTYEIGHT_BASE_URL="${LCD_FIVETHIRTYEIGHT_BASE_URL:-https://raw.githubusercontent.com/fivethirtyeight/data/master/us-weather-history}"
readonly EXPECTED_HEADER="date,actual_mean_temp,actual_min_temp,actual_max_temp,average_min_temp,average_max_temp,record_min_temp,record_max_temp,record_min_temp_year,record_max_temp_year,actual_precipitation,average_precipitation,record_precipitation"
readonly CITY_CODE_FIELD=3

stations_csv="${LCD_STATIONS_CSV:-$repo_root/config/stations.csv}"
out_dir="${1:-$LCD_FIVETHIRTYEIGHT_DIR}"
mkdir -p "$out_dir"

city_codes="$(tail -n +2 "$stations_csv" | cut -d, -f"$CITY_CODE_FIELD" | sort -u)"
if [[ -z "$city_codes" ]]; then
  echo "no city codes found in $stations_csv" >&2
  exit 1
fi

for code in $city_codes; do
  target="$out_dir/$code.csv"
  curl --fail --silent --show-error --location --retry 3 --retry-delay 2 \
    --output "$target.part" "$FIVETHIRTYEIGHT_BASE_URL/$code.csv"
  header="$(head -n 1 "$target.part" | tr -d '\r')"
  if [[ "$header" != "$EXPECTED_HEADER" ]]; then
    echo "$code.csv: unexpected header: $header" >&2
    rm -f "$target.part"
    exit 1
  fi
  mv "$target.part" "$target"
  echo "ok $target $(($(wc -l <"$target") - 1)) rows"
done

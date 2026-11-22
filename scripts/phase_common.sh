# Shared by run_phase2.sh and run_phase3.sh. Source it, do not run it.
# Loads the settings of scripts/env.sh and defines the helpers that package and submit a PySpark job.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck source=scripts/env.sh
source "$REPO_ROOT/scripts/env.sh"

: "${LCD_BEELINE_URL:=jdbc:hive2://localhost:10000}"
: "${LCD_SPARK_SUBMIT_OPTS:=}"

PACKAGE_ZIP=""

# Zip src/lcdweather so the executors can import it; the zip is removed when the script exits.
build_package_zip() {
  local build_dir
  build_dir="$(mktemp -d)"
  PACKAGE_ZIP="$build_dir/lcdweather.zip"
  trap 'rm -rf "$(dirname "$PACKAGE_ZIP")"' EXIT
  (cd "$REPO_ROOT/src" && python3 -m zipfile -c "$PACKAGE_ZIP" lcdweather)
}

# submit_job <job file under jobs/> [job arguments...]
submit_job() {
  local job="$1"
  shift
  # LCD_SPARK_SUBMIT_OPTS is a list of extra spark-submit flags, so it is split on spaces.
  # shellcheck disable=SC2086
  spark-submit $LCD_SPARK_SUBMIT_OPTS --py-files "$PACKAGE_ZIP" "$REPO_ROOT/jobs/$job" "$@"
}
